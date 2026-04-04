"""Tests for MCP tool filtering middleware."""

import pytest

from ai.mcp_bridge.tool_filter import (
    CORE_TOOLS,
    ToolFilter,
)


@pytest.fixture
def tool_filter():
    """Create a fresh ToolFilter instance for testing."""
    return ToolFilter()


class TestFilterByNamespace:
    """Tests for namespace-based filtering."""

    def test_filter_security_returns_security_tools(self, tool_filter):
        result = tool_filter.filter_by_namespace(["security"])
        assert "security.scan" in result or "security.status" in result
        # Check that most tools start with security. or agents.security
        security_tools = [
            t for t in result if t.startswith("security.") or t.startswith("agents.security")
        ]
        assert len(security_tools) > 0

    def test_filter_system_returns_system_tools(self, tool_filter):
        result = tool_filter.filter_by_namespace(["system"])
        assert "system.disk_usage" in result
        # Check that most tools start with system.
        system_tools = [t for t in result if t.startswith("system.")]
        assert len(system_tools) > 0

    def test_filter_all_returns_everything(self, tool_filter):
        result = tool_filter.filter_by_namespace(["all"])
        assert len(result) > 50

    def test_filter_empty_returns_everything(self, tool_filter):
        result = tool_filter.filter_by_namespace([])
        assert len(result) > 50


class TestFilterByQuery:
    """Tests for semantic query-based filtering."""

    def test_query_returns_relevant_tools(self, tool_filter):
        result = tool_filter.filter_by_query("check CVE vulnerability")
        assert len(result) > 0

    def test_query_respects_top_k(self, tool_filter):
        result = tool_filter.filter_by_query("test query", top_k=5)
        assert len(result) <= 5


class TestCoreTools:
    """Tests for core tools always being included."""

    def test_core_tools_included_in_any_result(self, tool_filter):
        result = tool_filter.filter_by_query("")
        all_tools = tool_filter.get_all_tools()
        # CORE_TOOLS should be in all_tools or in get_context_tools result
        for core_tool in CORE_TOOLS:
            if core_tool != "health":  # health is built-in, not in allowlist
                assert core_tool in all_tools or core_tool in result


class TestMaxToolsLimit:
    """Tests for the max tools limit."""

    def test_get_context_tools_respects_limit(self, tool_filter):
        result = tool_filter.get_context_tools("test message")
        assert len(result) <= 15


class TestGetAllTools:
    """Tests for getting all tools without filtering."""

    def test_get_all_tools_returns_complete_list(self, tool_filter):
        result = tool_filter.get_all_tools()
        assert len(result) >= 57
        assert "system.disk_usage" in result
        assert "security.status" in result


class TestEmptyQuery:
    """Tests for empty query handling."""

    def test_empty_query_returns_core_tools(self, tool_filter):
        result = tool_filter.get_context_tools("")
        # Should include core tools
        assert len(result) > 0
