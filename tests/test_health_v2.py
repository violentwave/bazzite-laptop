"""Tests for Phase 14 health improvements: staleness, auth_broken 3-strike, AllProvidersExhausted."""  # noqa: E501

import time

from ai.health import AllProvidersExhausted, HealthTracker


class TestStaleness:
    def test_stale_score_capped_at_0_8(self):
        """Provider not probed in 10+ min has effective_score capped at 0.8."""
        tracker = HealthTracker()
        tracker.record_success("groq", latency_ms=100.0)
        # Back-date last_probe_time past the threshold
        tracker.get("groq").last_probe_time = time.time() - 610
        sorted_providers = tracker.get_sorted(["groq"])
        assert len(sorted_providers) == 1
        assert sorted_providers[0].effective_score <= 0.8

    def test_fresh_provider_not_demoted(self):
        """Provider probed recently keeps its real score above 0.8."""
        tracker = HealthTracker()
        tracker.record_success("groq", latency_ms=100.0)
        sorted_providers = tracker.get_sorted(["groq"])
        assert sorted_providers[0].effective_score > 0.8

    def test_record_success_sets_last_probe_time(self):
        tracker = HealthTracker()
        before = time.time()
        tracker.record_success("groq", latency_ms=100.0)
        after = time.time()
        h = tracker.get("groq")
        assert h.last_probe_time is not None
        assert before <= h.last_probe_time <= after

    def test_record_failure_sets_last_probe_time(self):
        tracker = HealthTracker()
        tracker.record_failure("groq", "call failed")
        assert tracker.get("groq").last_probe_time is not None


class TestAuthBroken:
    def test_three_consecutive_401s_mark_auth_broken(self):
        tracker = HealthTracker()
        tracker.record_failure("groq", "call failed", status_code=401)
        assert tracker.get("groq").auth_broken is False
        tracker.record_failure("groq", "call failed", status_code=401)
        assert tracker.get("groq").auth_broken is False
        tracker.record_failure("groq", "call failed", status_code=401)
        assert tracker.get("groq").auth_broken is True

    def test_403_also_triggers_auth_broken(self):
        tracker = HealthTracker()
        for _ in range(3):
            tracker.record_failure("groq", "forbidden", status_code=403)
        assert tracker.get("groq").auth_broken is True

    def test_non_auth_error_does_not_trigger_auth_broken(self):
        tracker = HealthTracker()
        for _ in range(5):
            tracker.record_failure("groq", "server error", status_code=500)
        assert tracker.get("groq").auth_broken is False

    def test_non_auth_error_resets_auth_failure_counter(self):
        tracker = HealthTracker()
        tracker.record_failure("groq", "unauthorized", status_code=401)
        tracker.record_failure("groq", "unauthorized", status_code=401)
        tracker.record_failure("groq", "server error", status_code=500)  # resets counter
        tracker.record_failure("groq", "unauthorized", status_code=401)
        tracker.record_failure("groq", "unauthorized", status_code=401)
        assert tracker.get("groq").auth_broken is False  # only 2 since reset

    def test_auth_broken_excluded_from_get_sorted(self):
        tracker = HealthTracker()
        for _ in range(3):
            tracker.record_failure("groq", "unauthorized", status_code=401)
        result = tracker.get_sorted(["groq"])
        assert result == []

    def test_success_clears_auth_broken(self):
        tracker = HealthTracker()
        for _ in range(3):
            tracker.record_failure("groq", "unauthorized", status_code=401)
        tracker.record_success("groq", latency_ms=100.0)
        assert tracker.get("groq").auth_broken is False


class TestAllProvidersExhausted:
    def test_is_exception_subclass(self):
        exc = AllProvidersExhausted("fast")
        assert isinstance(exc, Exception)
        assert "fast" in str(exc)
