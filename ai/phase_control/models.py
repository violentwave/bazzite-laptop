"""Core models for phase-control orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class PhaseStatus(StrEnum):
    """Allowed phase lifecycle statuses."""

    PLANNED = "Planned"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    NEEDS_REVIEW = "Needs Review"
    BLOCKED = "Blocked"
    CANCELLED = "Cancelled"


@dataclass
class PhaseRow:
    """Normalized phase row data used by the control-plane runner."""

    phase_name: str
    phase_number: int
    status: PhaseStatus = PhaseStatus.PLANNED
    execution_prompt: str = ""
    validation_commands: list[str] = field(default_factory=list)
    done_criteria: list[str] = field(default_factory=list)
    dependencies: list[int] = field(default_factory=list)
    backend: str = "codex"
    branch_name: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    execution_mode: str = "safe"
    risk_tier: str = "medium"
    approval_required: bool = False
    approval_granted: bool = False
    timeout_seconds: int = 1800
    env_allowlist: list[str] = field(default_factory=list)
    artifacts_dir: str = ""
    run_id: str | None = None
    runner_host: str | None = None
    started_at: datetime | None = None
    lease_expires_at: datetime | None = None
    slack_channel: str | None = None
    slack_thread_ts: str | None = None
    blocker: str | None = None
    validation_summary: dict[str, Any] | None = None
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_active_lease(self, now: datetime | None = None) -> bool:
        """Return True when the current lease has not expired."""
        if self.run_id is None or self.lease_expires_at is None:
            return False
        check_now = now or datetime.now(tz=UTC)
        return self.lease_expires_at > check_now
