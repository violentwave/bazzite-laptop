"""Unit tests for ai/rag/embedder.py."""

from unittest.mock import MagicMock, patch

import pytest

from ai.rag.embedder import (
    EMBEDDING_DIM,
    OLLAMA_MODEL,
    _embed_cohere,
    _embed_ollama,
    embed_single,
    embed_texts,
    is_ollama_available,
)

# ── Helpers ──

ZERO_VEC = [0.0] * EMBEDDING_DIM


def _make_ollama_list(*model_names: str) -> MagicMock:
    """Build a mock return value for ollama.list()."""
    models = []
    for name in model_names:
        m = MagicMock()
        m.model = name
        models.append(m)
    resp = MagicMock()
    resp.models = models
    return resp


@pytest.fixture()
def mock_limiter():
    """A MagicMock rate limiter that allows all calls."""
    limiter = MagicMock()
    limiter.can_call.return_value = True
    return limiter


# ── TestIsOllamaAvailable ──


class TestIsOllamaAvailable:
    @patch("ai.rag.embedder.ollama")
    def test_available_exact_name(self, mock_ollama):
        mock_ollama.list.return_value = _make_ollama_list(OLLAMA_MODEL)
        assert is_ollama_available() is True

    @patch("ai.rag.embedder.ollama")
    def test_available_with_tag(self, mock_ollama):
        mock_ollama.list.return_value = _make_ollama_list(f"{OLLAMA_MODEL}:latest")
        assert is_ollama_available() is True

    @patch("ai.rag.embedder.ollama")
    def test_unavailable_wrong_model(self, mock_ollama):
        mock_ollama.list.return_value = _make_ollama_list("llama3:latest")
        assert is_ollama_available() is False

    @patch("ai.rag.embedder.ollama")
    def test_unavailable_server_down(self, mock_ollama):
        mock_ollama.list.side_effect = ConnectionError("refused")
        assert is_ollama_available() is False


# ── TestEmbedOllama ──


class TestEmbedOllama:
    @patch("ai.rag.embedder.ollama")
    def test_successful_embedding(self, mock_ollama):
        mock_ollama.embed.return_value = {"embeddings": [ZERO_VEC]}
        result = _embed_ollama(["hello"])
        assert result == [ZERO_VEC]
        mock_ollama.embed.assert_called_once_with(model=OLLAMA_MODEL, input=["hello"])

    @patch("ai.rag.embedder.ollama")
    def test_multiple_texts(self, mock_ollama):
        mock_ollama.embed.return_value = {"embeddings": [ZERO_VEC, ZERO_VEC]}
        result = _embed_ollama(["a", "b"])
        assert len(result) == 2

    @patch("ai.rag.embedder.ollama")
    def test_model_not_found(self, mock_ollama):
        import ollama as real_ollama

        mock_ollama.ResponseError = real_ollama.ResponseError
        mock_ollama.embed.side_effect = real_ollama.ResponseError("model not found")
        result = _embed_ollama(["hello"])
        assert result is None

    @patch("ai.rag.embedder.ollama")
    def test_server_down(self, mock_ollama):
        mock_ollama.embed.side_effect = ConnectionError("refused")
        result = _embed_ollama(["hello"])
        assert result is None


# ── TestEmbedCohere ──


class TestEmbedCohere:
    @patch("ai.rag.embedder.cohere")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_successful_embedding(self, _load, _get_key, mock_cohere, mock_limiter):
        mock_response = MagicMock()
        mock_response.embeddings.float_ = [ZERO_VEC]
        mock_client = MagicMock()
        mock_client.embed.return_value = mock_response
        mock_cohere.ClientV2.return_value = mock_client

        result = _embed_cohere(["hello"], rate_limiter=mock_limiter)
        assert result == [ZERO_VEC]
        mock_limiter.record_call.assert_called_once_with("cohere")

    @patch("ai.rag.embedder.get_key", return_value=None)
    @patch("ai.rag.embedder.load_keys")
    def test_no_api_key(self, _load, _get_key):
        result = _embed_cohere(["hello"])
        assert result is None

    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_rate_limited(self, _load, _get_key):
        limiter = MagicMock()
        limiter.can_call.return_value = False
        result = _embed_cohere(["hello"], rate_limiter=limiter)
        assert result is None

    @patch("ai.rag.embedder.cohere")
    @patch("ai.rag.embedder.get_key", return_value="test-key")
    @patch("ai.rag.embedder.load_keys")
    def test_input_type_forwarded(self, _load, _get_key, mock_cohere, mock_limiter):
        mock_response = MagicMock()
        mock_response.embeddings.float_ = [ZERO_VEC]
        mock_client = MagicMock()
        mock_client.embed.return_value = mock_response
        mock_cohere.ClientV2.return_value = mock_client

        _embed_cohere(["q"], rate_limiter=mock_limiter, input_type="search_query")

        mock_client.embed.assert_called_once_with(
            texts=["q"],
            model="embed-english-v3.0",
            input_type="search_query",
            embedding_types=["float"],
        )


# ── TestEmbedTexts ──


class TestEmbedTexts:
    @patch("ai.rag.embedder._embed_ollama", return_value=[ZERO_VEC])
    def test_ollama_primary_path(self, mock_ollama):
        result = embed_texts(["hello"])
        assert result == [ZERO_VEC]
        mock_ollama.assert_called_once_with(["hello"])

    @patch("ai.rag.embedder._embed_cohere", return_value=[ZERO_VEC])
    @patch("ai.rag.embedder._embed_ollama", return_value=None)
    def test_cohere_fallback(self, _mock_ollama, mock_cohere):
        result = embed_texts(["hello"])
        assert result == [ZERO_VEC]
        mock_cohere.assert_called_once()

    @patch("ai.rag.embedder._embed_cohere", return_value=None)
    @patch("ai.rag.embedder._embed_ollama", return_value=None)
    def test_both_unavailable_raises(self, _mock_ollama, _mock_cohere):
        with pytest.raises(RuntimeError, match="All embedding providers unavailable"):
            embed_texts(["hello"])

    def test_empty_input_returns_empty(self):
        result = embed_texts([])
        assert result == []

    @patch("ai.rag.embedder._embed_ollama", return_value=[ZERO_VEC])
    def test_does_not_call_cohere_when_ollama_works(self, _mock_ollama):
        with patch("ai.rag.embedder._embed_cohere") as mock_cohere:
            embed_texts(["hello"])
            mock_cohere.assert_not_called()


# ── TestEmbedSingle ──


class TestEmbedSingle:
    @patch("ai.rag.embedder._embed_ollama", return_value=[ZERO_VEC])
    def test_returns_single_vector(self, _mock_ollama):
        result = embed_single("hello")
        assert result == ZERO_VEC
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIM
