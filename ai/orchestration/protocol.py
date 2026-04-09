"""Agent protocol definitions — base classes and constants."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from ai.orchestration.message import AgentMessage, AgentResult


class TaskType(StrEnum):
    """Task type constants for agent dispatch."""

    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_TUNING = "performance_tuning"
    KNOWLEDGE_STORAGE = "knowledge_storage"
    CODE_QUALITY = "code_quality"
    TIMER_HEALTH = "timer_health"
    GENERAL = "general"


@dataclass
class TaskContext:
    """Context passed to agents when handling tasks."""

    task_id: str = uuid.uuid4().__str__()
    task_type: TaskType = TaskType.GENERAL
    payload: dict = None  # type: ignore[assignment]
    correlation_id: str = uuid.uuid4().__str__()


class BaseAgent(ABC):
    """Abstract base class for all orchestration agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this agent."""

    @abstractmethod
    async def handle(self, message: AgentMessage) -> AgentResult:
        """Handle an incoming message and return a result."""
        ...


class HandoffProtocol:
    """Protocol for agent-to-agent handoff with acknowledgment."""

    @staticmethod
    def create_handoff_message(
        from_agent: str,
        to_agent: str,
        task_type: TaskType,
        payload: dict,
        priority: int = 0,
    ) -> AgentMessage:
        """Create a standardized handoff message between agents."""
        return AgentMessage(
            source_agent=from_agent,
            target_agent=to_agent,
            task_type=task_type.value,
            payload=payload,
            priority=priority,
        )

    @staticmethod
    def validate_handoff(message: AgentMessage) -> bool:
        """Validate that a message has required handoff fields."""
        return (
            message.source_agent
            and message.target_agent
            and message.task_type
            and message.payload is not None
        )
