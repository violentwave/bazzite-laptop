"""Backend normalization tests for P55 adapters."""

from ai.phase_control.backends import ClaudeCodeBackend, CodexBackend, OpenCodeBackend
from ai.phase_control.result_models import BackendRequest, BackendStatus


def _request() -> BackendRequest:
    return BackendRequest(
        run_id="run-1",
        phase_name="P55",
        phase_number=55,
        repo_path="/tmp/repo",
        branch_name=None,
        execution_prompt="Implement feature",
        allowed_tools=["bash"],
        validation_commands=["python -V"],
        execution_mode="safe",
        risk_tier="medium",
        approval_required=True,
        timeout_seconds=1200,
        env_allowlist=[],
        artifacts_dir="/tmp/artifacts",
    )


def test_codex_backend_returns_normalized_result():
    result = CodexBackend().run(_request())
    assert result.backend == "codex"
    assert result.run_id == "run-1"
    assert result.status == BackendStatus.SUCCESS
    assert isinstance(result.artifacts, list)


def test_opencode_backend_returns_normalized_result():
    result = OpenCodeBackend().run(_request())
    assert result.backend == "opencode"
    assert result.status == BackendStatus.SUCCESS
    assert result.exit_code == 0


def test_claude_backend_empty_prompt_fails():
    req = _request()
    req.execution_prompt = ""
    result = ClaudeCodeBackend().run(req)
    assert result.backend == "claude_code"
    assert result.status == BackendStatus.FAILED
    assert result.exit_code != 0
