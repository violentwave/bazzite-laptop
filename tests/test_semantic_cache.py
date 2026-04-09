"""Tests for ai/cache_semantic.py SemanticCache."""

import json
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.cache_semantic import SemanticCache


def _ollama_running() -> bool:
    """Check if Ollama is reachable on localhost:11434."""
    try:
        with socket.create_connection(("localhost", 11434), timeout=1):
            return True
    except OSError:
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_running(),
    reason="Ollama not running on localhost:11434",
)


def _embed_via_ollama(text: str) -> list[float]:
    """Force Ollama for embedding — bypasses Cohere rate limits in tests."""
    from ai.rag.embedder import _embed_ollama
    return _embed_ollama([text])[0]


class TestSemanticCache:
    @requires_ollama
    def test_semantic_cache_hit(self, tmp_path):
        """Test semantic cache hit with similar query."""
        cache = SemanticCache(similarity_threshold=0.85, db_path=str(tmp_path))

        # Patch embed_single to force Ollama — Cohere trial key is rate-limited
        # (100 calls/month) which causes put() to silently store nothing.
        with patch("ai.cache_semantic.embed_single", side_effect=_embed_via_ollama):
            cache.put(
                "What CVEs affect my system?",
                {"answer": "none"},
                "fast",
            )

            result = cache.get("What CVEs are in my system?", "fast")

        assert result is not None
        assert result.get("answer") == "none"

    @requires_ollama
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
