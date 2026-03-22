"""Tests for code.search and code.rag_query MCP tools."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# ── Fixtures ──

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the bridge rate limiter between tests to prevent cross-test pollution."""
    import ai.mcp_bridge.tools as t
    t._global_call_times.clear()
    t._per_tool_call_times.clear()
    yield
    t._global_call_times.clear()
    t._per_tool_call_times.clear()


@pytest.fixture()
def allowlist():
    path = Path(__file__).parent.parent / "configs" / "mcp-bridge-allowlist.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


# ── Allowlist integrity ──

class TestCodeToolsInAllowlist:
    def test_code_search_present(self, allowlist):
        assert "code.search" in allowlist["tools"]

    def test_code_rag_query_present(self, allowlist):
        assert "code.rag_query" in allowlist["tools"]

    def test_code_search_uses_query_arg(self, allowlist):
        tool = allowlist["tools"]["code.search"]
        assert "query" in tool["args"]
        assert tool["args"]["query"]["max_length"] == 128

    def test_code_rag_query_uses_question_arg(self, allowlist):
        tool = allowlist["tools"]["code.rag_query"]
        assert "question" in tool["args"]
        assert tool["args"]["question"]["max_length"] == 500


# ── Arg validation ──

class TestCodeSearchArgValidation:
    @pytest.mark.asyncio
    async def test_rejects_missing_query(self):
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="required"):
            await execute_tool("code.search", {})

    @pytest.mark.asyncio
    async def test_rejects_query_too_long(self):
        from ai.mcp_bridge.tools import execute_tool

        long_q = "a" * 129
        with pytest.raises(ValueError, match="max length"):
            await execute_tool("code.search", {"query": long_q})


# ── code.search execution ──

class TestCodeSearch:
    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools._run_subprocess")
    async def test_returns_rg_output(self, mock_rg):
        mock_rg.return_value = "ai/router.py:45:def route_query(task, prompt):\n"

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("code.search", {"query": "route_query"})
        assert "route_query" in result

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools._run_subprocess")
    async def test_falls_back_to_grep_when_rg_not_found(self, mock_rg):
        # First call (rg) returns "[Command not found]", second (grep) returns results
        mock_rg.side_effect = [
            "[Command not found]",
            "ai/router.py:45:def route_query(task, prompt):\n",
        ]

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("code.search", {"query": "route_query"})
        assert "route_query" in result
        # Verify rg was tried first, then grep
        assert mock_rg.call_count == 2
        first_cmd = mock_rg.call_args_list[0][0][0]
        assert first_cmd[0] == "rg"
        second_cmd = mock_rg.call_args_list[1][0][0]
        assert second_cmd[0] == "grep"
        assert "-F" in second_cmd  # fixed-string mode prevents ReDoS

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools._run_subprocess")
    async def test_output_is_truncated(self, mock_rg):
        mock_rg.return_value = "x" * 5000

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("code.search", {"query": "x"})
        assert len(result) <= 4096 + len("...[truncated]")

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools._run_subprocess")
    async def test_home_path_redacted(self, mock_rg):
        mock_rg.return_value = "/home/lch/projects/bazzite-laptop/ai/router.py:1:x\n"

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("code.search", {"query": "x"})
        assert "/home/lch" not in result
        assert "[HOME]" in result


# ── code.rag_query execution ──

class TestCodeRagQuery:
    @pytest.mark.asyncio
    async def test_returns_index_not_built_when_empty(self):
        mock_store = MagicMock()
        mock_store.count.return_value = 0

        with patch("ai.rag.store.get_store", return_value=mock_store):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("code.rag_query", {"question": "How does routing work?"})

        data = json.loads(result)
        assert "not built yet" in data["answer"]
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_returns_results_when_index_exists(self):
        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/router.py",
                "symbol_name": "route_query",
                "line_start": 45,
                "line_end": 80,
                "content": "def route_query(task_type, prompt): ...",
                "_distance": 0.12,
            }
        ]

        with (
            patch("ai.rag.store.get_store", return_value=mock_store),
            patch("ai.rag.embedder.embed_single", return_value=[0.0] * 768),
        ):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("code.rag_query", {"question": "How does routing work?"})

        data = json.loads(result)
        assert len(data["results"]) == 1
        assert data["results"][0]["symbol_name"] == "route_query"
        assert data["results"][0]["relative_path"] == "ai/router.py"
        assert data["model_used"] == "context-only"

    @pytest.mark.asyncio
    async def test_home_path_redacted_in_output(self):
        mock_store = MagicMock()
        mock_store.count.return_value = 1
        mock_store.search_code.return_value = [
            {
                "relative_path": "/home/lch/projects/bazzite-laptop/ai/router.py",
                "symbol_name": "route_query",
                "line_start": 1,
                "line_end": 10,
                "content": "x",
                "_distance": 0.1,
            }
        ]

        with (
            patch("ai.rag.store.get_store", return_value=mock_store),
            patch("ai.rag.embedder.embed_single", return_value=[0.0] * 768),
        ):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("code.rag_query", {"question": "test"})

        assert "/home/lch" not in result


# ── code_query module unit tests ──

class TestCodeRagQueryModule:
    def test_index_not_built_message(self):
        mock_store = MagicMock()
        mock_store.count.return_value = 0

        with patch("ai.rag.store.get_store", return_value=mock_store):
            from ai.rag.code_query import code_rag_query

            result = code_rag_query("what is route_query?")

        assert "not built" in result["answer"]
        assert result["results"] == []

    def test_results_structure(self):
        mock_store = MagicMock()
        mock_store.count.return_value = 5
        mock_store.search_code.return_value = [
            {
                "relative_path": "ai/router.py",
                "symbol_name": "route_query",
                "line_start": 10,
                "line_end": 30,
                "content": "def route_query(): pass",
                "_distance": 0.05,
            }
        ]

        with (
            patch("ai.rag.store.get_store", return_value=mock_store),
            patch("ai.rag.embedder.embed_single", return_value=[0.0] * 768),
        ):
            from ai.rag.code_query import code_rag_query

            result = code_rag_query("route_query function")

        assert result["question"] == "route_query function"
        assert len(result["results"]) == 1
        chunk = result["results"][0]
        assert chunk["relative_path"] == "ai/router.py"
        assert chunk["symbol_name"] == "route_query"
        assert chunk["line_start"] == 10
        assert chunk["line_end"] == 30
        assert chunk["distance"] == 0.05
        assert result["model_used"] == "context-only"
        assert result["answer"] == ""

    def test_all_result_keys_present(self):
        mock_store = MagicMock()
        mock_store.count.return_value = 1
        mock_store.search_code.return_value = [
            {"relative_path": "a.py", "symbol_name": "f", "line_start": 1,
             "line_end": 5, "content": "x", "_distance": 0.1}
        ]

        with (
            patch("ai.rag.store.get_store", return_value=mock_store),
            patch("ai.rag.embedder.embed_single", return_value=[0.0] * 768),
        ):
            from ai.rag.code_query import code_rag_query

            result = code_rag_query("test")

        assert set(result.keys()) == {"question", "results", "answer", "model_used"}
        required_chunk_keys = {
            "relative_path", "symbol_name", "line_start", "line_end",
            "content", "distance",
        }
        assert required_chunk_keys <= set(result["results"][0].keys())
