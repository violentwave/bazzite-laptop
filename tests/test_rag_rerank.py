"""Unit tests for Cohere rerank integration in ai/rag/query.py."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Pre-mock heavy deps before any ai.rag imports
sys.modules.setdefault("lancedb", MagicMock())
sys.modules.setdefault("pyarrow", MagicMock())

_CHUNKS = [
    {"text": "GPU temp 92C warning", "_distance": 0.3, "source_file": "health.log",
     "section": "gpu"},
    {"text": "ClamAV found trojan", "_distance": 0.2, "source_file": "scan.log",
     "section": "threats"},
    {"text": "Disk usage 85%", "_distance": 0.4, "source_file": "health.log",
     "section": "disk"},
]


@pytest.fixture()
def mock_rate_limiter():
    rl = MagicMock()
    rl.can_call.return_value = True
    return rl


@pytest.fixture()
def mock_cohere():
    """Fake cohere.ClientV2 that reranks in reverse order."""
    result_items = [
        MagicMock(index=2, relevance_score=0.9),
        MagicMock(index=0, relevance_score=0.7),
        MagicMock(index=1, relevance_score=0.5),
    ]
    fake_response = MagicMock()
    fake_response.results = result_items

    fake_client = MagicMock()
    fake_client.rerank.return_value = fake_response

    fake_module = MagicMock()
    fake_module.ClientV2.return_value = fake_client
    return fake_module, fake_client


class TestCohereRerank:
    def test_rerank_called_when_use_llm_true(self, mock_rate_limiter, mock_cohere):
        fake_module, fake_client = mock_cohere
        chunks = list(_CHUNKS)

        with (
            patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}),
            patch.dict(sys.modules, {"cohere": fake_module}),
        ):
            from ai.rag.query import _cohere_rerank

            result = _cohere_rerank("security threats", chunks, mock_rate_limiter)

        fake_client.rerank.assert_called_once()
        mock_rate_limiter.record_call.assert_called_once_with("cohere_rerank")
        # Reranked order: index 2, 0, 1
        assert result[0] is chunks[2]
        assert result[1] is chunks[0]
        assert result[2] is chunks[1]

    def test_rerank_not_called_when_no_api_key(self, mock_rate_limiter, mock_cohere):
        fake_module, fake_client = mock_cohere
        chunks = list(_CHUNKS)

        env = {k: v for k, v in os.environ.items() if k != "COHERE_API_KEY"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch.dict(sys.modules, {"cohere": fake_module}),
        ):
            from ai.rag.query import _cohere_rerank

            result = _cohere_rerank("security threats", chunks, mock_rate_limiter)

        fake_client.rerank.assert_not_called()
        assert result is chunks  # original list returned unchanged

    def test_rerank_skipped_on_rate_limit(self, mock_cohere):
        fake_module, fake_client = mock_cohere
        chunks = list(_CHUNKS)

        rl = MagicMock()
        rl.can_call.return_value = False

        with (
            patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}),
            patch.dict(sys.modules, {"cohere": fake_module}),
        ):
            from ai.rag.query import _cohere_rerank

            result = _cohere_rerank("query", chunks, rl)

        fake_client.rerank.assert_not_called()
        assert result is chunks

    def test_fallback_on_rerank_error(self, mock_rate_limiter):
        chunks = list(_CHUNKS)

        fake_module = MagicMock()
        fake_module.ClientV2.side_effect = RuntimeError("Cohere API down")

        with (
            patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}),
            patch.dict(sys.modules, {"cohere": fake_module}),
        ):
            from ai.rag.query import _cohere_rerank

            result = _cohere_rerank("query", chunks, mock_rate_limiter)

        # Original order returned, no record_call
        assert result is chunks
        mock_rate_limiter.record_call.assert_not_called()

    def test_fallback_on_rerank_api_error(self, mock_rate_limiter):
        chunks = list(_CHUNKS)

        fake_client = MagicMock()
        fake_client.rerank.side_effect = Exception("HTTP 429")

        fake_module = MagicMock()
        fake_module.ClientV2.return_value = fake_client

        with (
            patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}),
            patch.dict(sys.modules, {"cohere": fake_module}),
        ):
            from ai.rag.query import _cohere_rerank

            result = _cohere_rerank("query", chunks, mock_rate_limiter)

        assert result is chunks
        mock_rate_limiter.record_call.assert_not_called()


class TestRagQueryRerankIntegration:
    """Verify rag_query wires rerank only when use_llm=True."""

    def _make_store(self):
        store = MagicMock()
        store.search_logs.return_value = list(_CHUNKS)
        store.search_threats.return_value = []
        store.search_docs.return_value = []
        return store

    def test_rerank_invoked_when_use_llm_true(self, mock_rate_limiter, mock_cohere):
        fake_module, fake_client = mock_cohere
        store = self._make_store()

        with (
            patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}),
            patch.dict(sys.modules, {"cohere": fake_module}),
            patch("ai.rag.query.RateLimiter", return_value=mock_rate_limiter),
            patch("ai.rag.embedder.embed_single", return_value=[0.1] * 768),
            patch("ai.rag.store.get_store", return_value=store),
            patch("ai.rag.query.route_query", return_value="LLM answer"),
        ):
            from ai.rag.query import rag_query

            result = rag_query("What threats?", use_llm=True, rate_limiter=mock_rate_limiter)

        fake_client.rerank.assert_called_once()
        assert result.answer == "LLM answer"

    def test_rerank_not_invoked_when_use_llm_false(self, mock_rate_limiter, mock_cohere):
        fake_module, fake_client = mock_cohere
        store = self._make_store()

        with (
            patch.dict(os.environ, {"COHERE_API_KEY": "test-key"}),
            patch.dict(sys.modules, {"cohere": fake_module}),
            patch("ai.rag.query.RateLimiter", return_value=mock_rate_limiter),
            patch("ai.rag.embedder.embed_single", return_value=[0.1] * 768),
            patch("ai.rag.store.get_store", return_value=store),
        ):
            from ai.rag.query import rag_query

            result = rag_query("What threats?", use_llm=False, rate_limiter=mock_rate_limiter)

        fake_client.rerank.assert_not_called()
        assert result.model_used == "context-only"
