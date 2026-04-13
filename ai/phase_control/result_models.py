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
    preflight_summary: str = ""
    preflight_record: dict[str, Any] | None = None


@dataclass
class PreflightRecord:
    """Project-intelligence preflight record for execution gating."""

    schema_version: str
    generated_at: str
    phase_context: dict[str, Any]
    artifact_context: dict[str, Any]
    code_context: dict[str, Any]
    pattern_context: dict[str, Any]
    health_signals: dict[str, Any]
    gate: dict[str, Any]
    summary: str
    source_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a serializable dictionary."""
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "phase_context": self.phase_context,
            "artifact_context": self.artifact_context,
            "code_context": self.code_context,
            "pattern_context": self.pattern_context,
            "health_signals": self.health_signals,
            "gate": self.gate,
            "summary": self.summary,
            "source_errors": list(self.source_errors),
        }


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
