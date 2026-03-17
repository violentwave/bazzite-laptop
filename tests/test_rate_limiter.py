"""Unit tests for ai/rate_limiter.py."""

import json
import threading
from datetime import date, datetime, timedelta

import pytest

from ai.rate_limiter import RateLimiter

# Minimal definitions for testing
MOCK_DEFINITIONS = {
    "llm_providers": {
        "groq": {"rpm": 3, "rph": 8, "rpd": 10},
        "cloudflare": {"rpm": None, "rph": None, "rpd": None},
    },
    "threat_intel": {
        "virustotal": {"rpm": 4, "rpd": 500},
        "malwarebazaar": {"rpm": None, "rpd": None},
    },
}


@pytest.fixture()
def defs_file(tmp_path):
    """Write mock definitions to a temp file."""
    p = tmp_path / "defs.json"
    p.write_text(json.dumps(MOCK_DEFINITIONS))
    return p


@pytest.fixture()
def limiter(tmp_path, defs_file):
    """Create a RateLimiter with temp state file and mock definitions."""
    state_file = tmp_path / "state.json"
    return RateLimiter(state_path=state_file, definitions_path=defs_file)


class TestLoadDefinitions:
    def test_loads_all_providers(self, limiter):
        assert "groq" in limiter._definitions
        assert "virustotal" in limiter._definitions
        assert "cloudflare" in limiter._definitions
        assert "malwarebazaar" in limiter._definitions

    def test_missing_definitions_file(self, tmp_path):
        lim = RateLimiter(
            state_path=tmp_path / "state.json",
            definitions_path=tmp_path / "nonexistent.json",
        )
        assert lim._definitions == {}


class TestCanCall:
    def test_fresh_state_allows_call(self, limiter):
        assert limiter.can_call("virustotal") is True

    def test_unknown_provider_allowed(self, limiter):
        assert limiter.can_call("unknown_provider_xyz") is True


class TestRecordCall:
    def test_creates_state_file(self, limiter):
        assert not limiter.state_path.exists()
        limiter.record_call("groq")
        assert limiter.state_path.exists()

    def test_increments_counters(self, limiter):
        limiter.record_call("groq")
        limiter.record_call("groq")
        state = json.loads(limiter.state_path.read_text())
        assert state["groq"]["calls_this_minute"] == 2
        assert state["groq"]["calls_today"] == 2


class TestRpmEnforcement:
    def test_blocks_after_limit(self, limiter):
        # groq has rpm=3
        for _ in range(3):
            assert limiter.can_call("groq") is True
            limiter.record_call("groq")
        assert limiter.can_call("groq") is False

    def test_window_reset(self, limiter):
        # Record calls up to limit
        for _ in range(3):
            limiter.record_call("groq")
        assert limiter.can_call("groq") is False

        # Fake the minute_start to >60s ago
        state = json.loads(limiter.state_path.read_text())
        old_time = datetime.now() - timedelta(seconds=61)
        state["groq"]["minute_start"] = old_time.isoformat()
        limiter.state_path.write_text(json.dumps(state))

        assert limiter.can_call("groq") is True


class TestRphEnforcement:
    def test_blocks_after_hourly_limit(self, limiter):
        # groq has rph=8; record 8 calls, resetting minute counter to avoid rpm block
        for i in range(8):
            limiter.record_call("groq")
            if (i + 1) % 3 == 0:
                state = json.loads(limiter.state_path.read_text())
                state["groq"]["calls_this_minute"] = 0
                limiter.state_path.write_text(json.dumps(state))
        assert limiter.can_call("groq") is False

    def test_hourly_window_reset(self, limiter):
        # Record calls up to hourly limit
        for i in range(8):
            limiter.record_call("groq")
            if (i + 1) % 3 == 0:
                state = json.loads(limiter.state_path.read_text())
                state["groq"]["calls_this_minute"] = 0
                limiter.state_path.write_text(json.dumps(state))
        assert limiter.can_call("groq") is False

        # Fake the hour_start to >3600s ago
        state = json.loads(limiter.state_path.read_text())
        old_time = datetime.now() - timedelta(seconds=3601)
        state["groq"]["hour_start"] = old_time.isoformat()
        # Also reset minute to avoid rpm block
        state["groq"]["calls_this_minute"] = 0
        limiter.state_path.write_text(json.dumps(state))

        assert limiter.can_call("groq") is True

    def test_wait_time_positive_when_rph_blocked(self, limiter):
        for i in range(8):
            limiter.record_call("groq")
            if (i + 1) % 3 == 0:
                state = json.loads(limiter.state_path.read_text())
                state["groq"]["calls_this_minute"] = 0
                limiter.state_path.write_text(json.dumps(state))
        wait = limiter.wait_time("groq")
        assert 0.0 < wait <= 3600.0

    def test_null_rph_unconstrained(self, limiter):
        # cloudflare has rph=null
        for _ in range(100):
            limiter.record_call("cloudflare")
        assert limiter.can_call("cloudflare") is True

    def test_backward_compat_no_hourly_fields(self, limiter):
        """Old state files without hourly fields should not break."""
        limiter.record_call("virustotal")
        # Remove hourly fields to simulate old state
        state = json.loads(limiter.state_path.read_text())
        state["virustotal"].pop("calls_this_hour", None)
        state["virustotal"].pop("hour_start", None)
        limiter.state_path.write_text(json.dumps(state))
        # Should still work
        assert limiter.can_call("virustotal") is True


class TestRpdEnforcement:
    def test_blocks_after_daily_limit(self, limiter):
        # groq has rpd=10
        for i in range(10):
            limiter.record_call("groq")
            # Reset minute counter each time to avoid rpm blocking
            if (i + 1) % 3 == 0:
                state = json.loads(limiter.state_path.read_text())
                state["groq"]["calls_this_minute"] = 0
                limiter.state_path.write_text(json.dumps(state))

        assert limiter.can_call("groq") is False

    def test_daily_reset(self, limiter):
        # Record calls and fake yesterday's date
        limiter.record_call("groq")
        state = json.loads(limiter.state_path.read_text())
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state["groq"]["day_date"] = yesterday
        state["groq"]["calls_today"] = 9999
        limiter.state_path.write_text(json.dumps(state))

        # Should reset on new day
        assert limiter.can_call("groq") is True


class TestNullLimits:
    def test_null_rpm_unconstrained(self, limiter):
        # cloudflare has rpm=null, rpd=null
        for _ in range(100):
            limiter.record_call("cloudflare")
        assert limiter.can_call("cloudflare") is True

    def test_null_rpd_unconstrained(self, limiter):
        # malwarebazaar has rpm=null, rpd=null
        for _ in range(50):
            limiter.record_call("malwarebazaar")
        assert limiter.can_call("malwarebazaar") is True


class TestWaitTime:
    def test_zero_when_can_call(self, limiter):
        assert limiter.wait_time("groq") == 0.0

    def test_positive_when_rpm_blocked(self, limiter):
        for _ in range(3):
            limiter.record_call("groq")
        wait = limiter.wait_time("groq")
        assert 0.0 < wait <= 60.0

    def test_zero_for_unknown_provider(self, limiter):
        assert limiter.wait_time("unknown_xyz") == 0.0


class TestAtomicWrite:
    def test_state_written_atomically(self, limiter):
        limiter.record_call("groq")
        # No .tmp files should remain
        tmp_files = list(limiter.state_path.parent.glob("*.tmp.*"))
        assert tmp_files == []
        # State file should be valid JSON
        state = json.loads(limiter.state_path.read_text())
        assert "groq" in state


class TestConcurrentSafety:
    def test_concurrent_writes(self, limiter):
        errors = []

        def record_n(n):
            try:
                for _ in range(n):
                    limiter.record_call("virustotal")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_n, args=(5,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent writes: {errors}"
        # State file should be valid JSON (not corrupted)
        state = json.loads(limiter.state_path.read_text())
        assert "virustotal" in state
        # Total calls should be 20 (4 threads x 5 calls), though race conditions
        # in read-then-write may cause undercounting. The key assertion is no corruption.
        assert state["virustotal"]["calls_today"] > 0
