"""Comprehensive tests for orchestration registry/bus/runner behavior."""

import asyncio
from unittest.mock import AsyncMock

from ai.orchestration.bus import OrchestrationBus
from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType
from ai.orchestration.registry import AgentRegistry
from ai.workflows.definitions import MORNING_BRIEFING_ENRICHED, SECURITY_DEEP_SCAN
from ai.workflows.runner import WorkflowRunner


class MockAgent(BaseAgent):
    """Simple BaseAgent implementation for test routing/lifecycle."""

    def __init__(self, name: str, task_types: list[str]):
        self._name = name
        self._task_types = task_types
        self.state = "stopped"

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_task_types(self) -> list[str]:
        return self._task_types

    async def handle(self, message: AgentMessage) -> AgentResult:
        return AgentResult(
            correlation_id=message.correlation_id,
            source_agent=self.name,
            success=True,
            data={"handled": message.task_type},
        )

    async def start(self) -> None:
        self.state = "running"

    async def stop(self) -> None:
        self.state = "stopped"


def test_agent_registry_register_deregister():
    """register a mock agent, verify listed, deregister, verify removed."""
    registry = AgentRegistry()
    agent = MockAgent("test-agent", [TaskType.GENERAL.value])

    asyncio.run(registry.register(agent.name, agent.handle))
    assert agent.name in asyncio.run(registry.list_agents())

    asyncio.run(registry.unregister(agent.name))
    assert agent.name not in asyncio.run(registry.list_agents())


def test_agent_registry_get_by_task_type():
    """register per-task-type agents and verify routing picks correct handler."""
    registry = AgentRegistry()
    security_agent = MockAgent("security-agent", [TaskType.SECURITY_AUDIT.value])
    code_agent = MockAgent("code-agent", [TaskType.CODE_QUALITY.value])
    agents = [security_agent, code_agent]

    for agent in agents:
        asyncio.run(registry.register(agent.name, agent.handle))

    def route_task(task_type: str) -> str:
        return next(agent.name for agent in agents if agent.can_handle(task_type))

    routed_security = route_task(TaskType.SECURITY_AUDIT.value)
    routed_code = route_task(TaskType.CODE_QUALITY.value)

    security_handler = asyncio.run(registry.get(routed_security))
    code_handler = asyncio.run(registry.get(routed_code))

    assert security_handler is not None
    assert code_handler is not None

    security_result = asyncio.run(
        security_handler(
            AgentMessage(
                source_agent="tester",
                target_agent=routed_security,
                task_type=TaskType.SECURITY_AUDIT.value,
                payload={},
            )
        )
    )
    code_result = asyncio.run(
        code_handler(
            AgentMessage(
                source_agent="tester",
                target_agent=routed_code,
                task_type=TaskType.CODE_QUALITY.value,
                payload={},
            )
        )
    )

    assert security_result.source_agent == "security-agent"
    assert code_result.source_agent == "code-agent"


def test_orchestration_bus_message_delivery():
    """publish an AgentMessage and verify a subscriber receives it."""
    bus = OrchestrationBus()
    received: list[AgentMessage] = []

    async def dispatch_handler(message: AgentMessage) -> AgentResult:
        return AgentResult(
            correlation_id=message.correlation_id,
            source_agent="test-agent",
            success=True,
            data={"ok": True},
        )

    async def subscriber(message: AgentMessage) -> None:
        received.append(message)

    asyncio.run(bus.registry.register("test-agent", dispatch_handler))
    bus._subscriptions["test-agent"].append(subscriber)

    message = AgentMessage(
        source_agent="sender",
        target_agent="test-agent",
        task_type=TaskType.GENERAL.value,
        payload={"test": "data"},
    )

    result = asyncio.run(bus.publish(message))
    assert result.success is True
    assert len(received) == 1
    assert received[0].payload == {"test": "data"}


def test_base_agent_lifecycle():
    """start/stop a BaseAgent subclass and verify state transitions."""
    agent = MockAgent("lifecycle-agent", [TaskType.GENERAL.value])

    assert agent.state == "stopped"
    asyncio.run(agent.start())
    assert agent.state == "running"

    result = asyncio.run(
        agent.handle(
            AgentMessage(
                source_agent="tester",
                target_agent=agent.name,
                task_type=TaskType.GENERAL.value,
                payload={"action": "ping"},
            )
        )
    )
    assert result.success is True
    assert result.data["handled"] == TaskType.GENERAL.value

    asyncio.run(agent.stop())
    assert agent.state == "stopped"


def test_workflow_run_executes_steps():
    """run a 2-step workflow and verify both mocked tool calls execute."""
    runner = WorkflowRunner()
    runner._execute_tool = AsyncMock(side_effect=["step1-ok", "step2-ok"])

    plan = [
        {"id": "step_1", "tool": "tool.one", "args": {}},
        {"id": "step_2", "tool": "tool.two", "args": {}, "depends_on": ["step_1"]},
    ]
    result = asyncio.run(runner.run_plan(plan))

    assert runner._execute_tool.await_count == 2
    assert result["steps"]["step_1"]["status"] == "complete"
    assert result["steps"]["step_2"]["status"] == "complete"
    assert result["status"] == "complete"


def test_workflow_run_handles_step_failure():
    """if step 1 fails, workflow is partial and step 2 is not called."""
    runner = WorkflowRunner()
    runner._execute_tool = AsyncMock(side_effect=RuntimeError("step 1 failed"))

    plan = [
        {"id": "step_1", "tool": "tool.one", "args": {}, "abort_on_error": True},
        {"id": "step_2", "tool": "tool.two", "args": {}, "depends_on": ["step_1"]},
    ]
    result = asyncio.run(runner.run_plan(plan))

    assert runner._execute_tool.await_count == 1
    assert result["steps"]["step_1"]["status"] == "failed"
    assert "step_2" not in result["steps"]
    assert result["status"] == "partial"


def test_named_workflow_security_deep_scan_structure():
    """verify security_deep_scan has six steps and expected dependencies."""
    steps = SECURITY_DEEP_SCAN["steps"]
    assert len(steps) == 6

    deps_map = {step["id"]: step.get("depends_on", []) for step in steps}
    assert deps_map["av_scan"] == []
    assert deps_map["log_ingest"] == []
    assert deps_map["cve_check"] == ["log_ingest"]
    assert deps_map["threat_summary"] == ["log_ingest"]
    assert deps_map["alert_summary"] == ["log_ingest"]
    assert set(deps_map["full_audit"]) == {"cve_check", "threat_summary", "alert_summary"}


def test_named_workflow_morning_briefing_has_memory_step():
    """verify morning_briefing_enriched includes memory.search step."""
    steps = MORNING_BRIEFING_ENRICHED["steps"]
    memory_step = next(step for step in steps if step["id"] == "memory_context")
    collect_step = next(step for step in steps if step["id"] == "collect")

    assert memory_step["tool"] == "memory.search"
    assert collect_step["depends_on"] == ["memory_context", "security", "code", "perf", "timers"]
