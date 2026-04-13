"""Runner tests for P55 control-plane flow."""

from subprocess import TimeoutExpired
from unittest.mock import patch

from ai.phase_control.models import PhaseRow, PhaseStatus
from ai.phase_control.notion_sync import InMemoryPhaseSync
from ai.phase_control.result_models import BackendResult, BackendStatus, PreflightRecord
from ai.phase_control.runner import PhaseControlRunner, RunnerConfig


class _BackendSuccess:
    backend_name = "codex"

    def run(self, request):
        assert request.preflight_record is None or isinstance(request.preflight_record, dict)
        return BackendResult(
            backend="codex",
            run_id=request.run_id,
            status=BackendStatus.SUCCESS,
            summary="ok",
            stdout_tail="",
            stderr_tail="",
            artifacts=[],
            suggested_commit_sha=None,
            validation_summary={},
            policy_events=[],
            started_at=BackendResult.now(),
            finished_at=BackendResult.now(),
            exit_code=0,
        )


class _BackendFail:
    backend_name = "codex"

    def run(self, request):
        return BackendResult(
            backend="codex",
            run_id=request.run_id,
            status=BackendStatus.FAILED,
            summary="backend failed",
            stdout_tail="",
            stderr_tail="x",
            artifacts=[],
            suggested_commit_sha=None,
            validation_summary={},
            policy_events=[],
            started_at=BackendResult.now(),
            finished_at=BackendResult.now(),
            exit_code=1,
        )


class _BackendCapture:
    backend_name = "codex"

    def __init__(self):
        self.last_request = None

    def run(self, request):
        self.last_request = request
        return BackendResult(
            backend="codex",
            run_id=request.run_id,
            status=BackendStatus.SUCCESS,
            summary="ok",
            stdout_tail="",
            stderr_tail="",
            artifacts=[],
            suggested_commit_sha=None,
            validation_summary={},
            policy_events=[],
            started_at=BackendResult.now(),
            finished_at=BackendResult.now(),
            exit_code=0,
        )


def _phase(status: PhaseStatus = PhaseStatus.READY, approval_required: bool = False) -> PhaseRow:
    return PhaseRow(
        phase_name="P55",
        phase_number=55,
        status=status,
        execution_prompt="implement",
        validation_commands=["python -V"],
        done_criteria=["tests pass"],
        backend="codex",
        approval_required=approval_required,
        approval_granted=not approval_required,
        slack_channel="C1",
        slack_thread_ts="1.1",
    )


def _preflight(allowed: bool = True) -> PreflightRecord:
    gate = {
        "allowed": allowed,
        "severity": "ok" if allowed else "block",
        "blockers": [] if allowed else ["missing_code_context"],
        "warnings": [],
        "source_errors": [],
    }
    return PreflightRecord(
        schema_version="p75.v1",
        generated_at=BackendResult.now().isoformat(),
        phase_context={"phase_number": 55},
        artifact_context={"phase_docs": ["docs/P74_PLAN.md"]},
        code_context={"fused": {"results": [{"relative_path": "ai/router.py"}]}},
        pattern_context={"task_patterns": []},
        health_signals={"timers": {"status": "healthy"}, "pipeline": {"status": "healthy"}},
        gate=gate,
        summary=f"preflight allowed={allowed}",
        source_errors=[],
    )


def test_runner_selects_backend():
    sync = InMemoryPhaseSync([_phase()])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendSuccess()},
    )
    selected = runner.select_backend(sync.get_phase(55))
    assert isinstance(selected, _BackendSuccess)


def test_runner_approval_gate_blocks_start():
    sync = InMemoryPhaseSync([_phase(approval_required=True)])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendSuccess()},
    )
    result = runner.run_once()
    assert result["status"] == "awaiting_approval"


def test_runner_failure_to_blocked_behavior():
    sync = InMemoryPhaseSync([_phase()])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendFail()},
    )
    with patch.object(runner, "_run_validations", return_value=_validation(True)):
        runner.run_once()

    updated = sync.get_phase(55)
    assert updated.status == PhaseStatus.BLOCKED
    assert updated.blocker == "backend failed"
    assert updated.lease_expires_at is None


def test_runner_backend_exception_releases_lease_and_blocks():
    class _BackendExplode:
        backend_name = "codex"

        def run(self, request):
            raise RuntimeError("boom")

    sync = InMemoryPhaseSync([_phase()])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendExplode()},
    )

    runner.run_once()
    updated = sync.get_phase(55)
    assert updated.status == PhaseStatus.BLOCKED
    assert "boom" in (updated.blocker or "")
    assert updated.lease_expires_at is None


def test_runner_validation_timeout_maps_to_blocked():
    sync = InMemoryPhaseSync([_phase()])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendSuccess()},
    )

    with patch(
        "subprocess.run",
        side_effect=TimeoutExpired(cmd=["python", "-V"], timeout=300, stderr="timed out"),
    ):
        runner.run_once()

    updated = sync.get_phase(55)
    assert updated.status == PhaseStatus.BLOCKED
    assert updated.validation_summary is not None
    assert updated.validation_summary["passed"] is False


def test_runner_resume_and_cancel_handling():
    sync = InMemoryPhaseSync([_phase(status=PhaseStatus.BLOCKED)])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendSuccess()},
    )

    resumed = runner.handle_slack_event(
        phase_number=55,
        channel="C1",
        thread_ts="1.1",
        text="resume continue",
    )
    assert resumed["status"] == "applied"
    assert sync.get_phase(55).status == PhaseStatus.READY

    sync.update_phase(_phase(status=PhaseStatus.IN_PROGRESS))
    cancelled = runner.handle_slack_event(
        phase_number=55,
        channel="C1",
        thread_ts="1.1",
        text="cancel stopping now",
    )
    assert cancelled["status"] == "applied"
    assert sync.get_phase(55).status == PhaseStatus.CANCELLED


def test_runner_preflight_block_prevents_backend_execution():
    class _BackendNever:
        backend_name = "codex"

        def run(self, request):  # pragma: no cover - should not run
            raise AssertionError("backend should not execute when preflight is blocked")

    sync = InMemoryPhaseSync([_phase()])
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": _BackendNever()},
    )

    with patch("ai.phase_control.runner.build_preflight_record", return_value=_preflight(False)):
        result = runner.run_once()

    updated = sync.get_phase(55)
    assert result["status"] == "preflight_blocked"
    assert updated.status == PhaseStatus.READY
    assert "preflight" in (updated.validation_summary or {})


def test_runner_build_request_includes_preflight_context():
    sync = InMemoryPhaseSync([_phase()])
    backend = _BackendCapture()
    runner = PhaseControlRunner(
        sync_backend=sync,
        config=RunnerConfig(repo_path="/tmp"),
        backends={"codex": backend},
    )

    with (
        patch("ai.phase_control.runner.build_preflight_record", return_value=_preflight(True)),
        patch.object(runner, "_run_validations", return_value=_validation(True)),
    ):
        runner.run_once()

    assert backend.last_request is not None
    assert "[Preflight Context]" in backend.last_request.execution_prompt
    assert backend.last_request.preflight_summary.startswith("preflight")


def _validation(passed: bool):
    from ai.phase_control.result_models import ValidationSummary

    return ValidationSummary(passed=passed, commands=[])
