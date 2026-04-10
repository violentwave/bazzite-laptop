"""Codex backend adapter for phase-control."""

from __future__ import annotations

from datetime import UTC, datetime

from ai.phase_control.backends.base import BaseBackend
from ai.phase_control.result_models import BackendRequest, BackendStatus


class CodexBackend(BaseBackend):
    """Backend adapter that normalizes Codex execution outcomes."""

    backend_name = "codex"

    def run(self, request: BackendRequest):
        started_at = datetime.now(tz=UTC)
        if not request.execution_prompt.strip():
            return self._result(
                request,
                status=BackendStatus.FAILED,
                summary="codex backend rejected empty execution prompt",
                stderr_tail="execution_prompt is required",
                exit_code=2,
                started_at=started_at,
            )

        return self._result(
            request,
            status=BackendStatus.SUCCESS,
            summary=f"codex backend accepted phase {request.phase_number} execution payload",
            stdout_tail="codex backend dry-run completed",
            started_at=started_at,
        )
