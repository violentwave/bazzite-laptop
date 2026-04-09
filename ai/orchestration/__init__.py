"""Agent orchestration bus for bazzite-laptop AI layer.

Provides async pub/sub message dispatch between named agents.
Import get_default_bus() to access the singleton bus with all 5 agents pre-registered.
"""

from ai.orchestration.bus import OrchestrationBus, get_default_bus
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
