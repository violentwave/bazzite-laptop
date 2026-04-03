"""JSON file cache for LLM responses.

Zero external dependencies. No pickle. No CVEs.
Each entry is a JSON file named by SHA256 hash, with 2-level directory sharding.
Atomic writes via tempfile + os.replace prevent partial files.
"""

import hashlib
import json
import logging
import os
import tempfile
import threading
import time
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class JsonFileCache:
    """Disk-based LLM response cache using JSON files. No pickle. No CVEs."""

    _eviction_running: bool = False
    _eviction_lock: threading.Lock = threading.Lock()

    def __init__(self, cache_dir: str | Path, default_ttl: int = 300):
        self._cache_dir = Path(cache_dir)
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hit_count = 0
        self._miss_count = 0
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # best-effort; reads/writes will fail gracefully
        with JsonFileCache._eviction_lock:
            if not JsonFileCache._eviction_running:
                JsonFileCache._eviction_running = True
                t = threading.Thread(target=self._auto_evict_loop, daemon=True)
                t.start()

    def _auto_evict_loop(self) -> None:
        while True:
            time.sleep(3600)
            try:
                count = self.evict_expired()
                if count > 0:
                    logger.info("Auto-evicted %d expired cache entries", count)
            except Exception:
                logger.warning("Auto-eviction failed", exc_info=True)

    @staticmethod
    @lru_cache(maxsize=10000)
    def _key_hash(key: str) -> str:
        """SHA256 hex digest of the key string, used as filename."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _entry_path(self, key_hash: str) -> Path:
        """2-level directory sharding: cache_dir/ab/abcdef...json"""
        shard = key_hash[:2]
        return self._cache_dir / shard / f"{key_hash}.json"

    def get(self, key: str) -> dict | None:
        """Return cached value if exists and not expired, else None."""
        key_hash = self._key_hash(key)
        path = self._entry_path(key_hash)
        try:
            data = json.loads(path.read_text())
            expires_at = data.get("expires_at", 0)
            if time.time() > expires_at:
                try:
                    path.unlink()
                except OSError:
                    pass
                with self._lock:
                    self._miss_count += 1
                return None
            with self._lock:
                self._hit_count += 1
            return data["value"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError, OSError):
            with self._lock:
                self._miss_count += 1
            return None

    def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        """Write value as JSON with expiry timestamp. Atomic write (tempfile + os.replace)."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        if effective_ttl == 0:
            return  # Never cache TTL=0 entries (e.g. embed type)

        key_hash = self._key_hash(key)
        path = self._entry_path(key_hash)
        now = time.time()
        entry = {
            "value": value,
            "expires_at": now + effective_ttl,
            "created_at": now,
            "key_preview": key[:80],
        }

        tmp_path: str | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json.tmp",
                dir=path.parent,
                delete=False,
            ) as f:
                json.dump(entry, f)
                tmp_path = f.name
            os.replace(tmp_path, path)
        except OSError:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def delete(self, key: str) -> bool:
        """Delete a cache entry. Return True if existed."""
        key_hash = self._key_hash(key)
        path = self._entry_path(key_hash)
        try:
            path.unlink()
            return True
        except (FileNotFoundError, OSError):
            return False

    def clear(self) -> int:
        """Delete all cache entries. Return count deleted."""
        count = 0
        try:
            for shard_dir in self._cache_dir.iterdir():
                if not shard_dir.is_dir():
                    continue
                for json_file in shard_dir.glob("*.json"):
                    try:
                        json_file.unlink()
                        count += 1
                    except OSError:
                        pass
        except OSError:
            pass
        return count

    def stats(self) -> dict:
        """Return cache statistics: entries, size, hit/miss counts, hit rate."""
        total_entries = 0
        total_size_bytes = 0
        try:
            for shard_dir in self._cache_dir.iterdir():
                if not shard_dir.is_dir():
                    continue
                for json_file in shard_dir.glob("*.json"):
                    total_entries += 1
                    try:
                        total_size_bytes += json_file.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass

        with self._lock:
            hits = self._hit_count
            misses = self._miss_count

        total = hits + misses
        hit_rate = hits / total if total > 0 else 0.0

        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size_bytes,
            "hit_count": hits,
            "miss_count": misses,
            "hit_rate": round(hit_rate, 4),
        }

    def evict_expired(self) -> int:
        """Remove all expired entries. Return count evicted."""
        count = 0
        now = time.time()
        try:
            for shard_dir in self._cache_dir.iterdir():
                if not shard_dir.is_dir():
                    continue
                for json_file in shard_dir.glob("*.json"):
                    try:
                        data = json.loads(json_file.read_text())
                        if now > data.get("expires_at", 0):
                            json_file.unlink()
                            count += 1
                    except (OSError, json.JSONDecodeError):
                        pass
        except OSError:
            pass
        return count


def get_cache_stats() -> dict:
    """MCP-callable function returning LLM cache statistics from disk."""
    ext = Path("/var/mnt/ext-ssd/bazzite-ai/llm-cache")
    internal = Path.home() / "security" / "llm-cache"
    cache_dir = ext if ext.parent.exists() else internal

    cache = JsonFileCache(cache_dir=cache_dir)
    result = cache.stats()
    result["cache_dir"] = str(cache_dir)
    return result
