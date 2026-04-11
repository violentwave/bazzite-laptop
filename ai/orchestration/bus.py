"""Pub/sub message bus for inter-agent communication."""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.registry import AgentRegistry

logger = logging.getLogger(__name__)

MessageHandler = Callable[[AgentMessage], Awaitable[AgentResult]]

MAX_HANDOFD_DEPTH = 5


class OrchestrationBus:
    """Async pub/sub bus for dispatching messages between agents."""

    def __init__(self) -> None:
        self._registry = AgentRegistry()
        self._subscriptions: dict[str, list[Callable[[AgentMessage], Awaitable[None]]]] = (
            defaultdict(list)
        )
        self._sub_lock = asyncio.Lock()
        self._running = False
        self._correlation_stack: dict[str, int] = defaultdict(int)

    @property
    def registry(self) -> AgentRegistry:
        """Access the agent registry."""
        return self._registry

    async def start(self) -> None:
        """Start the bus (no-op placeholder for lifecycle management)."""
        self._running = True
        logger.info("OrchestrationBus started")

    async def stop(self) -> None:
        """Stop the bus and clear all subscriptions."""
        self._running = False
        async with self._sub_lock:
            self._subscriptions.clear()
        self._correlation_stack.clear()
        logger.info("OrchestrationBus stopped")

    async def subscribe(
        self,
        agent_name: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        """Subscribe a handler to messages for a specific agent."""
        await self._registry.register(agent_name, handler)
        async with self._sub_lock:
            self._subscriptions[agent_name].append(handler)
            logger.debug("Subscribed %s to agent %s", handler, agent_name)

    async def unsubscribe(
        self,
        agent_name: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        """Unsubscribe a handler from an agent's messages."""
        await self._registry.unregister(agent_name)
        async with self._sub_lock:
            if handler in self._subscriptions[agent_name]:
                self._subscriptions[agent_name].remove(handler)
                logger.debug("Unsubscribed %s from agent %s", handler, agent_name)

    async def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return await self._registry.list_agents()

    async def dispatch(self, message: AgentMessage) -> AgentResult:
        """Dispatch a message to its target agent with circular handoff protection."""
        correlation_id = message.correlation_id

        self._correlation_stack[correlation_id] += 1
        depth = self._correlation_stack[correlation_id]

        if depth > MAX_HANDOFD_DEPTH:
            logger.error(
                "Circular handoff detected for correlation_id=%s, depth=%d",
                correlation_id,
                depth,
            )
            return AgentResult(
                correlation_id=correlation_id,
                source_agent=message.target_agent,
                success=False,
                data={},
                error=f"Circular handoff detected: max depth {MAX_HANDOFD_DEPTH} exceeded",
                duration_seconds=0.0,
            )

        start_time = time.monotonic()
        handler = await self._registry.get(message.target_agent)

        if handler is None:
            logger.warning("No handler for agent: %s", message.target_agent)
            duration = time.monotonic() - start_time
            return AgentResult(
                correlation_id=correlation_id,
                source_agent=message.target_agent,
                success=False,
                data={},
                error=f"No handler registered for agent: {message.target_agent}",
                duration_seconds=duration,
            )

        try:
            result = await handler(message)
            result.duration_seconds = time.monotonic() - start_time
            await self._notify_subscribers(message)
            return result
        except Exception as e:
            logger.exception("Error handling message for %s", message.target_agent)
            duration = time.monotonic() - start_time
            return AgentResult(
                correlation_id=correlation_id,
                source_agent=message.target_agent,
                success=False,
                data={},
                error=str(e),
                duration_seconds=duration,
            )
        finally:
            self._correlation_stack[correlation_id] -= 1
            if self._correlation_stack[correlation_id] == 0:
                del self._correlation_stack[correlation_id]

    async def publish(self, message: AgentMessage) -> AgentResult:
        """Publish a message to its target agent and notify subscribers."""
        return await self.dispatch(message)

    async def _notify_subscribers(self, message: AgentMessage) -> None:
        """Notify all subscribers of a message."""
        handlers = self._subscriptions.get(message.target_agent, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception:
                logger.exception("Error in subscriber for %s", message.target_agent)

    async def send(self, message: AgentMessage) -> AgentResult:
        """Alias for publish() for ergonomic API."""
        return await self.dispatch(message)


# Note: get_default_bus() and get_default_bus_async() are defined in ai.orchestration.__init__
# to ensure proper agent registration. Import from there instead of from this module.
