"""Edge case tests for ai/rag/query.py - cache, rerank, error handling."""

from unittest.mock import MagicMock, patch

from ai.rag.query import (
    _cohere_rerank,
    _extract_sources,
    _safe_search,
    rag_query,
)


class TestCacheIntegration:
    """Test RAG cache behavior."""

    @patch("ai.rag.query.route_query")
    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    @patch("ai.rag.query._rag_cache")
    def test_cache_hit_skips_embedding_and_search(
        self, mock_cache, mock_embed, mock_store, mock_route
    ):
        """Cache hit should skip all processing."""
        mock_cache.get.return_value = {
            "question": "test?",
            "context_chunks": [{"text": "cached"}],
            "answer": "cached answer",
            "sources": ["cache.log"],
            "model_used": "fast",
        }

        result = rag_query("test?", use_llm=True)

        assert result.answer == "cached answer"
        # Should not call embed or search
        mock_embed.assert_not_called()
        mock_store.assert_not_called()
        mock_route.assert_not_called()

    @patch("ai.rag.query.route_query", return_value="answer")
    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single", return_value=[0.1] * 768)
    @patch("ai.rag.query._rag_cache")
    def test_cache_miss_stores_result(
        self, mock_cache, mock_embed, mock_store, mock_route
    ):
        """Cache miss should store result after computation."""
        mock_cache.get.return_value = None
        store_instance = MagicMock()
        store_instance.search_logs.return_value = [
            {"source_file": "test.log", "text": "data", "_distance": 0.1}
        ]
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        rag_query("test?", use_llm=True)

        # Should cache the result
        mock_cache.set.assert_called_once()
        cached_data = mock_cache.set.call_args[0][1]
        assert cached_data["answer"] == "answer"
        assert cached_data["question"] == "test?"

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single", return_value=[0.1] * 768)
    @patch("ai.rag.query._rag_cache")
    def test_empty_results_not_cached(
        self, mock_cache, mock_embed, mock_store
    ):
        """Empty results should not be cached."""
        mock_cache.get.return_value = None
        store_instance = MagicMock()
        store_instance.search_logs.return_value = []
        store_instance.search_threats.return_value = []
        store_instance.search_docs.return_value = []
        mock_store.return_value = store_instance

        rag_query("test?", use_llm=False)

        # Should not cache empty results
        mock_cache.set.assert_not_called()


class TestCohereRerank:
    """Test Cohere rerank functionality."""

    @patch.dict("os.environ", {"COHERE_API_KEY": ""})
    def test_skips_when_no_api_key(self):
        """Should skip reranking when COHERE_API_KEY is not set."""
        chunks = [{"text": "a"}, {"text": "b"}]
        limiter = MagicMock()

        result = _cohere_rerank("query", chunks, limiter)

        assert result == chunks  # Original order
        limiter.can_call.assert_not_called()

    @patch.dict("os.environ", {"COHERE_API_KEY": "test-key"})
    def test_skips_when_rate_limited(self):
        """Should skip reranking when rate limited."""
        chunks = [{"text": "a"}, {"text": "b"}]
        limiter = MagicMock()
        limiter.can_call.return_value = False

        result = _cohere_rerank("query", chunks, limiter)

        assert result == chunks  # Original order
        limiter.record_call.assert_not_called()

    @patch("cohere.ClientV2")
    @patch.dict("os.environ", {"COHERE_API_KEY": "test-key"})
    def test_reorders_by_relevance(self, mock_client_class):
        """Should reorder chunks by Cohere relevance score."""
        chunks = [
            {"text": "low relevance", "_distance": 0.1},
            {"text": "high relevance", "_distance": 0.5},
            {"text": "medium relevance", "_distance": 0.3},
        ]
        limiter = MagicMock()
        limiter.can_call.return_value = True

        # Mock Cohere to return indices in different order
        mock_result = MagicMock()
        mock_result.index = 1  # "high relevance" first
        mock_result2 = MagicMock()
        mock_result2.index = 2  # "medium relevance" second
        mock_response = MagicMock()
        mock_response.results = [mock_result, mock_result2]

        mock_client = MagicMock()
        mock_client.rerank.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = _cohere_rerank("query", chunks, limiter, top_n=2)

        assert len(result) == 2
        assert result[0]["text"] == "high relevance"
        assert result[1]["text"] == "medium relevance"
        limiter.record_call.assert_called_once_with("cohere_rerank")

    @patch("cohere.ClientV2")
    @patch.dict("os.environ", {"COHERE_API_KEY": "test-key"})
    def test_falls_back_on_error(self, mock_client_class):
        """Should return original order on Cohere error."""
        chunks = [{"text": "a"}, {"text": "b"}]
        limiter = MagicMock()
        limiter.can_call.return_value = True

        mock_client_class.side_effect = Exception("API error")

        result = _cohere_rerank("query", chunks, limiter)

        assert result == chunks  # Original order
        limiter.record_call.assert_not_called()

    @patch("cohere.ClientV2")
    @patch.dict("os.environ", {"COHERE_API_KEY": "test-key"})
    def test_extracts_text_from_content_field(self, mock_client_class):
        """Should handle chunks with 'content' instead of 'text'."""
        chunks = [
            {"content": "data1"},
            {"content": "data2"},
        ]
        limiter = MagicMock()
        limiter.can_call.return_value = True

        mock_response = MagicMock()
        mock_response.results = []
        mock_client = MagicMock()
        mock_client.rerank.return_value = mock_response
        mock_client_class.return_value = mock_client

        _cohere_rerank("query", chunks, limiter)

        # Should call rerank with extracted content
        call_args = mock_client.rerank.call_args
        assert call_args.kwargs["documents"] == ["data1", "data2"]


class TestSafeSearch:
    """Test safe search wrapper."""

    def test_successful_search(self):
        """Should return results from search method."""
        store = MagicMock()
        store.search_logs.return_value = [{"text": "result"}]

        result = _safe_search(store, "search_logs", [0.1] * 768, limit=5)

        assert result == [{"text": "result"}]

    def test_returns_empty_on_exception(self):
        """Should return empty list on search failure."""
        store = MagicMock()
        store.search_logs.side_effect = Exception("DB error")

        result = _safe_search(store, "search_logs", [0.1] * 768, limit=5)

        assert result == []

    def test_calls_correct_method(self):
        """Should call the specified method name."""
        store = MagicMock()
        store.custom_search.return_value = [{"data": "test"}]

        result = _safe_search(store, "custom_search", [0.1] * 768, limit=10)

        store.custom_search.assert_called_once_with([0.1] * 768, limit=10)
        assert result == [{"data": "test"}]


class TestExtractSources:
    """Test source extraction logic."""

    def test_extracts_source_file(self):
        """Should extract source_file as source."""
        chunks = [
            {"source_file": "/var/log/test.log", "text": "data"},
            {"source_file": "/var/log/test2.log", "text": "data2"},
        ]

        sources = _extract_sources(chunks)

        assert sources == ["/var/log/test.log", "/var/log/test2.log"]

    def test_extracts_source_field(self):
        """Should extract 'source' field if no source_file."""
        chunks = [
            {"source": "virustotal", "text": "threat data"},
        ]

        sources = _extract_sources(chunks)

        assert sources == ["virustotal"]

    def test_uses_hash_for_threats(self):
        """Should use threat:hash format for chunks with hash but no source."""
        chunks = [
            {"hash": "abc123def456", "text": "threat"},
        ]

        sources = _extract_sources(chunks)

        assert sources == ["threat:abc123def456"]

    def test_deduplicates_sources(self):
        """Should remove duplicate sources."""
        chunks = [
            {"source_file": "same.log", "text": "a"},
            {"source_file": "same.log", "text": "b"},
            {"source_file": "different.log", "text": "c"},
        ]

        sources = _extract_sources(chunks)

        assert sources == ["same.log", "different.log"]

    def test_preserves_order(self):
        """Should preserve order of first occurrence."""
        chunks = [
            {"source_file": "b.log", "text": "data"},
            {"source_file": "a.log", "text": "data"},
            {"source_file": "b.log", "text": "data"},  # duplicate
        ]

        sources = _extract_sources(chunks)

        assert sources == ["b.log", "a.log"]

    def test_skips_chunks_without_any_source(self):
        """Should skip chunks that have no source identifiers."""
        chunks = [
            {"text": "no source"},
            {"source_file": "has_source.log", "text": "data"},
        ]

        sources = _extract_sources(chunks)

        assert sources == ["has_source.log"]


class TestParallelSearch:
    """Test parallel table search behavior."""

    @patch("ai.rag.query.route_query", return_value="answer")
    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single", return_value=[0.1] * 768)
    def test_searches_all_tables_in_parallel(
        self, mock_embed, mock_store, mock_route
    ):
        """Should search logs, threats, and docs tables."""
        store_instance = MagicMock()
        store_instance.search_logs.return_value = [{"text": "log"}]
        store_instance.search_threats.return_value = [{"text": "threat"}]
        store_instance.search_docs.return_value = [{"text": "doc"}]
        mock_store.return_value = store_instance

        result = rag_query("test?", limit=5, use_llm=True)

        # All three search methods should be called
        store_instance.search_logs.assert_called_once()
        store_instance.search_threats.assert_called_once()
        store_instance.search_docs.assert_called_once()
        assert len(result.context_chunks) == 3

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single", return_value=[0.1] * 768)
    def test_one_table_failure_doesnt_block_others(
        self, mock_embed, mock_store
    ):
        """If one table search fails, others should still work."""
        store_instance = MagicMock()
        store_instance.search_logs.side_effect = Exception("DB error")
        store_instance.search_threats.return_value = [{"text": "threat"}]
        store_instance.search_docs.return_value = [{"text": "doc"}]
        mock_store.return_value = store_instance

        result = rag_query("test?", use_llm=False)

        # Should have 2 results (threats + docs)
        assert len(result.context_chunks) == 2
