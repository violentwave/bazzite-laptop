"""Base backend contract for phase-control execution adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from ai.phase_control.result_models import BackendRequest, BackendResult, BackendStatus


def _tail(text: str, max_chars: int = 2000) -> str:
    """Return bounded tail text for normalized result fields."""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


class BaseBackend(ABC):
    """Abstract backend adapter interface."""

    backend_name: str = "base"

    @abstractmethod
    def run(self, request: BackendRequest) -> BackendResult:
        """Execute a request and return a normalized result."""

    def _result(
        self,
        request: BackendRequest,
        *,
        status: BackendStatus,
        summary: str,
        stdout_tail: str = "",
        stderr_tail: str = "",
        artifacts: list[str] | None = None,
        validation_summary: dict | None = None,
        policy_events: list[dict] | None = None,
        exit_code: int = 0,
        suggested_commit_sha: str | None = None,
        started_at: datetime | None = None,
    ) -> BackendResult:
        """Build a normalized backend result with defaults."""
        return BackendResult(
            backend=self.backend_name,
            run_id=request.run_id,
            status=status,
            summary=summary,
            stdout_tail=_tail(stdout_tail),
            stderr_tail=_tail(stderr_tail),
            artifacts=artifacts or [],
            suggested_commit_sha=suggested_commit_sha,
            validation_summary=validation_summary or {},
            policy_events=policy_events or [],
            started_at=started_at or datetime.now(tz=UTC),
            finished_at=datetime.now(tz=UTC),
            exit_code=exit_code,
        )
