"""Tests for MCP workflow tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.mcp_bridge.handlers import workflow_tools


class TestWorkflowList:
    """Tests for workflow_list tool."""

    @pytest.mark.asyncio
    async def test_workflow_list_returns_workflows_key(self):
        """Test workflow_list returns dict with workflows key containing 3 entries."""
        result = await workflow_tools.workflow_list({})

        assert "workflows" in result
        assert len(result["workflows"]) == 3
        assert all("name" in wf for wf in result["workflows"])
        assert all("description" in wf for wf in result["workflows"])


class TestWorkflowRun:
    """Tests for workflow_run tool."""

    @pytest.mark.asyncio
    async def test_workflow_run_with_valid_name_returns_status(self):
        """Test workflow_run with valid name returns status key."""
        with patch("ai.workflows.runner.WorkflowRunner") as MockRunner:
            mock_runner = MagicMock()
            mock_runner.run_plan = AsyncMock(
                return_value={
                    "status": "complete",
                    "steps": {"step1": {"status": "complete"}},
                }
            )
            MockRunner.return_value = mock_runner

            with patch("ai.rag.store.VectorStore"):
                result = await workflow_tools.workflow_run({"name": "security_deep_scan"})

        assert "status" in result
        assert result["workflow"] == "security_deep_scan"

    @pytest.mark.asyncio
    async def test_workflow_run_with_unknown_name_returns_error(self):
        """Test workflow_run with unknown name returns error key."""
        result = await workflow_tools.workflow_run({"name": "nonexistent_workflow"})

        assert "error" in result
        assert "Unknown workflow" in result["error"]


class TestWorkflowStatus:
    """Tests for workflow_status tool."""

    @pytest.mark.asyncio
    async def test_workflow_status_queries_lancedb(self):
        """Test workflow_status queries LanceDB workflow_runs table."""
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__getitem__ = MagicMock(
            return_value=MagicMock(
                sort_values=MagicMock(
                    return_value=MagicMock(
                        empty=False,
                        iloc=MagicMock(
                            return_value=MagicMock(
                                __getitem__=lambda self, key: {
                                    "run_id": "123",
                                    "workflow_name": "security_deep_scan",
                                    "status": "complete",
                                    "started_at": "2024-01-01T00:00:00",
                                    "completed_at": "2024-01-01T00:01:00",
                                    "step_count": 3,
                                    "steps_completed": 3,
                                    "error": "",
                                }[key]
                            )
                        ),
                    )
                )
            )
        )

        mock_table = MagicMock()
        mock_table.to_pandas = MagicMock(return_value=mock_df)

        with patch("ai.rag.store.VectorStore") as MockStore:
            mock_store = MagicMock()
            mock_store._get_schemas = MagicMock(return_value={"workflow_runs": MagicMock()})
            mock_store._ensure_table = MagicMock(return_value=mock_table)
            MockStore.return_value = mock_store

            result = await workflow_tools.workflow_status({"name": "security_deep_scan"})

        assert "runs" in result


class TestWorkflowAgents:
    """Tests for workflow_agents tool."""

    @pytest.mark.asyncio
    async def test_workflow_agents_returns_agents_with_task_types(self):
        """Test workflow_agents returns agents list with task_types."""
        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.list_agents = AsyncMock(
                return_value=[
                    "security",
                    "code_quality",
                    "performance",
                    "knowledge",
                    "timer_sentinel",
                ]
            )
            mock_bus.registry.get = AsyncMock(return_value=AsyncMock())
            mock_get_bus.return_value = mock_bus

            result = await workflow_tools.workflow_agents({})

        assert "agents" in result
        assert len(result["agents"]) == 5
        assert all("name" in agent for agent in result["agents"])
        assert all("task_types" in agent for agent in result["agents"])


class TestWorkflowHandoff:
    """Tests for workflow_handoff tool."""

    @pytest.mark.asyncio
    async def test_workflow_handoff_dispatches_via_bus(self):
        """Test workflow_handoff dispatches message via mocked bus."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"result": "ok"}
        mock_result.error = None

        with patch("ai.orchestration.get_default_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_bus.dispatch = AsyncMock(return_value=mock_result)
            mock_get_bus.return_value = mock_bus

            result = await workflow_tools.workflow_handoff(
                {"agent": "security", "task_type": "run_audit", "payload": {"key": "value"}}
            )

        assert result["success"] is True
        assert result["data"] == {"result": "ok"}
        mock_bus.dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_handoff_missing_params_returns_error(self):
        """Test workflow_handoff with missing agent/task_type returns error."""
        result = await workflow_tools.workflow_handoff({})

        assert "error" in result


class TestWorkflowHistory:
    """Tests for workflow_history tool."""

    @pytest.mark.asyncio
    async def test_workflow_history_queries_with_limit(self):
        """Test workflow_history queries with limit param."""
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__getitem__ = MagicMock(
            return_value=MagicMock(
                sort_values=MagicMock(return_value=MagicMock(head=MagicMock(return_value=[])))
            )
        )

        mock_table = MagicMock()
        mock_table.to_pandas = MagicMock(return_value=mock_df)

        with patch("ai.rag.store.VectorStore") as MockStore:
            mock_store = MagicMock()
            mock_store._get_schemas = MagicMock(return_value={"workflow_runs": MagicMock()})
            mock_store._ensure_table = MagicMock(return_value=mock_table)
            MockStore.return_value = mock_store

            result = await workflow_tools.workflow_history({"limit": 5})

        assert "runs" in result


class TestModuleImports:
    """Smoke test for module imports."""

    def test_all_6_tools_importable(self):
        """Test all 6 workflow tools are importable from workflow_tools module."""
        from ai.mcp_bridge.handlers import workflow_tools

        assert hasattr(workflow_tools, "workflow_list")
        assert hasattr(workflow_tools, "workflow_run")
        assert hasattr(workflow_tools, "workflow_status")
        assert hasattr(workflow_tools, "workflow_agents")
        assert hasattr(workflow_tools, "workflow_handoff")
        assert hasattr(workflow_tools, "workflow_history")
