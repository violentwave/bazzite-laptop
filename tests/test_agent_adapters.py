"""Tests for agent adapters."""

from unittest.mock import patch

import pytest

from ai.orchestration import (
    AgentMessage,
    OrchestrationBus,
    get_default_bus,
)
from ai.orchestration.protocol import TaskType


class TestSecurityAuditAgentAdapter:
    """Tests for SecurityAuditAgent adapter."""

    def test_instantiation(self):
        from ai.agents.security_audit_adapter import SecurityAuditAgent

        agent = SecurityAuditAgent()
        assert agent.name == "security"

    def test_supported_task_types(self):
        from ai.agents.security_audit_adapter import SecurityAuditAgent

        agent = SecurityAuditAgent()
        assert TaskType.SCAN_IOC in agent.supported_task_types
        assert TaskType.RUN_AUDIT in agent.supported_task_types
        assert TaskType.CHECK_CVE_FRESHNESS in agent.supported_task_types
        assert len(agent.supported_task_types) == 3

    @pytest.mark.asyncio
    async def test_handle_run_audit_success(self):
        from ai.agents.security_audit_adapter import SecurityAuditAgent

        agent = SecurityAuditAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="security",
            task_type=TaskType.RUN_AUDIT,
            payload={},
        )
        mock_result = {"status": "clean", "timestamp": "2024-01-01"}

        with patch(
            "ai.agents.security_audit.run_audit",
            return_value=mock_result,
        ):
            result = await agent.handle(msg)

        assert result.success is True
        assert result.source_agent == "security"
        assert result.data == mock_result

    @pytest.mark.asyncio
    async def test_handle_exception_returns_failure(self):
        from ai.agents.security_audit_adapter import SecurityAuditAgent

        agent = SecurityAuditAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="security",
            task_type=TaskType.RUN_AUDIT,
            payload={},
        )

        with patch(
            "ai.agents.security_audit.run_audit",
            side_effect=Exception("Audit failed"),
        ):
            result = await agent.handle(msg)

        assert result.success is False
        assert "Audit failed" in result.error


class TestCodeQualityAgentAdapter:
    """Tests for CodeQualityAgent adapter."""

    def test_instantiation(self):
        from ai.agents.code_quality_adapter import CodeQualityAgent

        agent = CodeQualityAgent()
        assert agent.name == "code_quality"

    def test_supported_task_types(self):
        from ai.agents.code_quality_adapter import CodeQualityAgent

        agent = CodeQualityAgent()
        assert TaskType.LINT_CHECK in agent.supported_task_types
        assert TaskType.AST_QUERY in agent.supported_task_types
        assert TaskType.SUGGEST_REFACTOR in agent.supported_task_types
        assert len(agent.supported_task_types) == 3

    @pytest.mark.asyncio
    async def test_handle_lint_check_success(self):
        from ai.agents.code_quality_adapter import CodeQualityAgent

        agent = CodeQualityAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="code_quality",
            task_type=TaskType.LINT_CHECK,
            payload={},
        )
        mock_result = {"status": "clean", "ruff": {"total_errors": 0}}

        with patch(
            "ai.agents.code_quality_agent.run_code_check",
            return_value=mock_result,
        ):
            result = await agent.handle(msg)

        assert result.success is True
        assert result.source_agent == "code_quality"

    @pytest.mark.asyncio
    async def test_handle_exception_returns_failure(self):
        from ai.agents.code_quality_adapter import CodeQualityAgent

        agent = CodeQualityAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="code_quality",
            task_type=TaskType.LINT_CHECK,
            payload={},
        )

        with patch(
            "ai.agents.code_quality_agent.run_code_check",
            side_effect=Exception("Code check failed"),
        ):
            result = await agent.handle(msg)

        assert result.success is False
        assert "Code check failed" in result.error


class TestPerformanceTuningAgentAdapter:
    """Tests for PerformanceTuningAgent adapter."""

    def test_instantiation(self):
        from ai.agents.performance_tuning_adapter import PerformanceTuningAgent

        agent = PerformanceTuningAgent()
        assert agent.name == "performance"

    def test_supported_task_types(self):
        from ai.agents.performance_tuning_adapter import PerformanceTuningAgent

        agent = PerformanceTuningAgent()
        assert TaskType.PROFILE_TOOL in agent.supported_task_types
        assert TaskType.DETECT_REGRESSION in agent.supported_task_types
        assert TaskType.TUNE_CACHE in agent.supported_task_types
        assert len(agent.supported_task_types) == 3

    @pytest.mark.asyncio
    async def test_handle_profile_tool_success(self):
        from ai.agents.performance_tuning_adapter import PerformanceTuningAgent

        agent = PerformanceTuningAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="performance",
            task_type=TaskType.PROFILE_TOOL,
            payload={},
        )
        mock_result = {"status": "optimal", "cpu_temp_max": 45.0}

        with patch(
            "ai.agents.performance_tuning.run_tuning",
            return_value=mock_result,
        ):
            result = await agent.handle(msg)

        assert result.success is True
        assert result.source_agent == "performance"

    @pytest.mark.asyncio
    async def test_handle_exception_returns_failure(self):
        from ai.agents.performance_tuning_adapter import PerformanceTuningAgent

        agent = PerformanceTuningAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="performance",
            task_type=TaskType.PROFILE_TOOL,
            payload={},
        )

        with patch(
            "ai.agents.performance_tuning.run_tuning",
            side_effect=Exception("Performance check failed"),
        ):
            result = await agent.handle(msg)

        assert result.success is False
        assert "Performance check failed" in result.error


class TestKnowledgeStorageAgentAdapter:
    """Tests for KnowledgeStorageAgent adapter."""

    def test_instantiation(self):
        from ai.agents.knowledge_storage_adapter import KnowledgeStorageAgent

        agent = KnowledgeStorageAgent()
        assert agent.name == "knowledge"

    def test_supported_task_types(self):
        from ai.agents.knowledge_storage_adapter import KnowledgeStorageAgent

        agent = KnowledgeStorageAgent()
        assert TaskType.STORE_INSIGHT in agent.supported_task_types
        assert TaskType.RETRIEVE_CONTEXT in agent.supported_task_types
        assert TaskType.SUMMARIZE_SESSION in agent.supported_task_types
        assert len(agent.supported_task_types) == 3

    @pytest.mark.asyncio
    async def test_handle_store_insight_success(self):
        from ai.agents.knowledge_storage_adapter import KnowledgeStorageAgent

        agent = KnowledgeStorageAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="knowledge",
            task_type=TaskType.STORE_INSIGHT,
            payload={},
        )
        mock_result = {"status": "healthy", "vector_db": {"total_rows": 1000}}

        with patch(
            "ai.agents.knowledge_storage.run_storage_check",
            return_value=mock_result,
        ):
            result = await agent.handle(msg)

        assert result.success is True
        assert result.source_agent == "knowledge"

    @pytest.mark.asyncio
    async def test_handle_exception_returns_failure(self):
        from ai.agents.knowledge_storage_adapter import KnowledgeStorageAgent

        agent = KnowledgeStorageAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="knowledge",
            task_type=TaskType.STORE_INSIGHT,
            payload={},
        )

        with patch(
            "ai.agents.knowledge_storage.run_storage_check",
            side_effect=Exception("Storage check failed"),
        ):
            result = await agent.handle(msg)

        assert result.success is False
        assert "Storage check failed" in result.error


class TestTimerSentinelAgentAdapter:
    """Tests for TimerSentinelAgent adapter."""

    def test_instantiation(self):
        from ai.agents.timer_sentinel_adapter import TimerSentinelAgent

        agent = TimerSentinelAgent()
        assert agent.name == "timer_sentinel"

    def test_supported_task_types(self):
        from ai.agents.timer_sentinel_adapter import TimerSentinelAgent

        agent = TimerSentinelAgent()
        assert TaskType.CHECK_TIMERS in agent.supported_task_types
        assert TaskType.ALERT_STALE in agent.supported_task_types
        assert TaskType.RESCHEDULE in agent.supported_task_types
        assert len(agent.supported_task_types) == 3

    @pytest.mark.asyncio
    async def test_handle_check_timers_success(self):
        from ai.agents.timer_sentinel_adapter import TimerSentinelAgent

        agent = TimerSentinelAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="timer_sentinel",
            task_type=TaskType.CHECK_TIMERS,
            payload={},
        )
        mock_result = {"status": "healthy", "stale": [], "missing": []}

        with patch(
            "ai.agents.timer_sentinel.check_timers",
            return_value=mock_result,
        ):
            result = await agent.handle(msg)

        assert result.success is True
        assert result.source_agent == "timer_sentinel"

    @pytest.mark.asyncio
    async def test_handle_exception_returns_failure(self):
        from ai.agents.timer_sentinel_adapter import TimerSentinelAgent

        agent = TimerSentinelAgent()
        msg = AgentMessage(
            source_agent="test",
            target_agent="timer_sentinel",
            task_type=TaskType.CHECK_TIMERS,
            payload={},
        )

        with patch(
            "ai.agents.timer_sentinel.check_timers",
            side_effect=Exception("Timer check failed"),
        ):
            result = await agent.handle(msg)

        assert result.success is False
        assert "Timer check failed" in result.error


class TestGetDefaultBus:
    """Tests for get_default_bus singleton."""

    @pytest.mark.asyncio
    async def test_default_bus_has_5_agents(self):
        from ai.orchestration import _register_default_agents

        bus = OrchestrationBus()
        await _register_default_agents(bus)
        agents = await bus.list_agents()

        assert len(agents) == 5
        assert "security" in agents
        assert "code_quality" in agents
        assert "performance" in agents
        assert "knowledge" in agents
        assert "timer_sentinel" in agents

    @pytest.mark.asyncio
    async def test_default_bus_singleton(self):
        bus1 = get_default_bus()
        bus2 = get_default_bus()

        assert bus1 is bus2
