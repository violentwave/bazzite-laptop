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
    SCAN_IOC = "scan_ioc"
    RUN_AUDIT = "run_audit"
    CHECK_CVE_FRESHNESS = "check_cve_freshness"
    LINT_CHECK = "lint_check"
    AST_QUERY = "ast_query"
    SUGGEST_REFACTOR = "suggest_refactor"
    PROFILE_TOOL = "profile_tool"
    DETECT_REGRESSION = "detect_regression"
    TUNE_CACHE = "tune_cache"
    STORE_INSIGHT = "store_insight"
    RETRIEVE_CONTEXT = "retrieve_context"
    SUMMARIZE_SESSION = "summarize_session"
    CHECK_TIMERS = "check_timers"
    ALERT_STALE = "alert_stale"
    RESCHEDULE = "reschedule"


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

    @property
    @abstractmethod
    def supported_task_types(self) -> list[str]:
        """List of task types this agent can handle."""

    @abstractmethod
    async def handle(self, message: AgentMessage) -> AgentResult:
        """Handle an incoming message and return a result."""
        ...

    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle the given task type."""
        return task_type in self.supported_task_types


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
