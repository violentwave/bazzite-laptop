"""Cross-script rate limit coordinator for the Bazzite AI layer.

Tracks API call counts and timestamps across script invocations using a
persistent JSON state file. Uses atomic writes (tmp + os.rename) and file
locking (fcntl.flock) to prevent corruption from concurrent access.

Usage:
    limiter = RateLimiter()
    if limiter.can_call("virustotal"):
        limiter.record_call("virustotal")
        # ... make the API call ...
    else:
        wait = limiter.wait_time("virustotal")
        print(f"Rate limited. Try again in {wait:.0f}s")
"""

import fcntl
import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

from ai.config import APP_NAME, RATE_LIMITS_DEF, RATE_LIMITS_STATE

logger = logging.getLogger(APP_NAME)


class RateLimiter:
    """Coordinates rate limits across all API providers.

    Args:
        state_path: Path to the runtime state JSON file.
        definitions_path: Path to the static rate limit definitions JSON file.
    """

    def __init__(
        self,
        state_path: Path | None = None,
        definitions_path: Path | None = None,
    ) -> None:
        self.state_path = state_path or RATE_LIMITS_STATE
        self.definitions_path = definitions_path or RATE_LIMITS_DEF
        self._definitions = self._load_definitions()

    def _load_definitions(self) -> dict[str, dict]:
        """Load static rate limit definitions, flattening provider categories."""
        try:
            with open(self.definitions_path) as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Could not load rate limit definitions: %s", e)
            return {}

        flat: dict[str, dict] = {}
        for category in ("llm_providers", "threat_intel"):
            for provider, limits in raw.get(category, {}).items():
                flat[provider] = limits
        return flat

    def _read_state(self) -> dict:
        """Read the current state file. Returns empty dict if missing/corrupt."""
        try:
            with open(self.state_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
            return {}

    def _write_state(self, state: dict) -> None:
        """Atomic write: write to tmp file then os.rename() over the real file.

        Follows the exact pattern from clamav-scan.sh write_status():
        read existing → update → write tmp → rename.
        """
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_path, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            os.rename(tmp_path, self.state_path)
        except (PermissionError, OSError) as e:
            logger.warning("Failed to write rate limiter state: %s", e)
            # Clean up tmp file on failure
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _get_provider_state(self, state: dict, provider: str) -> dict:
        """Get a provider's state entry, resetting stale windows."""
        now = time.time()
        today = date.today().isoformat()

        entry = state.get(provider, {
            "calls_this_minute": 0,
            "minute_start": datetime.fromtimestamp(now).isoformat(),
            "calls_today": 0,
            "day_date": today,
        })

        # Reset minute window if >60s elapsed
        try:
            minute_start = datetime.fromisoformat(entry["minute_start"]).timestamp()
        except (ValueError, KeyError):
            minute_start = 0.0

        if now - minute_start > 60:
            entry["calls_this_minute"] = 0
            entry["minute_start"] = datetime.fromtimestamp(now).isoformat()

        # Reset daily window on new calendar day
        if entry.get("day_date") != today:
            entry["calls_today"] = 0
            entry["day_date"] = today

        return entry

    def can_call(self, provider: str) -> bool:
        """Check if calling this provider would stay within rate limits."""
        limits = self._definitions.get(provider)
        if limits is None:
            # Unknown provider — allow by default but log
            logger.debug("No rate limit definition for provider '%s', allowing", provider)
            return True

        state = self._read_state()
        entry = self._get_provider_state(state, provider)

        rpm = limits.get("rpm")
        if rpm is not None and entry["calls_this_minute"] >= rpm:
            return False

        rpd = limits.get("rpd")
        if rpd is not None and entry["calls_today"] >= rpd:
            return False

        return True

    def record_call(self, provider: str) -> None:
        """Record that an API call was made to this provider."""
        state = self._read_state()
        entry = self._get_provider_state(state, provider)
        entry["calls_this_minute"] += 1
        entry["calls_today"] += 1
        state[provider] = entry
        self._write_state(state)

    def wait_time(self, provider: str) -> float:
        """Seconds to wait before the next allowed call. 0.0 if can call now."""
        limits = self._definitions.get(provider)
        if limits is None:
            return 0.0

        state = self._read_state()
        entry = self._get_provider_state(state, provider)

        # Check daily limit first — if exhausted, wait until midnight
        rpd = limits.get("rpd")
        if rpd is not None and entry["calls_today"] >= rpd:
            now = datetime.now()
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            # Seconds until next midnight
            seconds_left = 86400 - (now - midnight).total_seconds()
            return max(seconds_left, 0.0)

        # Check minute limit
        rpm = limits.get("rpm")
        if rpm is not None and entry["calls_this_minute"] >= rpm:
            try:
                minute_start = datetime.fromisoformat(entry["minute_start"]).timestamp()
            except (ValueError, KeyError):
                return 0.0
            elapsed = time.time() - minute_start
            return max(60.0 - elapsed, 0.0)

        return 0.0
