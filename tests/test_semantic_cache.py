"""Tests for ai/cache_semantic.py SemanticCache."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.cache_semantic import SemanticCache


class TestSemanticCache:
    def test_semantic_cache_hit(self, tmp_path):
        """Test semantic cache hit with similar query."""
        cache = SemanticCache(similarity_threshold=0.85, db_path=str(tmp_path))

        cache.put(
            "What CVEs affect my system?",
            {"answer": "none"},
            "fast",
        )

        result = cache.get("What CVEs are in my system?", "fast")

        assert result is not None
        assert result.get("answer") == "none"

    def test_semantic_cache_miss(self, tmp_path):
        """Test semantic cache miss for unrelated query."""
        cache = SemanticCache(db_path=str(tmp_path))

        cache.put(
            "What is the weather?",
            {"answer": "sunny"},
            "fast",
        )

        result = cache.get("Show me all running systemd timers", "fast")

        assert result is None

    def test_semantic_cache_ttl_expired(self, tmp_path):
        """Test TTL expiration removes cached entry."""
        cache = SemanticCache(db_path=str(tmp_path))
        table = cache._get_or_create_table()

        table.add(
            [
                {
                    "id": "test-id",
                    "query": "test query",
                    "response": json.dumps({"answer": "x"}),
                    "task_type": "fast",
                    "cached_at": datetime.now(UTC).isoformat(),
                    "hit_count": 0,
                    "vector": [0.0] * 768,
                }
            ]
        )

        with patch("ai.cache_semantic.datetime") as mock_datetime:
            future_time = datetime.now(UTC).timestamp() + (2 * 60 * 60) + 1
            mock_datetime.now.return_value = datetime.fromtimestamp(future_time, UTC)
            mock_datetime.fromisoformat = datetime.fromisoformat

            result = cache.get("test query", "fast")

        assert result is None

    def test_semantic_cache_task_type_filter(self, tmp_path):
        """Test task_type filter blocks cross-type hits."""
        cache = SemanticCache(db_path=str(tmp_path))

        cache.put(
            "list all threats",
            {"answer": "none"},
            "fast",
        )

        result = cache.get("list all threats", "reason")

        assert result is None

    def test_semantic_cache_rejects_invalid_task_type(self, tmp_path):
        """Test that get() raises ValueError for unknown task_type."""
        cache = SemanticCache(db_path=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid task_type"):
            cache.get("some query", "unknown_type")
