"""Typed message envelopes for inter-agent communication."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class AgentMessage:
    """Task dispatch envelope sent from one agent (or workflow) to another."""

    source_agent: str
    target_agent: str
    task_type: str
    payload: dict
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AgentResult:
    """Result returned by an agent after handling an AgentMessage."""

    correlation_id: str
    source_agent: str
    success: bool
    data: dict
    error: str | None = None
    duration_seconds: float = 0.0
