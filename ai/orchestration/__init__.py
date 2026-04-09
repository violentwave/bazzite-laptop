"""Agent orchestration bus for bazzite-laptop AI layer.

Provides async pub/sub message dispatch between named agents.
Import get_default_bus() to access the singleton bus with all 5 agents pre-registered.
"""

import asyncio

from ai.orchestration.bus import OrchestrationBus
from ai.orchestration.message import AgentMessage, AgentResult
from ai.orchestration.protocol import BaseAgent, TaskType
from ai.orchestration.registry import AgentRegistry

__all__ = [
    "OrchestrationBus",
    "AgentMessage",
    "AgentResult",
    "AgentRegistry",
    "BaseAgent",
    "TaskType",
    "get_default_bus",
]


_default_bus: OrchestrationBus | None = None


def get_default_bus() -> OrchestrationBus:
    """Get or create the default orchestration bus singleton with all agents registered."""
    global _default_bus
    if _default_bus is None:
        _default_bus = OrchestrationBus()
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_register_default_agents(_default_bus))
        else:
            import warnings

            warnings.warn(
                "get_default_bus() called from within async context - "
                "registration skipped (call from sync context to initialize)",
                RuntimeWarning,
                stacklevel=2,
            )
    return _default_bus


async def _register_default_agents(bus: OrchestrationBus) -> None:
    """Register all 5 default agents with the bus."""
    from ai.agents.code_quality_adapter import CodeQualityAgent
    from ai.agents.knowledge_storage_adapter import KnowledgeStorageAgent
    from ai.agents.performance_tuning_adapter import PerformanceTuningAgent
    from ai.agents.security_audit_adapter import SecurityAuditAgent
    from ai.agents.timer_sentinel_adapter import TimerSentinelAgent

    for agent in [
        SecurityAuditAgent(),
        CodeQualityAgent(),
        PerformanceTuningAgent(),
        KnowledgeStorageAgent(),
        TimerSentinelAgent(),
    ]:
        await bus.registry.register(agent.name, agent.handle)
