"""Tests for orchestrated workflows with agent-dispatched steps."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.orchestration import AgentResult
from ai.workflows.definitions import (
    CODE_HEALTH_CHECK,
    MORNING_BRIEFING_ENRICHED,
    SECURITY_DEEP_SCAN,
    WORKFLOW_REGISTRY,
)
from ai.workflows.runner import WorkflowRunner


class TestAgentDispatchedSteps:
    """Tests for agent-dispatched workflow steps."""

    @pytest.fixture
    def runner(self):
        return WorkflowRunner()

    @pytest.mark.asyncio
    async def test_run_plan_with_agent_step_dispatches_via_bus(self, runner):
        """Test run_plan with agent step dispatches via OrchestrationBus."""
        mock_result = AgentResult(
            correlation_id="corr-1",
            source_agent="security",
            success=True,
            data={"status": "clean"},
            duration_seconds=0.1,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(return_value=mock_result)
            mock_get_bus.return_value = mock_bus

            plan = [{"id": "step1", "agent": "security", "task_type": "run_audit", "args": {}}]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "complete"
            assert result["steps"]["step1"]["result"] == {"status": "clean"}
            mock_bus.dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_plan_with_payload_from_passes_upstream_result(self, runner):
        """Test run_plan with payload_from correctly passes upstream result."""
        upstream_result = {"audit_data": "test", "status": "clean"}

        step1_result = AgentResult(
            correlation_id="corr-1",
            source_agent="security",
            success=True,
            data=upstream_result,
            duration_seconds=0.1,
        )

        step2_result = AgentResult(
            correlation_id="corr-2",
            source_agent="knowledge",
            success=True,
            data={"stored": True},
            duration_seconds=0.1,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(side_effect=[step1_result, step2_result])
            mock_get_bus.return_value = mock_bus

            plan = [
                {"id": "step1", "agent": "security", "task_type": "run_audit", "args": {}},
                {
                    "id": "step2",
                    "agent": "knowledge",
                    "task_type": "store_insight",
                    "payload_from": "step1",
                    "args": {"category": "security"},
                    "depends_on": ["step1"],
                },
            ]
            await runner.run_plan(plan)

            calls = mock_bus.dispatch.call_args_list
            second_call = calls[1]
            second_msg = second_call[0][0]
            assert second_msg.payload.get("upstream_result") == upstream_result

    @pytest.mark.asyncio
    async def test_run_plan_with_failed_agent_step_sets_failed_status(self, runner):
        """Test run_plan with failed agent step sets status='failed'."""
        failed_result = AgentResult(
            correlation_id="corr-1",
            source_agent="security",
            success=False,
            data={},
            error="Security scan failed",
            duration_seconds=0.1,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(return_value=failed_result)
            mock_get_bus.return_value = mock_bus

            plan = [
                {
                    "id": "step1",
                    "agent": "security",
                    "task_type": "run_audit",
                    "args": {},
                    "abort_on_error": True,
                }
            ]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "failed"
            assert "Security scan failed" in result["steps"]["step1"]["error"]

    @pytest.mark.asyncio
    async def test_run_plan_skips_dependents_after_failure(self, runner):
        """Test run_plan skips dependents after failed agent step."""
        success_result = AgentResult(
            correlation_id="corr-1",
            source_agent="security",
            success=True,
            data={"status": "clean"},
            duration_seconds=0.1,
        )

        failed_result = AgentResult(
            correlation_id="corr-2",
            source_agent="timer_sentinel",
            success=False,
            data={},
            error="Timer check failed",
            duration_seconds=0.1,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(side_effect=[success_result, failed_result])
            mock_get_bus.return_value = mock_bus

            plan = [
                {"id": "step1", "agent": "security", "task_type": "run_audit", "args": {}},
                {
                    "id": "step2",
                    "agent": "timer_sentinel",
                    "task_type": "check_timers",
                    "args": {},
                    "depends_on": ["step1"],
                    "abort_on_error": True,
                },
            ]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "complete"
            assert result["steps"]["step2"]["status"] == "failed"
            assert result["status"] == "partial"


class TestWorkflowDefinitions:
    """Tests for workflow definitions."""

    def test_security_deep_scan_workflow(self):
        """Test security_deep_scan workflow structure."""
        assert SECURITY_DEEP_SCAN["name"] == "security_deep_scan"
        assert len(SECURITY_DEEP_SCAN["steps"]) == 6

        deps_map = {step["id"]: step.get("depends_on", []) for step in SECURITY_DEEP_SCAN["steps"]}
        assert deps_map["av_scan"] == []
        assert deps_map["log_ingest"] == []
        assert deps_map["cve_check"] == ["log_ingest"]
        assert deps_map["threat_summary"] == ["log_ingest"]
        assert deps_map["alert_summary"] == ["log_ingest"]
        assert set(deps_map["full_audit"]) == {"cve_check", "threat_summary", "alert_summary"}

    def test_code_health_check_workflow(self):
        """Test code_health_check workflow structure."""
        assert CODE_HEALTH_CHECK["name"] == "code_health_check"
        assert len(CODE_HEALTH_CHECK["steps"]) == 3

        steps = {s["id"]: s for s in CODE_HEALTH_CHECK["steps"]}
        assert steps["lint"]["agent"] == "code_quality"
        assert steps["lint"]["task_type"] == "lint_check"

        assert steps["profile"]["agent"] == "performance"
        assert steps["profile"]["task_type"] == "profile_tool"
        assert steps["profile"]["payload_from"] == "lint"

        assert steps["store"]["agent"] == "knowledge"
        assert steps["store"]["task_type"] == "store_insight"

    def test_morning_briefing_enriched_workflow(self):
        """Test morning_briefing_enriched workflow structure."""
        assert MORNING_BRIEFING_ENRICHED["name"] == "morning_briefing_enriched"
        assert len(MORNING_BRIEFING_ENRICHED["steps"]) == 6

        step_ids = [s["id"] for s in MORNING_BRIEFING_ENRICHED["steps"]]
        assert "memory_context" in step_ids
        assert "security" in step_ids
        assert "code" in step_ids
        assert "perf" in step_ids
        assert "timers" in step_ids
        assert "collect" in step_ids

        collect_step = next(s for s in MORNING_BRIEFING_ENRICHED["steps"] if s["id"] == "collect")
        assert collect_step["depends_on"] == [
            "memory_context",
            "security",
            "code",
            "perf",
            "timers",
        ]

    def test_workflow_registry_contains_all_three(self):
        """Test WORKFLOW_REGISTRY contains all 3 workflows."""
        assert "security_deep_scan" in WORKFLOW_REGISTRY
        assert "code_health_check" in WORKFLOW_REGISTRY
        assert "morning_briefing_enriched" in WORKFLOW_REGISTRY
        assert len(WORKFLOW_REGISTRY) == 3


class TestWorkflowExecution:
    """Integration tests for workflow execution."""

    @pytest.fixture
    def runner(self):
        return WorkflowRunner()

    @pytest.mark.asyncio
    async def test_security_deep_scan_completes_all_steps(self, runner):
        """Test security_deep_scan 6-step chain completes."""
        tool_results = [
            '{"scan":"ok"}',
            '{"ingest":"ok"}',
            '{"cve":"ok"}',
            '{"threat":"ok"}',
            '{"alert":"ok"}',
        ]
        full_audit_result = AgentResult(
            correlation_id="corr-1",
            source_agent="security",
            success=True,
            data={"status": "clean", "scan_triggered": False},
            duration_seconds=0.2,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(return_value=full_audit_result)
            mock_get_bus.return_value = mock_bus
            runner._execute_tool = AsyncMock(side_effect=tool_results)

            result = await runner.run_plan(SECURITY_DEEP_SCAN["steps"])

            assert result["steps"]["av_scan"]["status"] == "complete"
            assert result["steps"]["log_ingest"]["status"] == "complete"
            assert result["steps"]["cve_check"]["status"] == "complete"
            assert result["steps"]["threat_summary"]["status"] == "complete"
            assert result["steps"]["alert_summary"]["status"] == "complete"
            assert result["steps"]["full_audit"]["status"] == "complete"
            assert runner._execute_tool.await_count == 5
            mock_bus.dispatch.assert_called_once()
            assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_code_health_check_lint_result_flows_to_profile(self, runner):
        """Test code_health_check lint result flows into profile step payload."""
        lint_result = AgentResult(
            correlation_id="corr-1",
            source_agent="code_quality",
            success=True,
            data={"total_errors": 5, "by_rule": {"E501": 3}},
            duration_seconds=0.1,
        )

        profile_result = AgentResult(
            correlation_id="corr-2",
            source_agent="performance",
            success=True,
            data={"cpu_temp_max": 45.0},
            duration_seconds=0.2,
        )

        store_result = AgentResult(
            correlation_id="corr-3",
            source_agent="knowledge",
            success=True,
            data={"stored": True},
            duration_seconds=0.1,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(side_effect=[lint_result, profile_result, store_result])
            mock_get_bus.return_value = mock_bus

            result = await runner.run_plan(CODE_HEALTH_CHECK["steps"])

            assert result["steps"]["lint"]["status"] == "complete"
            assert result["steps"]["profile"]["status"] == "complete"

            calls = mock_bus.dispatch.call_args_list
            profile_call = calls[1]
            profile_msg = profile_call[0][0]
            assert "upstream_result" in profile_msg.payload
            assert profile_msg.payload["upstream_result"]["total_errors"] == 5

    @pytest.mark.asyncio
    async def test_morning_briefing_fan_out_completes_before_collect(self, runner):
        """Test morning_briefing all 4 fan-out steps complete before collect."""
        fan_out_results = [
            AgentResult(
                correlation_id=f"corr-{i}",
                source_agent=agent,
                success=True,
                data={"status": "ok"},
                duration_seconds=0.1,
            )
            for i, agent in enumerate(["security", "code_quality", "performance", "timer_sentinel"])
        ]

        collect_result = AgentResult(
            correlation_id="corr-5",
            source_agent="knowledge",
            success=True,
            data={"summary": "All agents completed"},
            duration_seconds=0.1,
        )

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(side_effect=fan_out_results + [collect_result])
            mock_get_bus.return_value = mock_bus

            result = await runner.run_plan(MORNING_BRIEFING_ENRICHED["steps"])

            assert result["steps"]["memory_context"]["status"] == "complete"
            assert result["steps"]["security"]["status"] == "complete"
            assert result["steps"]["code"]["status"] == "complete"
            assert result["steps"]["perf"]["status"] == "complete"
            assert result["steps"]["timers"]["status"] == "complete"
            assert result["steps"]["collect"]["status"] == "complete"
            assert result["status"] == "complete"


class TestExistingToolDispatch:
    """Test that existing tool-dispatch path still works (no regression)."""

    @pytest.fixture
    def runner(self):
        return WorkflowRunner()

    @pytest.mark.asyncio
    async def test_run_plan_tool_dispatch_still_works(self, runner):
        """Test run_plan with tool (non-agent) still executes correctly."""
        mock_tool_result = '{"result": "tool output"}'

        with patch.object(runner, "_execute_tool", new=AsyncMock(return_value=mock_tool_result)):
            plan = [{"id": "step1", "tool": "test_tool", "args": {"arg1": "value1"}}]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "complete"
            assert result["steps"]["step1"]["result"] == mock_tool_result

    @pytest.mark.asyncio
    async def test_run_plan_llm_dispatch_still_works(self, runner):
        """Test run_plan with llm tool still executes correctly."""
        mock_llm_result = "LLM response"

        with patch.object(runner, "_call_llm_direct", new=AsyncMock(return_value=mock_llm_result)):
            plan = [{"id": "step1", "tool": "llm", "args": {"prompt": "test prompt"}}]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "complete"
            assert result["steps"]["step1"]["result"] == mock_llm_result

    @pytest.mark.asyncio
    async def test_run_plan_dependencies_work_for_tool_steps(self, runner):
        """Test dependencies work correctly for tool-based steps."""
        with patch.object(runner, "_execute_tool", new=AsyncMock(return_value='"ok"')):
            plan = [
                {"id": "step1", "tool": "tool1", "args": {}},
                {"id": "step2", "tool": "tool2", "args": {}, "depends_on": ["step1"]},
            ]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "complete"
            assert result["steps"]["step2"]["status"] == "complete"
            assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_run_plan_abort_on_error_for_tool_steps(self, runner):
        """Test abort_on_error works for tool-based steps."""
        with patch.object(
            runner, "_execute_tool", new=AsyncMock(side_effect=Exception("Tool failed"))
        ):
            plan = [
                {
                    "id": "step1",
                    "tool": "tool1",
                    "args": {},
                    "abort_on_error": True,
                },
                {"id": "step2", "tool": "tool2", "args": {}, "depends_on": ["step1"]},
            ]
            result = await runner.run_plan(plan)

            assert result["steps"]["step1"]["status"] == "failed"
            assert result["status"] == "partial"
