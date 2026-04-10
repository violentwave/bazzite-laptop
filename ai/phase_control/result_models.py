"""Normalized backend request/result models for phase-control."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class BackendStatus(StrEnum):
    """Allowed normalized backend statuses."""

    SUCCESS = "success"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ValidationCommandResult:
    """Single validation command result."""

    command: str
    passed: bool
    exit_code: int
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass
class ValidationSummary:
    """Validation gate summary across all commands."""

    passed: bool
    commands: list[ValidationCommandResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a serializable dictionary."""
        return {
            "passed": self.passed,
            "commands": [
                {
                    "command": c.command,
                    "passed": c.passed,
                    "exit_code": c.exit_code,
                    "stdout_tail": c.stdout_tail,
                    "stderr_tail": c.stderr_tail,
                }
                for c in self.commands
            ],
        }


@dataclass
class BackendRequest:
    """Normalized backend execution request."""

    run_id: str
    phase_name: str
    phase_number: int
    repo_path: str
    branch_name: str | None
    execution_prompt: str
    allowed_tools: list[str]
    validation_commands: list[str]
    execution_mode: str
    risk_tier: str
    approval_required: bool
    timeout_seconds: int
    env_allowlist: list[str]
    artifacts_dir: str


@dataclass
class BackendResult:
    """Normalized backend execution result."""

    backend: str
    run_id: str
    status: BackendStatus
    summary: str
    stdout_tail: str
    stderr_tail: str
    artifacts: list[str]
    validation_summary: dict[str, Any]
    policy_events: list[dict[str, Any]]
    started_at: datetime
    finished_at: datetime
    exit_code: int
    suggested_commit_sha: str | None = None

    @staticmethod
    def now() -> datetime:
        """Timezone-aware timestamp helper."""
        return datetime.now(tz=UTC)
