"""Claude Code backend adapter for phase-control."""

from __future__ import annotations

from datetime import UTC, datetime

from ai.phase_control.backends.base import BaseBackend
from ai.phase_control.result_models import BackendRequest, BackendStatus


class ClaudeCodeBackend(BaseBackend):
    """Backend adapter that normalizes Claude Code execution outcomes."""

    backend_name = "claude_code"

    def run(self, request: BackendRequest):
        started_at = datetime.now(tz=UTC)
        if not request.execution_prompt.strip():
            return self._result(
                request,
                status=BackendStatus.FAILED,
                summary="claude_code backend rejected empty execution prompt",
                stderr_tail="execution_prompt is required",
                exit_code=2,
                started_at=started_at,
            )

        return self._result(
            request,
            status=BackendStatus.SUCCESS,
            summary=f"claude_code backend accepted phase {request.phase_number} execution payload",
            stdout_tail="claude_code backend dry-run completed",
            started_at=started_at,
        )
