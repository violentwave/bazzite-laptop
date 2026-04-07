"""Integration tests for P44-P49 features.

These tests verify end-to-end behavior of:
- P44: Input validation in MCP dispatch
- P45: Semantic cache in router
- P46: Token budget enforcement
- P47: Pattern search
- P48: Timer sentinel
- P49: Conversation memory
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestP44InputValidationE2E:
    """P44: Input validation blocks injection through MCP dispatch."""

    def test_sql_injection_blocked_at_dispatch(self):
        """Prove SQL injection is blocked at MCP dispatch level."""
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="validation failed"):
            asyncio.run(execute_tool("logs.search", {"query": "'; DROP TABLE --"}))

    def test_path_traversal_blocked_at_dispatch(self):
        """Prove path traversal is blocked at MCP dispatch level."""
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="validation failed"):
            asyncio.run(execute_tool("knowledge.rag_query", {"query": "../../etc/passwd"}))

    def test_command_injection_blocked_at_dispatch(self):
        """Prove command injection is blocked at dispatch level."""
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="validation failed"):
            asyncio.run(execute_tool("logs.search", {"query": "test; rm -rf /"}))


class TestP45SemanticCacheE2E:
    """P45: Semantic cache saves tokens on repeated queries."""

    def test_semantic_cache_imports(self):
        """Verify semantic cache module imports."""
        from ai.cache_semantic import SemanticCache

        assert SemanticCache is not None

    def test_semantic_cache_instantiation(self):
        """Verify cache can be instantiated."""
        from ai.cache_semantic import SemanticCache

        cache = SemanticCache()
        assert cache is not None

    def test_semantic_cache_stats_structure(self):
        """Verify cache stats returns expected structure."""
        from ai.cache_semantic import SemanticCache

        cache = SemanticCache()
        stats = cache.stats()
        assert isinstance(stats, dict)


class MockTable:
    """Mock LanceDB table for testing without Ollama."""

    def to_pydict(self):
        return {"id": [], "query": [], "response": []}

    def count_rows(self):
        return 0


class TestP46BudgetEnforcementE2E:
    """P46: Budget enforcement blocks excess usage."""

    def test_budget_module_imports(self):
        """Verify budget module imports."""
        from ai.budget import TokenBudget

        assert TokenBudget is not None

    def test_budget_status_structure(self):
        """Verify budget status returns all tiers."""
        from ai.budget import TokenBudget

        budget = TokenBudget()
        status = budget.get_status()

        for tier in ["security", "scheduled", "interactive", "coding"]:
            assert tier in status, f"Missing tier: {tier}"

    def test_budget_security_always_allowed(self):
        """Security tier should never be blocked."""
        from ai.budget import TokenBudget

        budget = TokenBudget()
        assert budget.can_spend("security", 1_000_000) is True

    def test_budget_classify_task(self):
        """Verify task classification maps correctly."""
        from ai.budget import classify_task

        assert classify_task("fast", "") == "interactive"
        assert classify_task("code", "") == "coding"
        assert classify_task("embed", "timer") == "scheduled"


class TestP47PatternSearchE2E:
    """P47: Pattern search returns relevant results."""

    def test_pattern_search_tool_exists(self):
        """Verify pattern search tool is registered."""
        from ai.rag.pattern_query import search_patterns

        assert search_patterns is not None

    def test_pattern_search_with_language_filter(self):
        """Verify pattern search accepts language filter."""
        from ai.rag.pattern_query import search_patterns

        results = search_patterns("atomic write", language="python")
        assert isinstance(results, list)


class TestP48TimerSentinelE2E:
    """P48: Timer sentinel health check."""

    def test_timer_sentinel_imports(self):
        """Verify timer sentinel module imports."""
        from ai.agents.timer_sentinel import check_timers

        assert check_timers is not None

    def test_timer_sentinel_returns_health(self):
        """Verify timer sentinel returns health status."""
        from ai.agents.timer_sentinel import check_timers

        result = check_timers()
        assert "status" in result
        assert result["status"] in ["healthy", "warning", "critical", "unknown"]


class TestP49ConversationMemoryE2E:
    """P49: Conversation memory stores and recalls."""

    def test_conversation_memory_module_exists(self):
        """Verify conversation memory module exists."""
        from ai.rag.memory import retrieve_relevant_context, store_interaction

        assert store_interaction is not None
        assert retrieve_relevant_context is not None

    def test_memory_retrieve_returns_list(self):
        """Verify retrieve returns list format."""
        from ai.rag.memory import retrieve_relevant_context

        results = retrieve_relevant_context("test query")
        assert isinstance(results, list)


class TestP44P49IntegrationSmoke:
    """Smoke test that all P44-P49 modules can be imported together."""

    def test_all_modules_import(self):
        """Verify all P44-P49 modules can be imported."""
        from ai.agents.timer_sentinel import check_timers
        from ai.budget import TokenBudget
        from ai.cache_semantic import SemanticCache
        from ai.rag.memory import store_interaction
        from ai.rag.pattern_query import search_patterns
        from ai.rag.pattern_store import get_or_create_table
        from ai.security.inputvalidator import InputValidator

        assert InputValidator is not None
        assert SemanticCache is not None
        assert TokenBudget is not None
        assert get_or_create_table is not None
        assert search_patterns is not None
        assert check_timers is not None
        assert store_interaction is not None
