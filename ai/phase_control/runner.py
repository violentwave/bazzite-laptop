"""Phase-control runner that coordinates policy, lease, backend, and validation."""

from __future__ import annotations

import logging
import shlex
import socket
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from subprocess import TimeoutExpired
from typing import Any
from uuid import uuid4

from ai.phase_control.backends import ClaudeCodeBackend, CodexBackend, OpenCodeBackend
from ai.phase_control.closeout import (
    CloseoutIngestionEngine,
    RetryConfig,
)
from ai.phase_control.closeout_targets import (
    HandoffIngestionTarget,
    NotionMemoryIngestionTarget,
    RepoDocsIngestionTarget,
    TaskPatternIngestionTarget,
    ValidationCoverageIngestionTarget,
)
from ai.phase_control.models import PhaseRow, PhaseStatus
from ai.phase_control.notion_sync import InMemoryPhaseSync, PhaseSyncBackend
from ai.phase_control.policy import (
    check_approval,
    check_done_validation,
    check_preflight_gate,
    check_ready_requirements,
)
from ai.phase_control.preflight import build_preflight_record
from ai.phase_control.result_models import (
    BackendRequest,
    BackendResult,
    BackendStatus,
    ValidationCommandResult,
    ValidationSummary,
)
from ai.phase_control.slack_commands import SlackCommandType, parse_slack_command
from ai.phase_control.state_machine import TransitionError, transition_phase

SlackPoster = Callable[[str, str, str | None], str | None]

logger = logging.getLogger("ai.phase_control.runner")


@dataclass
class RunnerConfig:
    """Runner configuration."""

    repo_path: str
    lease_seconds: int = 900
    runner_host: str = socket.gethostname()


class PhaseControlRunner:
    """Main control-plane runner for autonomous phase execution."""

    def __init__(
        self,
        *,
        sync_backend: PhaseSyncBackend | None = None,
        backends: dict[str, Any] | None = None,
        config: RunnerConfig,
        slack_poster: SlackPoster | None = None,
        enable_closeout: bool = True,
    ):
        self.sync_backend = sync_backend or InMemoryPhaseSync()
        self.config = config
        self.slack_poster = slack_poster
        self.backends = backends or {
            "codex": CodexBackend(),
            "opencode": OpenCodeBackend(),
            "claude_code": ClaudeCodeBackend(),
        }
        self.enable_closeout = enable_closeout
        self._closeout_engine: CloseoutIngestionEngine | None = None

    def _get_closeout_engine(self) -> CloseoutIngestionEngine:
        """Get or create the closeout ingestion engine with all targets registered."""
        if self._closeout_engine is None:
            engine = CloseoutIngestionEngine(
                repo_path=self.config.repo_path,
                retry_config=RetryConfig(max_retries=3, base_delay_seconds=1.0),
            )
            # Register all ingestion targets (P76)
            engine.register_target(RepoDocsIngestionTarget())
            engine.register_target(NotionMemoryIngestionTarget())
            engine.register_target(TaskPatternIngestionTarget())
            engine.register_target(HandoffIngestionTarget())
            engine.register_target(ValidationCoverageIngestionTarget())
            self._closeout_engine = engine
        return self._closeout_engine

    def select_backend(self, phase: PhaseRow):
        """Select backend adapter by phase backend field."""
        backend = self.backends.get(phase.backend)
        if backend is None:
            raise ValueError(f"unknown backend '{phase.backend}'")
        return backend

    def _build_request(self, phase: PhaseRow, run_id: str) -> BackendRequest:
        """Build normalized request for adapter execution."""
        artifacts_dir = phase.artifacts_dir or str(
            Path(self.config.repo_path) / "artifacts" / "phase-control" / run_id
        )
        preflight_summary = str(phase.metadata.get("preflight_summary", "") or "")
        execution_prompt = phase.execution_prompt
        if preflight_summary:
            execution_prompt = (
                "[Preflight Context]\n"
                f"{preflight_summary}\n\n"
                "[Execution Prompt]\n"
                f"{phase.execution_prompt}"
            )
        return BackendRequest(
            run_id=run_id,
            phase_name=phase.phase_name,
            phase_number=phase.phase_number,
            repo_path=self.config.repo_path,
            branch_name=phase.branch_name,
            execution_prompt=execution_prompt,
            allowed_tools=phase.allowed_tools,
            validation_commands=phase.validation_commands,
            execution_mode=phase.execution_mode,
            risk_tier=phase.risk_tier,
            approval_required=phase.approval_required,
            timeout_seconds=phase.timeout_seconds,
            env_allowlist=phase.env_allowlist,
            artifacts_dir=artifacts_dir,
            preflight_summary=preflight_summary,
            preflight_record=phase.metadata.get("preflight_record"),
        )

    def _run_validations(self, commands: list[str]) -> ValidationSummary:
        """Run validation commands with static argv execution (no shell)."""
        results: list[ValidationCommandResult] = []
        for command in commands:
            argv = shlex.split(command)
            if not argv:
                results.append(
                    ValidationCommandResult(
                        command=command,
                        passed=False,
                        exit_code=2,
                        stderr_tail="empty validation command",
                    )
                )
                continue

            try:
                completed = subprocess.run(  # noqa: S603
                    argv,
                    cwd=self.config.repo_path,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results.append(
                    ValidationCommandResult(
                        command=command,
                        passed=completed.returncode == 0,
                        exit_code=completed.returncode,
                        stdout_tail=completed.stdout[-2000:],
                        stderr_tail=completed.stderr[-2000:],
                    )
                )
            except TimeoutExpired as exc:
                results.append(
                    ValidationCommandResult(
                        command=command,
                        passed=False,
                        exit_code=124,
                        stdout_tail=(exc.stdout or "")[-2000:]
                        if isinstance(exc.stdout, str)
                        else "",
                        stderr_tail=(exc.stderr or "validation timeout")[-2000:]
                        if isinstance(exc.stderr, str)
                        else "validation timeout",
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive
                results.append(
                    ValidationCommandResult(
                        command=command,
                        passed=False,
                        exit_code=1,
                        stderr_tail=str(exc),
                    )
                )

        return ValidationSummary(
            passed=all(result.passed for result in results),
            commands=results,
        )

    def run_once(self) -> dict[str, Any]:
        """Run one control-plane tick against the next eligible phase."""
        phase = self.sync_backend.get_next_ready_phase()
        if phase is None:
            return {"status": "idle"}

        ready = check_ready_requirements(phase)
        if not ready.allowed:
            return {
                "status": "policy_violation",
                "phase": phase.phase_number,
                "events": [{"code": e.code, "message": e.message} for e in ready.events],
            }

        approval = check_approval(phase)
        if not approval.allowed:
            return {
                "status": "awaiting_approval",
                "phase": phase.phase_number,
                "events": [{"code": e.code, "message": e.message} for e in approval.events],
            }

        run_id = str(uuid4())
        lease_ok = self.sync_backend.claim_lease(
            phase.phase_number,
            run_id=run_id,
            runner_host=self.config.runner_host,
            lease_seconds=self.config.lease_seconds,
            slack_channel=phase.slack_channel,
            slack_thread_ts=phase.slack_thread_ts,
        )
        if not lease_ok:
            return {"status": "lease_conflict", "phase": phase.phase_number}

        lease_claimed = True
        phase = self.sync_backend.get_phase(phase.phase_number) or phase
        validation_summary = ValidationSummary(passed=False, commands=[])
        response_status = "processed"

        try:
            preflight = build_preflight_record(phase, repo_path=self.config.repo_path)
            preflight_dict = preflight.to_dict()
            phase.metadata["preflight_record"] = preflight_dict
            phase.metadata["preflight_summary"] = preflight.summary

            preflight_gate = check_preflight_gate(preflight_dict)
            if not preflight_gate.allowed:
                blocker = (
                    "; ".join(event.message for event in preflight_gate.events)
                    or "preflight blocked"
                )
                phase.blocker = blocker
                phase.validation_summary = {"preflight": preflight_dict}
                phase.summary = preflight.summary
                self.sync_backend.update_phase(phase)
                response_status = "preflight_blocked"
                return {
                    "status": response_status,
                    "phase": phase.phase_number,
                    "run_id": run_id,
                    "phase_status": phase.status,
                    "events": [
                        {"code": event.code, "message": event.message}
                        for event in preflight_gate.events
                    ],
                }

            transition_phase(
                phase,
                PhaseStatus.IN_PROGRESS,
                lease_acquired=True,
                approval_satisfied=approval.allowed,
            )
            self.sync_backend.update_phase(phase)

            if self.slack_poster and phase.slack_channel:
                thread_ts = self.slack_poster(
                    phase.slack_channel,
                    f"Starting phase {phase.phase_number}: {phase.phase_name} (run {run_id})",
                    phase.slack_thread_ts,
                )
                if thread_ts and not phase.slack_thread_ts:
                    phase.slack_thread_ts = thread_ts
                    self.sync_backend.update_phase(phase)

            request = self._build_request(phase, run_id)
            backend = self.select_backend(phase)
            try:
                result: BackendResult = backend.run(request)
            except Exception as exc:
                result = BackendResult(
                    backend=getattr(backend, "backend_name", phase.backend),
                    run_id=run_id,
                    status=BackendStatus.FAILED,
                    summary=f"backend exception: {exc}",
                    stdout_tail="",
                    stderr_tail=str(exc),
                    artifacts=[],
                    validation_summary={},
                    policy_events=[],
                    started_at=BackendResult.now(),
                    finished_at=BackendResult.now(),
                    exit_code=1,
                )

            validation_summary = self._run_validations(phase.validation_commands)
            phase.validation_summary = validation_summary.to_dict()
            preflight_summary = str(phase.metadata.get("preflight_summary", "") or "")
            phase.summary = (
                f"{preflight_summary}\nBackend: {result.summary}"
                if preflight_summary
                else result.summary
            )

            if result.status == BackendStatus.SUCCESS:
                done_gate = check_done_validation(validation_summary)
                if done_gate.allowed:
                    transition_phase(phase, PhaseStatus.DONE, validation_passed=True)
                    # P76: Run closeout ingestion after successful phase completion
                    if self.enable_closeout and phase.status == PhaseStatus.DONE:
                        try:
                            closeout_report = self._run_closeout_ingestion(phase, run_id)
                            # Store closeout report in metadata for visibility
                            phase.metadata["closeout_report"] = closeout_report.to_dict()
                        except Exception as closeout_exc:
                            # Do not fail phase completion due to ingestion issues
                            logger.warning(
                                "Closeout ingestion failed for phase %d: %s",
                                phase.phase_number,
                                closeout_exc,
                            )
                            phase.metadata["closeout_error"] = str(closeout_exc)
                else:
                    transition_phase(
                        phase,
                        PhaseStatus.BLOCKED,
                        blocker="validation failed after backend success",
                        validation_summary=validation_summary.to_dict(),
                    )
            elif result.status == BackendStatus.NEEDS_REVIEW:
                transition_phase(phase, PhaseStatus.NEEDS_REVIEW)
            elif result.status in {BackendStatus.BLOCKED, BackendStatus.FAILED}:
                transition_phase(
                    phase,
                    PhaseStatus.BLOCKED,
                    blocker=result.summary or "backend reported failure",
                    validation_summary=validation_summary.to_dict(),
                )
            else:
                transition_phase(
                    phase,
                    PhaseStatus.CANCELLED,
                    reason_text=result.summary or "backend cancelled execution",
                )
        except Exception as exc:
            response_status = "failed"
            phase.validation_summary = validation_summary.to_dict()
            phase.summary = str(exc)
            if phase.status == PhaseStatus.IN_PROGRESS:
                try:
                    transition_phase(
                        phase,
                        PhaseStatus.BLOCKED,
                        blocker=f"runner exception: {exc}",
                        validation_summary=validation_summary.to_dict(),
                    )
                except TransitionError:
                    pass
        finally:
            if lease_claimed:
                self.sync_backend.release_lease(phase.phase_number, run_id=run_id)
            phase.run_id = run_id
            self.sync_backend.update_phase(phase)

        return {
            "status": response_status,
            "phase": phase.phase_number,
            "run_id": run_id,
            "phase_status": phase.status,
        }

    def _run_closeout_ingestion(
        self,
        phase: PhaseRow,
        run_id: str,
        dry_run: bool = False,
    ) -> Any:  # Returns CloseoutReport
        """Run P76 closeout ingestion for a completed phase.

        This method is called automatically when a phase transitions to DONE.
        It orchestrates ingestion of repo docs, Notion memory, task patterns,
        handoff summaries, and validation coverage.

        Args:
            phase: The completed phase row
            run_id: The execution run ID
            dry_run: If True, simulate without persisting

        Returns:
            CloseoutReport with ingestion results and coverage metrics
        """
        logger.info(
            "Running closeout ingestion for phase %d (run_id=%s)",
            phase.phase_number,
            run_id,
        )

        engine = self._get_closeout_engine()
        report = engine.run_closeout(phase, run_id=run_id, dry_run=dry_run)

        # Log summary
        if report.overall_status.value == "success":
            logger.info(
                "Closeout complete for phase %d: all targets succeeded",
                phase.phase_number,
            )
        elif report.overall_status.value == "partial":
            failed = [r.target for r in report.ingestion_results if r.status.value == "failed"]
            logger.warning(
                "Closeout partial for phase %d: failed targets: %s",
                phase.phase_number,
                failed,
            )
        else:
            logger.error(
                "Closeout failed for phase %d",
                phase.phase_number,
            )

        # Notify on Slack if configured
        if self.slack_poster and phase.slack_channel:
            coverage_pct = report.coverage.coverage_percentage if report.coverage else 0.0
            status_emoji = "✅" if report.overall_status.value == "success" else "⚠️"
            message = (
                f"{status_emoji} Phase {phase.phase_number} closeout complete. "
                f"Coverage: {coverage_pct:.0f}%"
            )
            if report.dead_letter_entries:
                message += f" | {len(report.dead_letter_entries)} items in dead letter"
            self.slack_poster(
                phase.slack_channel,
                message,
                phase.slack_thread_ts,
            )

        return report

    def run_closeout_manually(
        self,
        phase_number: int,
        dry_run: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Manually trigger closeout ingestion for a phase (recovery/retry).

        Args:
            phase_number: The phase to run closeout for
            dry_run: If True, simulate without persisting
            force: If True, re-ingest even if already processed

        Returns:
            Dict with closeout report or error
        """
        phase = self.sync_backend.get_phase(phase_number)
        if phase is None:
            return {"status": "error", "message": f"Phase {phase_number} not found"}

        run_id = str(uuid4())
        try:
            report = self._run_closeout_ingestion(phase, run_id, dry_run=dry_run)
            # Update phase with new closeout report
            if not dry_run:
                phase.metadata["closeout_report"] = report.to_dict()
                phase.metadata["closeout_rerun"] = {
                    "run_id": run_id,
                    "forced": force,
                    "timestamp": BackendResult.now(),
                }
                self.sync_backend.update_phase(phase)

            return {
                "status": "success",
                "phase": phase_number,
                "run_id": run_id,
                "overall_status": report.overall_status.value,
                "coverage_percentage": report.coverage.coverage_percentage
                if report.coverage
                else 0.0,
                "report": report.to_dict(),
            }
        except Exception as e:
            logger.exception("Manual closeout failed for phase %d", phase_number)
            return {"status": "error", "phase": phase_number, "message": str(e)}

    def handle_slack_event(
        self,
        *,
        phase_number: int,
        channel: str,
        thread_ts: str | None,
        text: str,
    ) -> dict[str, Any]:
        """Apply a parsed Slack thread command to a phase row."""
        phase = self.sync_backend.get_phase(phase_number)
        if phase is None:
            return {"status": "missing_phase"}

        parsed = parse_slack_command(
            text,
            channel=channel,
            thread_ts=thread_ts,
            expected_channel=phase.slack_channel,
            expected_thread_ts=phase.slack_thread_ts,
        )
        if parsed is None:
            return {"status": "ignored"}

        if parsed.command == SlackCommandType.APPROVE:
            phase.approval_granted = True
        elif parsed.command == SlackCommandType.REJECT:
            phase.approval_granted = False
            if phase.status == PhaseStatus.IN_PROGRESS:
                transition_phase(
                    phase,
                    PhaseStatus.BLOCKED,
                    blocker=parsed.reason_text or "rejected via slack",
                    validation_summary=phase.validation_summary or {},
                )
        elif parsed.command == SlackCommandType.HOLD:
            if phase.status == PhaseStatus.IN_PROGRESS:
                transition_phase(
                    phase,
                    PhaseStatus.BLOCKED,
                    blocker=parsed.reason_text or "held via slack",
                    validation_summary=phase.validation_summary or {},
                )
        elif parsed.command == SlackCommandType.RESUME:
            if phase.status in {PhaseStatus.BLOCKED, PhaseStatus.NEEDS_REVIEW}:
                transition_phase(phase, PhaseStatus.READY)
        elif parsed.command == SlackCommandType.CANCEL:
            if phase.status in {PhaseStatus.READY, PhaseStatus.IN_PROGRESS}:
                transition_phase(
                    phase,
                    PhaseStatus.CANCELLED,
                    reason_text=parsed.reason_text or "cancelled via slack",
                )

        self.sync_backend.update_phase(phase)
        return {"status": "applied", "command": parsed.command, "phase_status": phase.status}
