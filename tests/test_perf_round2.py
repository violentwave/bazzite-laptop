"""Tests for P40 performance round 2: caching, metrics, router reset, client reuse."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

# ── RateLimiter stale entry pruning ──────────────────────────────────────────


class TestRateLimiterPruning:
    """Tests for prune_stale_entries()."""

    @pytest.fixture()
    def limiter_with_state(self, tmp_path):
        """RateLimiter with pre-populated stale and fresh entries."""
        from ai.rate_limiter import RateLimiter

        state_file = tmp_path / "state.json"
        defs_file = tmp_path / "defs.json"
        defs_file.write_text(json.dumps({"llm_providers": {}, "threat_intel": {}}))

        stale_time = time.time() - 120  # 2 minutes ago
        stale_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stale_time))
        today = time.strftime("%Y-%m-%d")

        state = {
            "stale_provider": {
                "calls_this_minute": 0,
                "minute_start": stale_iso,
                "calls_this_hour": 0,
                "hour_start": stale_iso,
                "calls_today": 0,
                "day_date": today,
            },
            "fresh_provider": {
                "calls_this_minute": 5,
                "minute_start": stale_iso,
                "calls_this_hour": 5,
                "hour_start": stale_iso,
                "calls_today": 5,
                "day_date": today,
            },
            "not_a_provider": {"some": "other_data"},
        }
        state_file.write_text(json.dumps(state))

        return RateLimiter(state_path=state_file, definitions_path=defs_file, use_memory=False)

    def test_prune_removes_stale_zero_counter_entries(self, limiter_with_state):
        """Entries with all zero counters and expired minute window should be removed."""
        removed = limiter_with_state.prune_stale_entries()
        assert removed == 1

        state = limiter_with_state._read_state()
        assert "stale_provider" not in state
        assert "fresh_provider" in state
        assert "not_a_provider" in state

    def test_prune_returns_zero_when_no_stale(self, tmp_path):
        """When no entries are stale, prune should return 0."""
        from ai.rate_limiter import RateLimiter

        state_file = tmp_path / "state.json"
        defs_file = tmp_path / "defs.json"
        defs_file.write_text(json.dumps({"llm_providers": {}, "threat_intel": {}}))

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        today = time.strftime("%Y-%m-%d")
        state = {
            "active_provider": {
                "calls_this_minute": 3,
                "minute_start": now_iso,
                "calls_this_hour": 10,
                "hour_start": now_iso,
                "calls_today": 50,
                "day_date": today,
            },
        }
        state_file.write_text(json.dumps(state))

        limiter = RateLimiter(state_path=state_file, definitions_path=defs_file, use_memory=False)
        removed = limiter.prune_stale_entries()
        assert removed == 0

    def test_prune_handles_empty_state(self, tmp_path):
        """Empty state file should return 0 and not crash."""
        from ai.rate_limiter import RateLimiter

        state_file = tmp_path / "state.json"
        defs_file = tmp_path / "defs.json"
        defs_file.write_text(json.dumps({"llm_providers": {}, "threat_intel": {}}))
        state_file.write_text("{}")

        limiter = RateLimiter(state_path=state_file, definitions_path=defs_file, use_memory=False)
        removed = limiter.prune_stale_entries()
        assert removed == 0

    def test_prune_handles_missing_state(self, tmp_path):
        """Missing state file should return 0 and not crash."""
        from ai.rate_limiter import RateLimiter

        state_file = tmp_path / "state.json"
        defs_file = tmp_path / "defs.json"
        defs_file.write_text(json.dumps({"llm_providers": {}, "threat_intel": {}}))

        limiter = RateLimiter(state_path=state_file, definitions_path=defs_file, use_memory=False)
        removed = limiter.prune_stale_entries()
        assert removed == 0


# ── Metrics module ───────────────────────────────────────────────────────────


class TestMetricsModule:
    """Tests for ai.metrics module."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Clear metrics before and after each test."""
        from ai.metrics import reset_metrics

        reset_metrics()
        yield
        reset_metrics()

    def test_track_performance_records_calls(self):
        """Decorator should increment call count and record latency."""
        from ai.metrics import get_metrics, track_performance

        @track_performance
        def dummy():
            return 42

        dummy()
        dummy()

        stats = get_metrics()
        dummy_key = [k for k in stats if k.endswith("dummy")][0]
        assert stats[dummy_key]["calls"] == 2
        assert stats[dummy_key]["errors"] == 0
        assert stats[dummy_key]["total_ms"] > 0

    def test_track_performance_records_errors(self):
        """Decorator should increment error count on exception."""
        from ai.metrics import get_metrics, track_performance

        @track_performance
        def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            failing()

        stats = get_metrics()
        failing_key = [k for k in stats if k.endswith("failing")][0]
        assert stats[failing_key]["calls"] == 1
        assert stats[failing_key]["errors"] == 1

    def test_track_performance_preserves_exception(self):
        """Decorator should re-raise the original exception."""
        from ai.metrics import track_performance

        @track_performance
        def raises():
            raise RuntimeError("test")

        with pytest.raises(RuntimeError, match="test"):
            raises()

    def test_get_metrics_returns_all(self):
        """get_metrics() without name should return all entries."""
        from ai.metrics import get_metrics, track_performance

        @track_performance
        def fn_a():
            pass

        @track_performance
        def fn_b():
            pass

        fn_a()
        fn_b()
        fn_b()

        all_metrics = get_metrics()
        fn_a_key = [k for k in all_metrics if k.endswith("fn_a")][0]
        fn_b_key = [k for k in all_metrics if k.endswith("fn_b")][0]
        assert all_metrics[fn_a_key]["calls"] == 1
        assert all_metrics[fn_b_key]["calls"] == 2

    def test_get_metrics_unknown_name_returns_empty(self):
        """get_metrics('unknown') should return empty dict."""
        from ai.metrics import get_metrics

        stats = get_metrics("nonexistent")
        assert stats == {}

    def test_reset_metrics_clears_all(self):
        """reset_metrics() should clear all entries."""
        from ai.metrics import get_metrics, reset_metrics, track_performance

        @track_performance
        def tracked():
            pass

        tracked()
        reset_metrics()
        assert get_metrics() == {}

    def test_reset_metrics_single_name(self):
        """reset_metrics(name) should clear only that entry."""
        from ai.metrics import get_metrics, reset_metrics, track_performance

        @track_performance
        def fn_a():
            pass

        @track_performance
        def fn_b():
            pass

        fn_a()
        fn_b()
        reset_metrics([k for k in get_metrics() if k.endswith("fn_a")][0])

        all_metrics = get_metrics()
        assert not any(k.endswith("fn_a") for k in all_metrics)
        assert any(k.endswith("fn_b") for k in all_metrics)

    def test_record_metric(self):
        """record_metric should add to the metrics store."""
        from ai.metrics import get_metrics, record_metric

        record_metric("tokens.total", 1500)
        record_metric("tokens.total", 2000)

        stats = get_metrics("tokens.total")
        assert stats["calls"] == 2
        assert stats["total_ms"] == 3500

    def test_avg_ms_included_when_calls_gt_zero(self):
        """avg_ms should be computed when calls > 0."""
        from ai.metrics import get_metrics, track_performance

        @track_performance
        def slow():
            time.sleep(0.01)

        slow()
        stats = get_metrics()
        slow_key = [k for k in stats if k.endswith("slow")][0]
        assert "avg_ms" in stats[slow_key]
        assert stats[slow_key]["avg_ms"] > 0

    def test_avg_ms_not_included_when_no_calls(self):
        """avg_ms should not be present when there are no calls."""
        from ai.metrics import get_metrics

        stats = get_metrics("never_called")
        assert "avg_ms" not in stats


# ── Threat intel parallel lookup ─────────────────────────────────────────────


class TestParallelLookup:
    """Tests for async parallel lookup in threat_intel/lookup.py."""

    @pytest.fixture()
    def mock_limiter(self):
        limiter = MagicMock()
        limiter.can_call.return_value = True
        limiter.wait_time.return_value = 0.0
        return limiter

    def test_parallel_flag_runs_all_providers(self, mock_limiter):
        """parallel=True should call all providers concurrently."""
        from ai.threat_intel.lookup import lookup_hash
        from ai.threat_intel.models import ThreatReport

        call_order = []

        def make_provider(name):
            def _fn(sha256, rl):
                call_order.append(name)
                time.sleep(0.01)
                return ThreatReport(
                    hash=sha256,
                    source=name,
                    family=f"family_{name}",
                    risk_level="low",
                    timestamp="2026-01-01T00:00:00+00:00",
                )

            return _fn

        with (
            patch("ai.threat_intel.lookup._lookup_virustotal", side_effect=make_provider("vt")),
            patch("ai.threat_intel.lookup._lookup_otx", side_effect=make_provider("otx")),
            patch("ai.threat_intel.lookup._lookup_malwarebazaar", side_effect=make_provider("mb")),
        ):
            result = lookup_hash("a" * 64, rate_limiter=mock_limiter, parallel=True)

        assert result.source == "vt"
        assert len(call_order) == 3

    def test_sequential_mode_stops_on_first_hit(self, mock_limiter):
        """parallel=False should cascade and stop on first hit."""
        from ai.threat_intel.lookup import lookup_hash
        from ai.threat_intel.models import ThreatReport

        mb_report = ThreatReport(
            hash="a" * 64,
            source="malwarebazaar",
            family="Emotet",
            risk_level="high",
            timestamp="2026-01-01T00:00:00+00:00",
        )

        with (
            patch("ai.threat_intel.lookup._lookup_malwarebazaar", return_value=mb_report),
            patch("ai.threat_intel.lookup._lookup_otx") as mock_otx,
            patch("ai.threat_intel.lookup._lookup_virustotal") as mock_vt,
        ):
            result = lookup_hash("a" * 64, rate_limiter=mock_limiter, parallel=False)

        assert result.source == "malwarebazaar"
        mock_otx.assert_not_called()
        mock_vt.assert_not_called()

    def test_invalid_hash_returns_none_source(self, mock_limiter):
        """Invalid SHA256 should return source='none'."""
        from ai.threat_intel.lookup import lookup_hash

        result = lookup_hash("not-a-hash", rate_limiter=mock_limiter)
        assert result.source == "none"
        assert result.description == "Invalid SHA256 hash"


# ── MCP perf_metrics tool ────────────────────────────────────────────────────


class TestPerfMetricsTool:
    """Tests for system.perf_metrics MCP tool."""

    def test_perf_metrics_returns_data(self):
        """The underlying metrics functions should work correctly."""
        from ai.metrics import get_metrics, reset_metrics, track_performance

        @track_performance
        def test_fn():
            return "ok"

        test_fn()
        test_fn()

        all_metrics = get_metrics()
        test_key = [k for k in all_metrics if k.endswith("test_fn")][0]
        assert all_metrics[test_key]["calls"] == 2

        reset_metrics()
        assert get_metrics() == {}

    def test_perf_metrics_handler_logic(self):
        """Test the handler logic directly without FastMCP."""
        from ai.metrics import get_metrics, reset_metrics, track_performance

        @track_performance
        def handler_fn():
            return "ok"

        handler_fn()

        # Simulate the handler logic
        def _handler_perf_metrics(function=None, reset=False):
            try:
                if reset:
                    reset_metrics(function)
                    return {"status": "reset", "function": function}
                if function:
                    return {function: get_metrics(function)}
                return get_metrics()
            except Exception as e:
                return {"error": str(e)}

        result = _handler_perf_metrics(function=None, reset=False)
        assert any(k.endswith("handler_fn") for k in result)

        result = _handler_perf_metrics(function=None, reset=True)
        assert result["status"] == "reset"
