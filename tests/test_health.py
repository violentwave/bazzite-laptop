"""Unit tests for ai/health.py — provider health tracking."""

import time

import pytest

from ai.health import HealthTracker, ProviderHealth


class TestProviderHealth:
    """ProviderHealth dataclass and score calculation."""

    def test_cold_start_score_is_half(self):
        h = ProviderHealth(name="groq")
        assert h.score == 0.5

    def test_perfect_score(self):
        h = ProviderHealth(name="groq", success_count=100, failure_count=0, total_latency_ms=100 * 500)  # noqa: E501
        assert h.score == pytest.approx(0.985, abs=0.001)

    def test_all_failures_score_near_zero(self):
        h = ProviderHealth(name="groq", success_count=0, failure_count=10, total_latency_ms=10 * 9000)  # noqa: E501
        assert h.score == pytest.approx(0.03, abs=0.001)

    def test_high_latency_penalizes_score(self):
        h = ProviderHealth(name="groq", success_count=10, failure_count=0, total_latency_ms=10 * 15000)  # noqa: E501
        assert h.score == pytest.approx(0.7, abs=0.001)

    def test_is_disabled_when_disabled_until_in_future(self):
        h = ProviderHealth(name="groq", disabled_until=time.time() + 300)
        assert h.is_disabled is True

    def test_is_not_disabled_when_disabled_until_in_past(self):
        h = ProviderHealth(name="groq", disabled_until=time.time() - 1)
        assert h.is_disabled is False

    def test_is_not_disabled_when_none(self):
        h = ProviderHealth(name="groq")
        assert h.is_disabled is False


class TestHealthTracker:
    @pytest.fixture()
    def tracker(self):
        return HealthTracker()

    def test_record_success_updates_counts(self, tracker):
        tracker.record_success("groq", latency_ms=200.0)
        h = tracker.get("groq")
        assert h.success_count == 1
        assert h.failure_count == 0
        assert h.consecutive_failures == 0
        assert h.total_latency_ms == 200.0

    def test_record_failure_increments_consecutive(self, tracker):
        tracker.record_failure("groq", error="timeout")
        tracker.record_failure("groq", error="timeout")
        h = tracker.get("groq")
        assert h.failure_count == 2
        assert h.consecutive_failures == 2
        assert h.last_error == "timeout"

    def test_success_resets_consecutive_failures(self, tracker):
        tracker.record_failure("groq", error="err")
        tracker.record_failure("groq", error="err")
        tracker.record_success("groq", latency_ms=100.0)
        h = tracker.get("groq")
        assert h.consecutive_failures == 0

    def test_auto_demotion_after_three_failures(self, tracker):
        for _ in range(3):
            tracker.record_failure("groq", error="err")
        h = tracker.get("groq")
        assert h.is_disabled is True
        assert h.disabled_until is not None
        assert h.disabled_until == pytest.approx(time.time() + 300, abs=5)

    def test_exponential_backoff_on_repeated_demotion(self, tracker):
        for _ in range(3):
            tracker.record_failure("groq", error="err")
        h = tracker.get("groq")
        first_duration = h.disabled_until - time.time()
        assert first_duration == pytest.approx(300, abs=5)
        h.disabled_until = time.time() - 1
        h.consecutive_failures = 0
        for _ in range(3):
            tracker.record_failure("groq", error="err")
        h = tracker.get("groq")
        second_duration = h.disabled_until - time.time()
        assert second_duration == pytest.approx(600, abs=5)

    def test_backoff_caps_at_thirty_minutes(self, tracker):
        h = tracker.get("groq")
        h._demotion_count = 10
        for _ in range(3):
            tracker.record_failure("groq", error="err")
        h = tracker.get("groq")
        duration = h.disabled_until - time.time()
        assert duration == pytest.approx(1800, abs=5)

    def test_get_creates_new_provider(self, tracker):
        h = tracker.get("new-provider")
        assert h.name == "new-provider"
        assert h.score == 0.5

    def test_get_sorted_returns_by_score_descending(self, tracker):
        tracker.record_success("fast-provider", latency_ms=100.0)
        tracker.record_success("fast-provider", latency_ms=100.0)
        tracker.record_failure("slow-provider", error="err")
        names = [h.name for h in tracker.get_sorted(["fast-provider", "slow-provider"])]
        assert names[0] == "fast-provider"

    def test_auth_broken_set_on_401(self, tracker):
        for _ in range(3):
            tracker.record_failure("gemini", error="HTTP 401 Unauthorized")
        assert tracker.get("gemini").auth_broken is True

    def test_auth_broken_set_on_403(self, tracker):
        for _ in range(3):
            tracker.record_failure("gemini", error="HTTP 403 Forbidden")
        assert tracker.get("gemini").auth_broken is True

    def test_auth_broken_not_set_on_generic_error(self, tracker):
        tracker.record_failure("gemini", error="timeout")
        assert tracker.get("gemini").auth_broken is False

    def test_auth_broken_cleared_on_success(self, tracker):
        for _ in range(3):
            tracker.record_failure("gemini", error="401 Unauthorized")
        tracker.record_success("gemini", latency_ms=100.0)
        assert tracker.get("gemini").auth_broken is False

    def test_get_sorted_excludes_disabled(self, tracker):
        for _ in range(3):
            tracker.record_failure("dead-provider", error="err")
        tracker.record_success("live-provider", latency_ms=100.0)
        names = [h.name for h in tracker.get_sorted(["dead-provider", "live-provider"])]
        assert "dead-provider" not in names
        assert "live-provider" in names
