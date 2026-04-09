"""Agent handler registry — maps agent names to async handler callables."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from ai.orchestration.message import AgentMessage, AgentResult

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Thread-safe registry mapping agent names to handler coroutines."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[AgentMessage], Awaitable[AgentResult]]] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        name: str,
        handler: Callable[[AgentMessage], Awaitable[AgentResult]],
    ) -> None:
        """Register an async handler for a named agent."""
        async with self._lock:
            self._handlers[name] = handler
            logger.info("Registered agent handler: %s", name)

    async def unregister(self, name: str) -> None:
        """Unregister the handler for a named agent."""
        async with self._lock:
            self._handlers.pop(name, None)
            logger.info("Unregistered agent handler: %s", name)

    async def get_handler(
        self, name: str
    ) -> Callable[[AgentMessage], Awaitable[AgentResult]] | None:
        """Retrieve the handler for a named agent, or None if not found."""
        async with self._lock:
            return self._handlers.get(name)

    async def list_agents(self) -> list[str]:
        """List all registered agent names."""
        async with self._lock:
            return list(self._handlers.keys())

    async def clear(self) -> None:
        """Clear all registered handlers."""
        async with self._lock:
            self._handlers.clear()
            logger.info("Cleared all agent handlers")
