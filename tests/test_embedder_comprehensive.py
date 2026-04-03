"""Comprehensive edge case tests for ai/rag/embedder.py."""

import time
from unittest.mock import MagicMock, patch

import pytest

from ai.rag.embedder import (
    EMBEDDING_DIM,
    _embed_gemini,
    _validate_dimensions,
    embed_single,
    embed_texts,
    select_provider,
)


class TestGeminiRetryLogic:
    """Test Gemini retry behavior with 429 errors."""

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    @patch("ai.rag.embedder.time.sleep")  # Mock sleep to speed up tests
    def test_gemini_retries_on_429(self, mock_sleep, _load, _get_key, mock_litellm):
        """Should retry up to 3 times on RateLimitError."""
        mock_litellm.RateLimitError = Exception  # Use base Exception for test
        mock_litellm.embedding.side_effect = [
            mock_litellm.RateLimitError("429"),
            mock_litellm.RateLimitError("429"),
            MagicMock(data=[{"embedding": [0.0] * EMBEDDING_DIM}]),
        ]

        result = _embed_gemini(["test"], rate_limiter=None)

        assert result is not None
        assert len(result) == 1
        assert mock_litellm.embedding.call_count == 3
        # Should wait progressively: 2s, 4s
        assert mock_sleep.call_count == 2

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    @patch("ai.rag.embedder.time.sleep")
    def test_gemini_gives_up_after_max_retries(self, mock_sleep, _load, _get_key, mock_litellm):
        """Should return None after 3 failed retries."""
        mock_litellm.RateLimitError = Exception
        mock_litellm.embedding.side_effect = mock_litellm.RateLimitError("429")

        result = _embed_gemini(["test"], rate_limiter=None)

        assert result is None
        assert mock_litellm.embedding.call_count == 3

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_gemini_batch_delay_between_texts(self, _load, _get_key, mock_litellm):
        """Should add delay between batch texts to avoid rate limits."""
        mock_litellm.embedding.return_value = MagicMock(
            data=[{"embedding": [0.0] * EMBEDDING_DIM}]
        )

        start = time.time()
        _embed_gemini(["text1", "text2", "text3"], rate_limiter=None)
        elapsed = time.time() - start

        # Should have 2 delays (100ms each) for 3 texts
        # Allow some margin for test execution
        assert elapsed >= 0.2  # 2 * 0.1s
        assert mock_litellm.embedding.call_count == 3


class TestDimensionValidation:
    """Test dimension validation edge cases."""

    @patch("ai.rag.embedder.logger")
    def test_warns_on_wrong_dimension(self, mock_logger):
        """Should warn when vector has wrong dimension."""
        wrong_dim_vectors = [[0.0] * 512]  # Wrong: 512 instead of 768

        _validate_dimensions(wrong_dim_vectors)

        mock_logger.warning.assert_called_once()
        assert "512" in str(mock_logger.warning.call_args)
        assert "768" in str(mock_logger.warning.call_args)

    @patch("ai.rag.embedder.logger")
    def test_no_warn_on_correct_dimension(self, mock_logger):
        """Should not warn when dimension is correct."""
        correct_vectors = [[0.0] * EMBEDDING_DIM]

        _validate_dimensions(correct_vectors)

        mock_logger.warning.assert_not_called()


class TestEmbedSingleCache:
    """Test LRU cache behavior in embed_single."""

    @patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * EMBEDDING_DIM])
    def test_cache_hit_avoids_recompute(self, mock_gemini):
        """Second call with same text should use cache."""
        # Clear cache
        from ai.rag.embedder import _embed_single_cached
        _embed_single_cached.cache_clear()

        result1 = embed_single("test text")
        result2 = embed_single("test text")

        # Only 1 call to gemini due to cache
        assert mock_gemini.call_count == 1
        assert result1 == result2

    @patch("ai.rag.embedder._embed_gemini")
    def test_cache_respects_input_type(self, mock_gemini):
        """Different input_type should not hit cache."""
        mock_gemini.return_value = [[0.1] * EMBEDDING_DIM]
        from ai.rag.embedder import _embed_single_cached
        _embed_single_cached.cache_clear()

        embed_single("test", input_type="search_document")
        embed_single("test", input_type="search_query")

        # Should be 2 calls - different input_type
        assert mock_gemini.call_count == 2

    @patch("ai.rag.embedder.embed_texts")
    def test_bypasses_cache_with_rate_limiter(self, mock_embed_texts):
        """Should bypass cache when rate_limiter is passed."""
        mock_embed_texts.return_value = [[0.1] * EMBEDDING_DIM]
        limiter = MagicMock()

        embed_single("test", rate_limiter=limiter)

        # Should call embed_texts directly, not cached version
        mock_embed_texts.assert_called_once()


class TestProviderFallbackChain:
    """Test provider fallback chain logic."""

    @patch("ai.rag.embedder._embed_ollama", return_value=[[0.1] * EMBEDDING_DIM])
    @patch("ai.rag.embedder._embed_cohere", return_value=None)
    @patch("ai.rag.embedder._embed_gemini", return_value=None)
    def test_tries_all_providers_in_order(self, mock_gemini, mock_cohere, mock_ollama):
        """Should try Gemini → Cohere → Ollama."""
        result = embed_texts(["test"])

        assert result == [[0.1] * EMBEDDING_DIM]
        mock_gemini.assert_called_once()
        mock_cohere.assert_called_once()
        mock_ollama.assert_called_once()

    @patch("ai.rag.embedder._embed_cohere", return_value=[[0.1] * EMBEDDING_DIM])
    @patch("ai.rag.embedder._embed_gemini", return_value=None)
    def test_skips_ollama_when_cohere_works(self, mock_gemini, mock_cohere):
        """Should not try Ollama if Cohere succeeds."""
        with patch("ai.rag.embedder._embed_ollama") as mock_ollama:
            result = embed_texts(["test"])

            assert result == [[0.1] * EMBEDDING_DIM]
            mock_ollama.assert_not_called()

    @patch("ai.rag.embedder._embed_cohere")
    @patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * EMBEDDING_DIM])
    def test_forced_provider_raises_on_failure(self, mock_gemini, mock_cohere):
        """provider='gemini' should raise if Gemini fails."""
        mock_gemini.return_value = None

        with pytest.raises(RuntimeError, match="Gemini embedding failed"):
            embed_texts(["test"], provider="gemini")

        # Should not try fallback providers
        mock_cohere.assert_not_called()


class TestRateLimiterIntegration:
    """Test rate limiter integration across providers."""

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_records_call_on_success(self, _load, _key, mock_litellm):
        """Should record call in rate limiter on successful embedding."""
        mock_litellm.RateLimitError = Exception
        mock_litellm.embedding.return_value = MagicMock(
            data=[{"embedding": [0.1] * EMBEDDING_DIM}]
        )
        limiter = MagicMock()
        limiter.can_call.return_value = True

        embed_texts(["test"], rate_limiter=limiter)

        # Should check and record
        limiter.can_call.assert_called()
        limiter.record_call.assert_called()

    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_skips_provider_when_rate_limited(self, _load, _get_key):
        """Should skip provider if rate limit is hit."""
        limiter = MagicMock()
        limiter.can_call.return_value = False

        with patch("ai.rag.embedder._embed_cohere") as mock_cohere:
            mock_cohere.return_value = [[0.1] * EMBEDDING_DIM]
            # Gemini will be skipped due to rate limit
            result = embed_texts(["test"], rate_limiter=limiter)

            # Should fall through to Cohere
            assert result is not None


class TestSelectProvider:
    """Test provider selection logic."""

    @patch("ai.rag.embedder.get_key")
    @patch("ai.rag.embedder.load_keys")
    @patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * EMBEDDING_DIM])
    def test_prefers_gemini(self, mock_gemini, _load, mock_get_key):
        """Should prefer Gemini when API key is set."""
        mock_get_key.side_effect = lambda k: "test-key" if k == "GEMINI_API_KEY" else None

        provider = select_provider()

        assert provider == "gemini"

    @patch("ai.rag.embedder.get_key")
    @patch("ai.rag.embedder.load_keys")
    @patch("ai.rag.embedder._embed_gemini", return_value=None)
    def test_falls_back_to_cohere(self, _mock_gemini, _load, mock_get_key):
        """Should use Cohere if Gemini fails."""
        mock_get_key.side_effect = lambda k: "test-key" if k == "COHERE_API_KEY" else None

        provider = select_provider()

        assert provider == "cohere"

    @patch("ai.rag.embedder.is_ollama_available", return_value=True)
    @patch("ai.rag.embedder._embed_ollama", return_value=[[0.1] * EMBEDDING_DIM])
    @patch("ai.rag.embedder.get_key", return_value=None)
    @patch("ai.rag.embedder.load_keys")
    def test_uses_ollama_when_no_api_keys(self, _load, _get_key, mock_ollama, _available):
        """Should use Ollama when no cloud API keys are set."""
        provider = select_provider()

        assert provider == "ollama"

    @patch("ai.rag.embedder.is_ollama_available", return_value=False)
    @patch("ai.rag.embedder.get_key", return_value=None)
    @patch("ai.rag.embedder.load_keys")
    def test_raises_when_no_provider_available(self, _load, _get_key, _available):
        """Should raise when no provider is available."""
        with pytest.raises(RuntimeError, match="No embedding provider available"):
            select_provider()


class TestInputTypeMapping:
    """Test task_type mapping for Gemini."""

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_search_document_maps_to_retrieval_document(self, _load, _get_key, mock_litellm):
        """search_document should map to RETRIEVAL_DOCUMENT."""
        mock_litellm.embedding.return_value = MagicMock(
            data=[{"embedding": [0.0] * EMBEDDING_DIM}]
        )

        _embed_gemini(["test"], input_type="search_document")

        call_kwargs = mock_litellm.embedding.call_args.kwargs
        assert call_kwargs["task_type"] == "RETRIEVAL_DOCUMENT"

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_search_query_maps_to_retrieval_query(self, _load, _get_key, mock_litellm):
        """search_query should map to RETRIEVAL_QUERY."""
        mock_litellm.embedding.return_value = MagicMock(
            data=[{"embedding": [0.0] * EMBEDDING_DIM}]
        )

        _embed_gemini(["test"], input_type="search_query")

        call_kwargs = mock_litellm.embedding.call_args.kwargs
        assert call_kwargs["task_type"] == "RETRIEVAL_QUERY"

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_unknown_type_defaults_to_retrieval_document(self, _load, _get_key, mock_litellm):
        """Unknown input_type should default to RETRIEVAL_DOCUMENT."""
        mock_litellm.embedding.return_value = MagicMock(
            data=[{"embedding": [0.0] * EMBEDDING_DIM}]
        )

        _embed_gemini(["test"], input_type="unknown_type")

        call_kwargs = mock_litellm.embedding.call_args.kwargs
        assert call_kwargs["task_type"] == "RETRIEVAL_DOCUMENT"
