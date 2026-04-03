"""Test RAG query disk caching."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clear_rag_cache(tmp_path):
    """Point _rag_cache at a temp dir so tests are isolated."""
    import ai.rag.query as query_mod
    from ai.cache import JsonFileCache

    original = query_mod._rag_cache
    query_mod._rag_cache = JsonFileCache(tmp_path / "rag-cache", default_ttl=300)
    yield
    query_mod._rag_cache = original


def test_rag_cache_hit_skips_embed(tmp_path):
    """Second identical call hits cache and does not re-embed."""
    from ai.rag.query import rag_query

    mock_chunks = [{"text": "log line", "source_file": "test.log", "_distance": 0.1}]

    with patch("ai.rag.embedder.embed_single", return_value=[0.1] * 384) as mock_embed:
        with patch("ai.rag.store.get_store") as mock_store:
            store = MagicMock()
            store.search_logs.return_value = mock_chunks
            store.search_threats.return_value = []
            store.search_docs.return_value = []
            mock_store.return_value = store

            with patch("ai.rag.query.route_query", return_value="answer"):
                result1 = rag_query("test question")
                result2 = rag_query("test question")

    # embed_single should only be called once (second call hits cache)
    assert mock_embed.call_count == 1
    assert result1.answer == result2.answer
