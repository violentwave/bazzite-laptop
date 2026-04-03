"""Edge case tests for ai/rag/embedder.py - Missing scenarios."""

from unittest.mock import MagicMock, patch

import pytest

from ai.rag.embedder import (
    embed_single,
    embed_texts,
    select_provider,
)


class TestEmbedderEdgeCases:
    """Edge cases missing from test_embedder.py."""

    # ── Rate Limiting Edge Cases ──

    @patch("ai.rag.embedder._embed_gemini")
    def test_gemini_rate_limit_triggers_fallback(self, mock_gemini):
        """When Gemini is rate limited, should fall back to Cohere."""
        mock_gemini.return_value = None  # Simulate internal rate limit rejection
        limiter = MagicMock()
        limiter.can_call.side_effect = lambda provider: provider != "gemini_embed"

        with patch("ai.rag.embedder._embed_cohere", return_value=[[0.1] * 768]):
            result = embed_texts(["test"], rate_limiter=limiter)
            assert len(result) == 1

    @patch("ai.rag.embedder._embed_gemini", return_value=None)
    @patch("ai.rag.embedder._embed_cohere")
    def test_cohere_rate_limit_triggers_ollama(self, mock_cohere, _):
        """When both Gemini and Cohere are rate limited, fall back to Ollama."""
        mock_cohere.return_value = None  # Simulate internal rate limit rejection
        limiter = MagicMock()
        limiter.can_call.return_value = False

        with patch("ai.rag.embedder._embed_ollama", return_value=[[0.1] * 768]):
            result = embed_texts(["test"], rate_limiter=limiter)
            assert len(result) == 1

    # ── Retry Logic Edge Cases ──

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_gemini_retry_exhaustion(self, _load, _key, mock_litellm):
        """When all retry attempts fail, should return None."""
        from ai.rag.embedder import _embed_gemini

        mock_litellm.RateLimitError = Exception
        mock_litellm.embedding.side_effect = mock_litellm.RateLimitError("429")

        result = _embed_gemini(["test"])
        assert result is None
        # Should retry 3 times
        assert mock_litellm.embedding.call_count == 3

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_gemini_non_rate_limit_error_no_retry(self, _load, _key, mock_litellm):
        """Non-rate-limit errors should not trigger retry."""
        from ai.rag.embedder import _embed_gemini

        class _FakeRateLimitError(Exception):
            pass

        mock_litellm.RateLimitError = _FakeRateLimitError
        mock_litellm.embedding.side_effect = ValueError("Invalid input")

        result = _embed_gemini(["test"])
        assert result is None
        # Should NOT retry on non-rate-limit errors
        assert mock_litellm.embedding.call_count == 1

    # ── Dimension Validation Edge Cases ──

    @patch("ai.rag.embedder._embed_gemini")
    def test_wrong_dimension_logs_warning(self, mock_gemini, caplog):
        """Should log warning if vector dimension doesn't match."""
        mock_gemini.return_value = [[0.1] * 512]  # Wrong dimension

        import logging
        with caplog.at_level(logging.WARNING):
            result = embed_texts(["test"])
        assert result == [[0.1] * 512]
        assert any("dimension" in r.message.lower() for r in caplog.records)

    @patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * 768])
    def test_mixed_dimensions_in_batch(self, mock_gemini):
        """All vectors in batch must have same dimension."""
        # This edge case: what if backend returns mixed dimensions?
        pass  # TODO: Implement if needed

    # ── Provider Selection Edge Cases ──

    @patch("ai.rag.embedder.get_key", return_value=None)
    @patch("ai.rag.embedder.is_ollama_available", return_value=False)
    @patch("ai.rag.embedder.load_keys")
    def test_select_provider_all_unavailable(self, _load, _ollama, _key):
        """Should raise RuntimeError when no provider available."""
        with pytest.raises(RuntimeError, match="No embedding provider available"):
            select_provider()

    @patch(
        "ai.rag.embedder.get_key", side_effect=lambda k: "key" if k == "COHERE_API_KEY" else None
    )
    @patch("ai.rag.embedder.load_keys")
    def test_select_provider_cohere_when_gemini_missing(self, _load, _key):
        """Should select Cohere when Gemini key missing."""
        result = select_provider()
        assert result == "cohere"

    # ── Cache Edge Cases ──

    def test_embed_single_cache_bypass_with_rate_limiter(self):
        """embed_single with rate_limiter should bypass cache."""
        limiter = MagicMock()
        with patch("ai.rag.embedder.embed_texts", return_value=[[0.1] * 768]) as mock_embed:
            embed_single("test", rate_limiter=limiter)
            # Should call embed_texts directly, not cached version
            mock_embed.assert_called_once()

    def test_embed_single_cache_hit(self):
        """Repeated calls with same text should use cache."""
        with patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * 768]) as mock_gemini:
            embed_single("cached text")
            embed_single("cached text")
            # Should only call embedding once
            assert mock_gemini.call_count == 1

    # ── Batch Processing Edge Cases ──

    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_gemini_partial_batch_failure(self, _load, _key, mock_litellm):
        """If one text in batch fails, entire batch should fail."""
        from ai.rag.embedder import _embed_gemini

        class _FakeRateLimitError(Exception):
            pass

        mock_litellm.RateLimitError = _FakeRateLimitError
        # First call succeeds, second fails
        mock_litellm.embedding.side_effect = [
            MagicMock(data=[{"embedding": [0.1] * 768}]),
            ValueError("Invalid text"),
        ]

        result = _embed_gemini(["text1", "text2"])
        assert result is None  # Should return None on any failure

    @patch("ai.rag.embedder.time.sleep")
    @patch("ai.rag.embedder.litellm")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_gemini_batch_delay(self, _load, _key, mock_litellm, mock_sleep):
        """Should add delay between batch calls."""
        from ai.rag.embedder import _embed_gemini

        mock_litellm.embedding.return_value = MagicMock(data=[{"embedding": [0.1] * 768}])

        _embed_gemini(["text1", "text2", "text3"])

        # Should sleep between calls (not before first)
        assert mock_sleep.call_count == 2

    # ── Input Validation Edge Cases ──

    def test_embed_texts_empty_list(self):
        """Empty input should return empty list without API calls."""
        with patch("ai.rag.embedder._embed_gemini") as mock_gemini:
            result = embed_texts([])
            assert result == []
            mock_gemini.assert_not_called()

    def test_embed_texts_whitespace_only(self):
        """Should handle whitespace-only text gracefully."""
        with patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * 768, [0.1] * 768]):
            result = embed_texts(["   ", "\t\n"])
            assert len(result) == 2

    def test_embed_texts_very_long_text(self):
        """Should handle text exceeding model context limit."""
        long_text = "x" * 100000  # 100k chars
        with patch("ai.rag.embedder._embed_gemini", return_value=[[0.1] * 768]):
            result = embed_texts([long_text])
            # Should truncate or chunk internally
            assert len(result) == 1

    # ── Ollama Availability Edge Cases ──

    @patch("ai.rag.embedder.ollama")
    def test_ollama_available_connection_timeout(self, mock_ollama):
        """Connection timeout should return False, not crash."""
        mock_ollama.list.side_effect = TimeoutError("timeout")

        from ai.rag.embedder import is_ollama_available

        assert is_ollama_available() is False

    @patch("ai.rag.embedder.ollama")
    def test_ollama_available_httpx_error(self, mock_ollama):
        """httpx errors should return False gracefully."""
        import httpx

        mock_ollama.list.side_effect = httpx.ConnectError("refused")

        from ai.rag.embedder import is_ollama_available

        assert is_ollama_available() is False
