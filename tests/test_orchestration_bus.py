"""Tests for ai/orchestration module."""

import asyncio

import pytest

from ai.orchestration import (
    AgentMessage,
    AgentRegistry,
    AgentResult,
    BaseAgent,
    OrchestrationBus,
    TaskType,
)


class TestAgentMessage:
    """Tests for AgentMessage construction and defaults."""

    def test_agent_message_basic_constructor(self):
        """Test AgentMessage with all required fields."""
        msg = AgentMessage(
            source_agent="agent1",
            target_agent="agent2",
            task_type="test_task",
            payload={"key": "value"},
        )
        assert msg.source_agent == "agent1"
        assert msg.target_agent == "agent2"
        assert msg.task_type == "test_task"
        assert msg.payload == {"key": "value"}

    def test_agent_message_correlation_id_auto_generated(self):
        """Test that correlation_id is auto-generated if not provided."""
        msg1 = AgentMessage(
            source_agent="agent1",
            target_agent="agent2",
            task_type="test",
            payload={},
        )
        msg2 = AgentMessage(
            source_agent="agent1",
            target_agent="agent2",
            task_type="test",
            payload={},
        )
        assert msg1.correlation_id is not None
        assert msg2.correlation_id is not None
        assert msg1.correlation_id != msg2.correlation_id

    def test_agent_message_correlation_id_can_be_provided(self):
        """Test that correlation_id can be provided explicitly."""
        msg = AgentMessage(
            source_agent="agent1",
            target_agent="agent2",
            task_type="test",
            payload={},
            correlation_id="custom-id-123",
        )
        assert msg.correlation_id == "custom-id-123"

    def test_agent_message_priority_default(self):
        """Test that priority defaults to 0."""
        msg = AgentMessage(
            source_agent="agent1",
            target_agent="agent2",
            task_type="test",
            payload={},
        )
        assert msg.priority == 0

    def test_agent_message_priority_can_be_set(self):
        """Test that priority can be set."""
        msg = AgentMessage(
            source_agent="agent1",
            target_agent="agent2",
            task_type="test",
            payload={},
            priority=5,
        )
        assert msg.priority == 5


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    @pytest.fixture
    def registry(self):
        return AgentRegistry()

    @pytest.mark.asyncio
    async def test_register_handler(self, registry):
        """Test registering a handler."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await registry.register("agent1", handler)
        assert await registry.is_registered("agent1")

    @pytest.mark.asyncio
    async def test_get_handler(self, registry):
        """Test retrieving a handler."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await registry.register("agent1", handler)
        retrieved = await registry.get("agent1")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_get_handler_not_found(self, registry):
        """Test getting a non-existent handler returns None."""
        result = await registry.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_agents(self, registry):
        """Test listing registered agents."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await registry.register("agent1", handler)
        await registry.register("agent2", handler)
        agents = await registry.list_agents()
        assert "agent1" in agents
        assert "agent2" in agents
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_is_registered_false(self, registry):
        """Test is_registered returns False for unregistered agent."""
        assert await registry.is_registered("nonexistent") is False

    @pytest.mark.asyncio
    async def test_is_registered_true(self, registry):
        """Test is_registered returns True for registered agent."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await registry.register("agent1", handler)
        assert await registry.is_registered("agent1") is True


class TestOrchestrationBusDispatch:
    """Tests for OrchestrationBus dispatch functionality."""

    @pytest.fixture
    def bus(self):
        return OrchestrationBus()

    @pytest.mark.asyncio
    async def test_dispatch_to_registered_handler(self, bus):
        """Test dispatching a message to a registered handler."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="handler",
                success=True,
                data={"result": "processed"},
            )

        await bus._registry.register("agent1", handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={},
        )
        result = await bus.dispatch(msg)

        assert result.success is True
        assert result.data == {"result": "processed"}
        assert result.source_agent == "handler"

    @pytest.mark.asyncio
    async def test_dispatch_to_unregistered_handler_returns_failure(self, bus):
        """Test dispatching to unregistered handler returns failure result."""
        msg = AgentMessage(
            source_agent="caller",
            target_agent="nonexistent",
            task_type="test",
            payload={},
        )
        result = await bus.dispatch(msg)

        assert result.success is False
        assert "nonexistent" in result.error
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_dispatch_duration_recorded(self, bus):
        """Test that duration_seconds is populated correctly."""
        await asyncio.sleep(0.01)

        async def handler(msg: AgentMessage) -> AgentResult:
            await asyncio.sleep(0.01)
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="handler",
                success=True,
                data={},
            )

        await bus._registry.register("agent1", handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={},
        )
        result = await bus.dispatch(msg)

        assert result.success is True
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_circular_handoff_protection(self, bus):
        """Test that circular handoffs are detected and blocked at depth 5."""
        call_count = 0

        async def recursive_handler(msg: AgentMessage) -> AgentResult:
            nonlocal call_count
            call_count += 1

            if call_count < 10:
                nested_msg = AgentMessage(
                    source_agent=msg.target_agent,
                    target_agent=msg.target_agent,
                    task_type=msg.task_type,
                    payload={},
                    correlation_id=msg.correlation_id,
                )
                return await bus.dispatch(nested_msg)

            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent=msg.target_agent,
                success=True,
                data={},
            )

        await bus._registry.register("agent1", recursive_handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={},
            correlation_id="test-correlation",
        )
        result = await bus.dispatch(msg)

        assert result.success is False
        assert "Circular handoff detected" in result.error
        assert "max depth 5" in result.error

    @pytest.mark.asyncio
    async def test_list_agents(self, bus):
        """Test listing registered agents via bus."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await bus._registry.register("agent1", handler)
        await bus._registry.register("agent2", handler)
        agents = await bus.list_agents()

        assert "agent1" in agents
        assert "agent2" in agents


class TestConcurrentDispatch:
    """Tests for concurrent dispatch using asyncio.gather."""

    @pytest.fixture
    def bus(self):
        return OrchestrationBus()

    @pytest.mark.asyncio
    async def test_concurrent_dispatch_three_messages(self, bus):
        """Test concurrent dispatch with 3 messages."""

        async def handler_a(msg: AgentMessage) -> AgentResult:
            await asyncio.sleep(0.01)
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="agent-a",
                success=True,
                data={"agent": "a"},
            )

        async def handler_b(msg: AgentMessage) -> AgentResult:
            await asyncio.sleep(0.01)
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="agent-b",
                success=True,
                data={"agent": "b"},
            )

        async def handler_c(msg: AgentMessage) -> AgentResult:
            await asyncio.sleep(0.01)
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="agent-c",
                success=True,
                data={"agent": "c"},
            )

        await bus._registry.register("agent-a", handler_a)
        await bus._registry.register("agent-b", handler_b)
        await bus._registry.register("agent-c", handler_c)

        msg_a = AgentMessage(
            source_agent="caller", target_agent="agent-a", task_type="test", payload={}
        )
        msg_b = AgentMessage(
            source_agent="caller", target_agent="agent-b", task_type="test", payload={}
        )
        msg_c = AgentMessage(
            source_agent="caller", target_agent="agent-c", task_type="test", payload={}
        )

        results = await asyncio.gather(
            bus.dispatch(msg_a), bus.dispatch(msg_b), bus.dispatch(msg_c)
        )

        assert all(r.success for r in results)
        assert results[0].data["agent"] == "a"
        assert results[1].data["agent"] == "b"
        assert results[2].data["agent"] == "c"

    @pytest.mark.asyncio
    async def test_concurrent_same_agent(self, bus):
        """Test concurrent dispatch to same agent."""
        call_count = 0

        async def handler(msg: AgentMessage) -> AgentResult:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="agent1",
                success=True,
                data={"count": call_count},
            )

        await bus._registry.register("agent1", handler)

        msgs = [
            AgentMessage(source_agent="caller", target_agent="agent1", task_type="test", payload={})
            for _ in range(5)
        ]

        results = await asyncio.gather(*[bus.dispatch(msg) for msg in msgs])

        assert all(r.success for r in results)
        assert len(results) == 5


class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    @pytest.mark.asyncio
    async def test_base_agent_can_handle(self):
        """Test BaseAgent.can_handle method."""

        class TestAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "test-agent"

            @property
            def supported_task_types(self) -> list[str]:
                return ["task1", "task2"]

            async def handle(self, message: AgentMessage) -> AgentResult:
                return AgentResult(
                    correlation_id=message.correlation_id,
                    source_agent=self.name,
                    success=True,
                    data={},
                )

        agent = TestAgent()
        assert agent.can_handle("task1") is True
        assert agent.can_handle("task2") is True
        assert agent.can_handle("task3") is False


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_has_required_values(self):
        """Test that required TaskType values exist."""
        assert TaskType.SCAN_IOC == "scan_ioc"
        assert TaskType.RUN_AUDIT == "run_audit"
        assert TaskType.CHECK_CVE_FRESHNESS == "check_cve_freshness"
        assert TaskType.LINT_CHECK == "lint_check"
        assert TaskType.AST_QUERY == "ast_query"
        assert TaskType.SUGGEST_REFACTOR == "suggest_refactor"
        assert TaskType.PROFILE_TOOL == "profile_tool"
        assert TaskType.DETECT_REGRESSION == "detect_regression"
        assert TaskType.TUNE_CACHE == "tune_cache"
        assert TaskType.STORE_INSIGHT == "store_insight"
        assert TaskType.RETRIEVE_CONTEXT == "retrieve_context"
        assert TaskType.SUMMARIZE_SESSION == "summarize_session"
        assert TaskType.CHECK_TIMERS == "check_timers"
        assert TaskType.ALERT_STALE == "alert_stale"
        assert TaskType.RESCHEDULE == "reschedule"


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_agent_result_required_fields(self):
        """Test AgentResult with required fields only."""
        result = AgentResult(
            correlation_id="corr-123",
            source_agent="agent1",
            success=True,
            data={"key": "value"},
        )
        assert result.correlation_id == "corr-123"
        assert result.source_agent == "agent1"
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.duration_seconds == 0.0

    def test_agent_result_optional_fields(self):
        """Test AgentResult with optional fields."""
        result = AgentResult(
            correlation_id="corr-123",
            source_agent="agent1",
            success=False,
            data={},
            error="Something went wrong",
            duration_seconds=1.5,
        )
        assert result.error == "Something went wrong"
        assert result.duration_seconds == 1.5


class TestBusLifecycle:
    """Tests for OrchestrationBus lifecycle and edge cases."""

    @pytest.fixture
    def bus(self):
        return OrchestrationBus()

    @pytest.mark.asyncio
    async def test_bus_start_and_stop(self, bus):
        """Test bus can be started and stopped."""
        await bus.start()
        assert bus._running is True

        await bus.stop()
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_dispatch_error_handling(self, bus):
        """Test dispatch handles handler exceptions gracefully."""

        async def failing_handler(msg: AgentMessage) -> AgentResult:
            raise ValueError("Handler failed")

        await bus._registry.register("failing", failing_handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="failing",
            task_type="test",
            payload={},
        )
        result = await bus.dispatch(msg)

        assert result.success is False
        assert "Handler failed" in result.error
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_bus_publish_alias(self, bus):
        """Test that publish() is an alias for dispatch()."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="handler",
                success=True,
                data={"via": "publish"},
            )

        await bus._registry.register("agent1", handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={},
        )
        result = await bus.publish(msg)

        assert result.success is True
        assert result.data == {"via": "publish"}

    @pytest.mark.asyncio
    async def test_bus_send_alias(self, bus):
        """Test that send() is an alias for dispatch()."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="handler",
                success=True,
                data={"via": "send"},
            )

        await bus._registry.register("agent1", handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={},
        )
        result = await bus.send(msg)

        assert result.success is True
        assert result.data == {"via": "send"}

    @pytest.mark.asyncio
    async def test_registry_unregister(self, bus):
        """Test unregistering a handler."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await bus._registry.register("agent1", handler)
        assert await bus._registry.is_registered("agent1")

        await bus._registry.unregister("agent1")
        assert await bus._registry.is_registered("agent1") is False

    @pytest.mark.asyncio
    async def test_registry_clear(self, bus):
        """Test clearing all handlers."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="test",
                success=True,
                data={},
            )

        await bus._registry.register("agent1", handler)
        await bus._registry.register("agent2", handler)

        await bus._registry.clear()
        agents = await bus._registry.list_agents()
        assert len(agents) == 0

    @pytest.mark.asyncio
    async def test_message_with_empty_payload(self, bus):
        """Test dispatch with empty payload dict."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="handler",
                success=True,
                data={"received_payload": msg.payload},
            )

        await bus._registry.register("agent1", handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={},
        )
        result = await bus.dispatch(msg)

        assert result.success is True
        assert result.data["received_payload"] == {}

    @pytest.mark.asyncio
    async def test_message_with_complex_payload(self, bus):
        """Test dispatch with complex nested payload."""

        async def handler(msg: AgentMessage) -> AgentResult:
            return AgentResult(
                correlation_id=msg.correlation_id,
                source_agent="handler",
                success=True,
                data={"payload_size": len(msg.payload["items"])},
            )

        await bus._registry.register("agent1", handler)
        msg = AgentMessage(
            source_agent="caller",
            target_agent="agent1",
            task_type="test",
            payload={"items": [1, 2, 3, 4, 5], "meta": {"key": "value"}},
        )
        result = await bus.dispatch(msg)

        assert result.success is True
        assert result.data["payload_size"] == 5
