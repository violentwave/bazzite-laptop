"""Pub/sub message bus for inter-agent communication."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.registry import AgentRegistry

logger = logging.getLogger(__name__)

MessageHandler = Callable[[AgentMessage], Awaitable[AgentResult]]


class OrchestrationBus:
    """Async pub/sub bus for dispatching messages between agents."""

    def __init__(self) -> None:
        self._registry = AgentRegistry()
        self._subscriptions: dict[str, list[Callable[[AgentMessage], Awaitable[None]]]] = (
            defaultdict(list)
        )
        self._sub_lock = asyncio.Lock()
        self._running = False

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
        logger.info("OrchestrationBus stopped")

    async def subscribe(
        self,
        agent_name: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        """Subscribe a handler to messages for a specific agent."""
        async with self._sub_lock:
            self._subscriptions[agent_name].append(handler)
            logger.debug("Subscribed %s to agent %s", handler, agent_name)

    async def unsubscribe(
        self,
        agent_name: str,
        handler: Callable[[AgentMessage], Awaitable[None]],
    ) -> None:
        """Unsubscribe a handler from an agent's messages."""
        async with self._sub_lock:
            if handler in self._subscriptions[agent_name]:
                self._subscriptions[agent_name].remove(handler)
                logger.debug("Unsubscribed %s from agent %s", handler, agent_name)

    async def publish(self, message: AgentMessage) -> AgentResult:
        """Publish a message to its target agent and notify subscribers."""
        handler = await self._registry.get_handler(message.target_agent)
        if handler is None:
            logger.warning("No handler for agent: %s", message.target_agent)
            return AgentResult(
                correlation_id=message.correlation_id,
                source_agent=message.target_agent,
                success=False,
                data={},
                error=f"No handler registered for agent: {message.target_agent}",
            )

        try:
            result = await handler(message)
            await self._notify_subscribers(message)
            return result
        except Exception as e:
            logger.exception("Error handling message for %s", message.target_agent)
            return AgentResult(
                correlation_id=message.correlation_id,
                source_agent=message.target_agent,
                success=False,
                data={},
                error=str(e),
            )

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
        return await self.publish(message)


_default_bus: OrchestrationBus | None = None


async def get_default_bus() -> OrchestrationBus:
    """Get or create the default orchestration bus singleton."""
    global _default_bus
    if _default_bus is None:
        _default_bus = OrchestrationBus()
        await _default_bus.start()
    return _default_bus
