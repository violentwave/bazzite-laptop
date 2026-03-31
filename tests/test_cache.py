"""Tests for ai/cache.py — JsonFileCache."""

import json
import threading
import time
from pathlib import Path

import pytest

from ai.cache import JsonFileCache


@pytest.fixture()
def cache(tmp_path):
    """Fresh JsonFileCache backed by a temp directory."""
    return JsonFileCache(cache_dir=tmp_path / "test-cache", default_ttl=300)


class TestBasicOperations:
    def test_set_and_get(self, cache):
        cache.set("k", {"hello": "world"}, ttl=60)
        result = cache.get("k")
        assert result == {"hello": "world"}

    def test_get_missing_key(self, cache):
        assert cache.get("nonexistent-key") is None

    def test_delete_existing(self, cache):
        cache.set("k", {"x": 1}, ttl=60)
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_delete_missing(self, cache):
        assert cache.delete("nonexistent") is False


class TestExpiry:
    def test_ttl_expiration(self, cache):
        cache.set("expiring", {"val": 42}, ttl=1)
        assert cache.get("expiring") is not None
        time.sleep(2)
        assert cache.get("expiring") is None

    def test_ttl_zero_skips_write(self, cache):
        cache.set("embed-key", {"vec": [1, 2, 3]}, ttl=0)
        assert cache.get("embed-key") is None

    def test_evict_expired(self, cache):
        cache.set("live", {"ok": True}, ttl=300)
        cache.set("dead", {"ok": False}, ttl=1)
        time.sleep(2)
        evicted = cache.evict_expired()
        assert evicted == 1
        assert cache.get("live") is not None


class TestAtomicWrite:
    def test_atomic_write_no_partial_files(self, cache):
        cache.set("safe-key", {"data": "value"}, ttl=60)
        key_hash = cache._key_hash("safe-key")
        path = cache._entry_path(key_hash)
        # Only the final .json should exist, no .tmp files
        tmp_files = list(path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0
        # The JSON file should be valid
        data = json.loads(path.read_text())
        assert data["value"] == {"data": "value"}


class TestClear:
    def test_clear_removes_all(self, cache):
        cache.set("a", {"v": 1}, ttl=60)
        cache.set("b", {"v": 2}, ttl=60)
        cache.set("c", {"v": 3}, ttl=60)
        count = cache.clear()
        assert count == 3
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None

    def test_clear_empty_cache(self, cache):
        assert cache.clear() == 0


class TestStats:
    def test_stats_keys_present(self, cache):
        s = cache.stats()
        for key in ("total_entries", "total_size_bytes", "hit_count", "miss_count", "hit_rate"):
            assert key in s

    def test_stats_counts_entries(self, cache):
        cache.set("x", {"v": 1}, ttl=60)
        cache.set("y", {"v": 2}, ttl=60)
        s = cache.stats()
        assert s["total_entries"] == 2
        assert s["total_size_bytes"] > 0


class TestHitMissCounters:
    def test_hit_miss_counters(self, cache):
        cache.set("hit-me", {"x": 1}, ttl=60)
        cache.get("hit-me")    # hit
        cache.get("missing-1") # miss
        cache.get("missing-2") # miss
        s = cache.stats()
        assert s["hit_count"] == 1
        assert s["miss_count"] == 2
        assert s["hit_rate"] == pytest.approx(1 / 3, abs=0.01)

    def test_hit_rate_zero_when_no_calls(self, cache):
        assert cache.stats()["hit_rate"] == 0.0


class TestDirectorySharding:
    def test_directory_sharding(self, cache):
        cache.set("shard-test", {"v": 1}, ttl=60)
        key_hash = cache._key_hash("shard-test")
        shard = key_hash[:2]
        path = cache._entry_path(key_hash)
        assert path.parent.name == shard
        assert path.parent.parent == cache._cache_dir
        assert path.exists()


class TestCorruptHandling:
    def test_corrupt_json_handled(self, cache):
        # Manually write garbage into a cache file location
        key = "corrupt-key"
        key_hash = cache._key_hash(key)
        path = cache._entry_path(key_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("NOT_VALID_JSON{{{{")
        # get() should return None, not raise
        assert cache.get(key) is None


class TestThreadSafety:
    def test_thread_safety(self, cache):
        errors: list[Exception] = []
        results: list[dict] = []

        def worker(idx: int) -> None:
            try:
                key = f"thread-key-{idx}"
                cache.set(key, {"idx": idx}, ttl=60)
                val = cache.get(key)
                if val is not None:
                    results.append(val)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert len(results) == 20


class TestNoPickle:
    def test_no_pickle_import(self):
        src = (Path(__file__).parent.parent / "ai" / "cache.py").read_text()
        assert "import pickle" not in src
        assert "import shelve" not in src
