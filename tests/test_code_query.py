"""Unit tests for ai/rag/code_query.py — code-aware RAG queries."""

from unittest.mock import MagicMock, patch

import pytest

from ai.rag.code_query import code_rag_query


class TestCodeRagQuery:
    """Tests for code_rag_query function."""

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_index_not_built_returns_message(self, mock_embed, mock_get_store):
        """Returns helpful message when code index not built."""
        mock_store = MagicMock()
        mock_store.count.return_value = 0
        mock_get_store.return_value = mock_store

        result = code_rag_query("How does route_query work?")

        assert result["question"] == "How does route_query work?"
        assert len(result["results"]) == 0
        assert "Code index not built" in result["answer"]
        assert result["model_used"] == "context-only"
        mock_embed.assert_not_called()

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_context_only_mode_returns_results(self, mock_embed, mock_get_store):
        """Context-only mode (use_llm=False) returns search results without LLM answer."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/router.py",
                "symbol_name": "route_query",
                "line_start": 100,
                "line_end": 120,
                "content": "def route_query(task_type, prompt):\\n    ...",
                "_distance": 0.15,
            }
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768

        result = code_rag_query("How does route_query work?", use_llm=False)

        assert result["question"] == "How does route_query work?"
        assert len(result["results"]) == 1
        assert result["results"][0]["relative_path"] == "ai/router.py"
        assert result["results"][0]["symbol_name"] == "route_query"
        assert result["answer"] == ""
        assert result["model_used"] == "context-only"

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    @patch("ai.router.route_query")
    def test_llm_synthesis_mode(self, mock_route, mock_embed, mock_get_store):
        """LLM synthesis mode (use_llm=True) generates an answer."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/router.py",
                "symbol_name": "route_query",
                "line_start": 100,
                "line_end": 120,
                "content": "def route_query(task_type, prompt):\\n    return result",
                "_distance": 0.15,
            }
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768
        mock_route.return_value = "route_query routes LLM calls based on task_type"

        result = code_rag_query("How does route_query work?", use_llm=True)

        assert result["question"] == "How does route_query work?"
        assert len(result["results"]) == 1
        assert "route_query routes" in result["answer"]
        assert result["model_used"] == "code"

        # Verify route_query was called with correct task_type
        assert mock_route.call_count == 1
        call_args = mock_route.call_args
        assert call_args[0][0] == "code"  # task_type
        assert "route_query" in call_args[0][1]  # prompt contains context

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    @patch("ai.router.route_query")
    def test_scaffold_response_fallback(self, mock_route, mock_embed, mock_get_store):
        """Scaffold responses fall back to context-only mode."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/test.py",
                "symbol_name": "test_func",
                "line_start": 1,
                "line_end": 10,
                "content": "def test_func(): pass",
                "_distance": 0.2,
            }
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768
        mock_route.return_value = "[SCAFFOLD] This is a placeholder response"

        result = code_rag_query("Test question", use_llm=True)

        assert result["answer"] == ""
        assert result["model_used"] == "context-only"

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    @patch("ai.router.route_query")
    def test_llm_routing_error_fallback(self, mock_route, mock_embed, mock_get_store):
        """Router errors fall back to context-only mode."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/test.py",
                "symbol_name": "test_func",
                "line_start": 1,
                "line_end": 10,
                "content": "def test_func(): pass",
                "_distance": 0.2,
            }
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768
        mock_route.side_effect = RuntimeError("All providers rate-limited")

        result = code_rag_query("Test question", use_llm=True)

        assert result["answer"] == ""
        assert result["model_used"] == "context-only"

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_limit_parameter_respected(self, mock_embed, mock_get_store):
        """Limit parameter controls number of results returned."""
        mock_store = MagicMock()
        mock_store.count.return_value = 100
        # Return more results than limit
        mock_store.search_code.return_value = [
            {
                "relative_path": f"ai/file{i}.py",
                "symbol_name": f"func{i}",
                "line_start": i * 10,
                "line_end": i * 10 + 10,
                "content": f"def func{i}(): pass",
                "_distance": 0.1 * i,
            }
            for i in range(10)
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768

        code_rag_query("Test", use_llm=False, limit=3)

        # search_code should be called with limit=3
        mock_store.search_code.assert_called_once()
        call_args = mock_store.search_code.call_args
        assert call_args.kwargs["limit"] == 3  # limit passed as keyword arg


class TestEdgeCases:
    """Edge cases and error handling."""

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_empty_search_results(self, mock_embed, mock_get_store):
        """Empty search results handled gracefully."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = []
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768

        result = code_rag_query("Nonexistent function", use_llm=False)

        assert result["question"] == "Nonexistent function"
        assert len(result["results"]) == 0
        assert result["answer"] == ""

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    def test_missing_fields_in_search_results(self, mock_embed, mock_get_store):
        """Missing fields in search results use defaults."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        # Return result with missing fields
        mock_store.search_code.return_value = [
            {
                "_distance": 0.15,
                # Missing: relative_path, symbol_name, line_start, line_end, content
            }
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768

        result = code_rag_query("Test", use_llm=False)

        # Should not crash, should use defaults
        assert len(result["results"]) == 1
        r = result["results"][0]
        assert r["relative_path"] == ""
        assert r["symbol_name"] == ""
        assert r["line_start"] == 0
        assert r["line_end"] == 0
        assert r["content"] == ""
        assert r["distance"] == 0.15

    @patch("ai.rag.store.get_store")
    def test_embed_single_error_propagates(self, mock_get_store):
        """Embedding errors propagate to caller."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_get_store.return_value = mock_store

        with patch("ai.rag.embedder.embed_single", side_effect=RuntimeError("Embedding failed")):
            with pytest.raises(RuntimeError, match="Embedding failed"):
                code_rag_query("Test question")


class TestSystemPrompt:
    """System prompt and context formatting tests."""

    @patch("ai.rag.store.get_store")
    @patch("ai.rag.embedder.embed_single")
    @patch("ai.router.route_query")
    def test_context_formatting(self, mock_route, mock_embed, mock_get_store):
        """Context is properly formatted in the LLM prompt."""
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/router.py",
                "symbol_name": "route_query",
                "line_start": 100,
                "line_end": 105,
                "content": "def route_query(task_type, prompt):\\n    pass",
                "_distance": 0.1,
            }
        ]
        mock_get_store.return_value = mock_store
        mock_embed.return_value = [0.1] * 768
        mock_route.return_value = "Test answer"

        code_rag_query("Test question", use_llm=True)

        # Check the prompt passed to route_query
        call_args = mock_route.call_args
        prompt = call_args[0][1]

        # Should contain system prompt
        assert "senior Python developer" in prompt
        assert "Bazzite gaming laptop AI codebase" in prompt

        # Should contain formatted context
        assert "[ai/router.py | route_query L100-105]" in prompt
        assert "def route_query" in prompt

        # Should contain question
        assert "Question: Test question" in prompt
