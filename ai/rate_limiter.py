"""Cross-script rate limit coordinator for the Bazzite AI layer.

Tracks API call counts and timestamps across script invocations using a
persistent JSON state file. Uses atomic writes (tmp + os.rename) and file
locking (fcntl.flock) to prevent corruption from concurrent access.

Supports in-memory caching with background flush for high-frequency calls.

Usage:
    limiter = RateLimiter()
    if limiter.can_call("virustotal"):
        limiter.record_call("virustotal")
        # ... make the API call ...
    else:
        wait = limiter.wait_time("virustotal")
        print(f"Rate limited. Try again in {wait:.0f}s")
"""

import atexit
import fcntl
import json
import logging
import os
import tempfile
import threading
import time
from datetime import date, datetime
from pathlib import Path

from ai.config import APP_NAME, RATE_LIMITS_DEF, RATE_LIMITS_STATE

logger = logging.getLogger(APP_NAME)

_FLUSH_INTERVAL_SEC = 60
_memory_cache: dict[str, dict] = {}
_cache_lock = threading.RLock()
_flush_thread: threading.Thread | None = None
_shutdown = threading.Event()


class RateLimiter:
    """Coordinates rate limits across all API providers.

    Supports in-memory caching for high-frequency calls with background
    flush to disk.

    Args:
        state_path: Path to the runtime state JSON file.
        definitions_path: Path to the static rate limit definitions JSON file.
        use_memory: Enable in-memory caching (default True).
    """

    def __init__(
        self,
        state_path: Path | None = None,
        definitions_path: Path | None = None,
        use_memory: bool = True,
    ) -> None:
        self.state_path = state_path or RATE_LIMITS_STATE
        self.definitions_path = definitions_path or RATE_LIMITS_DEF
        self._definitions = self._load_definitions()
        self._use_memory = use_memory and state_path is None

        if self._use_memory:
            _start_flush_daemon()

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

    def _write_state(self, state: dict, _lock_f=None) -> None:
        """Atomic write: lock shared file, write tmp, rename over state file.

        Uses a dedicated .lock file for coordination (not the tmp file),
        ensuring concurrent writers serialize properly.

        Args:
            state: The state dict to persist.
            _lock_f: Optional pre-acquired lock file handle.  When provided
                the caller already holds LOCK_EX on the .lock file, so this
                method skips re-acquiring it (avoids same-process deadlock
                between different file descriptions).
        """
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_suffix(".lock")
        fd = None
        tmp_path = None
        own_lock = _lock_f is None

        try:
            fd, tmp_name = tempfile.mkstemp(
                dir=self.state_path.parent, prefix=".state-", suffix=".tmp"
            )
            tmp_path = Path(tmp_name)

            def _do_write(lock_fh):
                nonlocal fd, tmp_path
                with os.fdopen(fd, "w") as f:
                    fd = None  # os.fdopen takes ownership
                    json.dump(state, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.rename(tmp_path, self.state_path)
                tmp_path = None  # rename succeeded, nothing to clean up

            if own_lock:
                with open(lock_path, "w") as lock_fh:
                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
                    _do_write(lock_fh)
            else:
                _do_write(_lock_f)
        except (PermissionError, OSError) as e:
            logger.warning("Failed to write rate limiter state: %s", e)
        finally:
            if fd is not None:
                os.close(fd)
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _get_provider_state(self, state: dict, provider: str) -> dict:
        """Get a provider's state entry, resetting stale windows."""
        now = time.time()
        now_iso = datetime.fromtimestamp(now).isoformat()
        today = date.today().isoformat()

        entry = state.get(
            provider,
            {
                "calls_this_minute": 0,
                "minute_start": now_iso,
                "calls_this_hour": 0,
                "hour_start": now_iso,
                "calls_today": 0,
                "day_date": today,
            },
        )

        # Ensure hourly fields exist (backward compat with old state files)
        if "calls_this_hour" not in entry:
            entry["calls_this_hour"] = 0
            entry["hour_start"] = now_iso

        # Reset minute window if >60s elapsed
        try:
            minute_start = datetime.fromisoformat(entry["minute_start"]).timestamp()
        except (ValueError, KeyError):
            minute_start = 0.0

        if now - minute_start > 60:
            entry["calls_this_minute"] = 0
            entry["minute_start"] = now_iso

        # Reset hourly window if >3600s elapsed
        try:
            hour_start = datetime.fromisoformat(entry["hour_start"]).timestamp()
        except (ValueError, KeyError):
            hour_start = 0.0

        if now - hour_start > 3600:
            entry["calls_this_hour"] = 0
            entry["hour_start"] = now_iso

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

        rph = limits.get("rph")
        if rph is not None and entry["calls_this_hour"] >= rph:
            return False

        rpd = limits.get("rpd")
        if rpd is not None and entry["calls_today"] >= rpd:
            return False

        return True

    def record_call(self, provider: str) -> None:
        """Record that an API call was made to this provider.

        Uses in-memory cache with background flush when use_memory=True,
        otherwise falls back to direct file writes.
        """
        if self._use_memory:
            self._record_call_memory(provider)
        else:
            self._record_call_disk(provider)

    def _record_call_memory(self, provider: str) -> None:
        """Record to in-memory cache (fast path)."""
        now = time.time()
        now_iso = datetime.fromtimestamp(now).isoformat()
        today = date.today().isoformat()

        with _cache_lock:
            entry = _memory_cache.get(
                provider,
                {
                    "calls_this_minute": 0,
                    "minute_start": now_iso,
                    "calls_this_hour": 0,
                    "hour_start": now_iso,
                    "calls_today": 0,
                    "day_date": today,
                },
            )

            minute_start = entry.get("minute_start", now_iso)
            try:
                minute_ts = datetime.fromisoformat(minute_start).timestamp()
            except (ValueError, KeyError):
                minute_ts = 0.0

            if now - minute_ts > 60:
                entry["calls_this_minute"] = 0
                entry["minute_start"] = now_iso

            hour_start = entry.get("hour_start", now_iso)
            try:
                hour_ts = datetime.fromisoformat(hour_start).timestamp()
            except (ValueError, KeyError):
                hour_ts = 0.0

            if now - hour_ts > 3600:
                entry["calls_this_hour"] = 0
                entry["hour_start"] = now_iso

            if entry.get("day_date") != today:
                entry["calls_today"] = 0
                entry["day_date"] = today

            entry["calls_this_minute"] = entry.get("calls_this_minute", 0) + 1
            entry["calls_this_hour"] = entry.get("calls_this_hour", 0) + 1
            entry["calls_today"] = entry.get("calls_today", 0) + 1
            _memory_cache[provider] = entry

    def _record_call_disk(self, provider: str) -> None:
        """Record directly to disk (legacy path)."""
        lock_path = self.state_path.with_suffix(".lock")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(lock_path, "a") as lock_f:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                state = self._read_state()
                entry = self._get_provider_state(state, provider)
                entry["calls_this_minute"] += 1
                entry["calls_this_hour"] += 1
                entry["calls_today"] += 1
                state[provider] = entry
                self._write_state(state, _lock_f=lock_f)
        except (PermissionError, OSError) as e:
            logger.warning("Failed to record call: %s", e)

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

        # Check hourly limit
        rph = limits.get("rph")
        if rph is not None and entry["calls_this_hour"] >= rph:
            try:
                hour_start = datetime.fromisoformat(entry["hour_start"]).timestamp()
            except (ValueError, KeyError):
                return 0.0
            elapsed = time.time() - hour_start
            return max(3600.0 - elapsed, 0.0)

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

    def prune_stale_entries(self) -> int:
        """Remove stale provider entries from state file.

        An entry is considered stale if:
        - All counters are zero (calls_this_minute, calls_this_hour, calls_today)
        - The minute window has expired (>60s since minute_start)

        Returns the number of entries removed.
        """
        state = self._read_state()
        if not state:
            return 0

        now = time.time()
        stale_keys = []

        for provider, entry in state.items():
            # Skip if entry doesn't look like a rate limit entry
            if "calls_this_minute" not in entry:
                continue

            # Check if all counters are zero
            if (
                entry.get("calls_this_minute", 0) == 0
                and entry.get("calls_this_hour", 0) == 0
                and entry.get("calls_today", 0) == 0
            ):
                # Check if minute window has expired
                try:
                    minute_start = datetime.fromisoformat(entry["minute_start"]).timestamp()
                    if now - minute_start > 60:
                        stale_keys.append(provider)
                except (ValueError, KeyError):
                    # Invalid timestamp means stale
                    stale_keys.append(provider)

        if stale_keys:
            lock_path = self.state_path.with_suffix(".lock")
            try:
                with open(lock_path, "w") as lock_f:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                    for key in stale_keys:
                        state.pop(key, None)
                    self._write_state(state, _lock_f=lock_f)
            except (PermissionError, OSError) as e:
                logger.warning("Failed to prune stale entries: %s", e)
                return 0

        return len(stale_keys)


def _start_flush_daemon() -> None:
    """Start background thread to flush in-memory cache every 60s."""
    global _flush_thread

    if _flush_thread is not None and _flush_thread.is_alive():
        return

    _shutdown.clear()
    _flush_thread = threading.Thread(target=_flush_loop, daemon=True, name="rate-limiter-flush")
    _flush_thread.start()
    atexit.register(_flush_at_exit)


def _flush_loop() -> None:
    """Background flush loop - runs every 60s."""
    while not _shutdown.is_set():
        time.sleep(_FLUSH_INTERVAL_SEC)
        if _shutdown.is_set():
            break
        _flush_memory_cache()


def _flush_memory_cache() -> None:
    """Flush in-memory cache to disk (called by background thread)."""
    global _memory_cache

    with _cache_lock:
        if not _memory_cache:
            return
        cache_copy = _memory_cache.copy()
        _memory_cache.clear()

    if not cache_copy:
        return

    state_path = RATE_LIMITS_STATE
    lock_path = state_path.with_suffix(".lock")

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                with open(state_path) as f:
                    state = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                state = {}

            for provider, entry in cache_copy.items():
                existing = state.get(
                    provider,
                    {
                        "calls_this_minute": 0,
                        "calls_this_hour": 0,
                        "calls_today": 0,
                    },
                )
                existing["calls_this_minute"] = existing.get("calls_this_minute", 0) + entry.get(
                    "calls_this_minute", 0
                )
                existing["calls_this_hour"] = existing.get("calls_this_hour", 0) + entry.get(
                    "calls_this_hour", 0
                )
                existing["calls_today"] = existing.get("calls_today", 0) + entry.get(
                    "calls_today", 0
                )
                state[provider] = existing

            fd, tmp_name = tempfile.mkstemp(dir=state_path.parent, prefix=".state-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(state, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.rename(tmp_name, state_path)
            except Exception:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
    except Exception:
        with _cache_lock:
            for provider, entry in cache_copy.items():
                existing = _memory_cache.get(
                    provider,
                    {
                        "calls_this_minute": 0,
                        "calls_this_hour": 0,
                        "calls_today": 0,
                    },
                )
                existing["calls_this_minute"] = existing.get("calls_this_minute", 0) + entry.get(
                    "calls_this_minute", 0
                )
                existing["calls_this_hour"] = existing.get("calls_this_hour", 0) + entry.get(
                    "calls_this_hour", 0
                )
                existing["calls_today"] = existing.get("calls_today", 0) + entry.get(
                    "calls_today", 0
                )
                _memory_cache[provider] = existing


def _flush_at_exit() -> None:
    """Flush cache on process exit."""
    _shutdown.set()
    if _flush_thread is not None:
        _flush_thread.join(timeout=5)
    _flush_memory_cache()
