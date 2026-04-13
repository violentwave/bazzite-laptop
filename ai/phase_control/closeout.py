"""Closeout ingestion automation for phase completion.

P76 — Ingestion Reliability + Continuous Learning Automation

Automates phase-closeout ingestion so repo artifacts, Notion updates, RuFlo memory,
LanceDB documents, task patterns, and related metadata are ingested reliably with
coverage tracking and failure visibility.

Ingestion Targets:
- Repo docs → LanceDB / doc ingestion
- Notion phase row → RuFlo memory
- Phase artifacts → Task patterns (selective, high-signal only)
- HANDOFF.md → Shared context / handoff memory
- Test results → Coverage tracking

Failure Model:
- Bounded exponential backoff retries
- Dead-letter logging for manual review
- Failures visible in logs and closeout reporting
- Does NOT block phase completion on ingestion failure
- Does treat failed ingestion as incomplete closeout state
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from ai.config import APP_NAME, VECTOR_DB_DIR
from ai.phase_control.models import PhaseRow, PhaseStatus

logger = logging.getLogger(APP_NAME)


class IngestionStatus(StrEnum):
    """Status of an ingestion operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class IngestionResult:
    """Result of a single ingestion target operation."""

    target: str  # e.g., "repo_docs", "notion_memory", "task_patterns"
    status: IngestionStatus
    items_processed: int = 0
    items_skipped: int = 0
    error_message: str | None = None
    retry_count: int = 0
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "status": self.status.value,
            "items_processed": self.items_processed,
            "items_skipped": self.items_skipped,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class CoverageMetrics:
    """Coverage metrics for phase closeout."""

    # Metadata coverage
    notion_status_normalized: bool = False
    commit_sha_present: bool = False
    finished_at_present: bool = False
    validation_summary_present: bool = False

    # Artifact coverage
    plan_doc_exists: bool = False
    completion_report_exists: bool = False
    artifact_register_updated: bool = False

    # Ingestion coverage
    repo_docs_ingested: bool = False
    handoff_ingested: bool = False
    phase_summary_in_memory: bool = False
    task_patterns_logged: bool = False

    # Validation coverage
    validation_commands_run: bool = False
    test_outputs_captured: bool = False

    # Failure visibility
    failures_recorded: bool = False
    retry_state_visible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata_coverage": {
                "notion_status_normalized": self.notion_status_normalized,
                "commit_sha_present": self.commit_sha_present,
                "finished_at_present": self.finished_at_present,
                "validation_summary_present": self.validation_summary_present,
            },
            "artifact_coverage": {
                "plan_doc_exists": self.plan_doc_exists,
                "completion_report_exists": self.completion_report_exists,
                "artifact_register_updated": self.artifact_register_updated,
            },
            "ingestion_coverage": {
                "repo_docs_ingested": self.repo_docs_ingested,
                "handoff_ingested": self.handoff_ingested,
                "phase_summary_in_memory": self.phase_summary_in_memory,
                "task_patterns_logged": self.task_patterns_logged,
            },
            "validation_coverage": {
                "validation_commands_run": self.validation_commands_run,
                "test_outputs_captured": self.test_outputs_captured,
            },
            "failure_visibility": {
                "failures_recorded": self.failures_recorded,
                "retry_state_visible": self.retry_state_visible,
            },
        }

    @property
    def coverage_percentage(self) -> float:
        """Calculate overall coverage percentage."""
        all_fields = [
            self.notion_status_normalized,
            self.commit_sha_present,
            self.finished_at_present,
            self.validation_summary_present,
            self.plan_doc_exists,
            self.completion_report_exists,
            self.artifact_register_updated,
            self.repo_docs_ingested,
            self.handoff_ingested,
            self.phase_summary_in_memory,
            self.task_patterns_logged,
            self.validation_commands_run,
            self.test_outputs_captured,
            self.failures_recorded,
            self.retry_state_visible,
        ]
        if not all_fields:
            return 0.0
        return (sum(all_fields) / len(all_fields)) * 100


@dataclass
class CloseoutReport:
    """Complete closeout report for a phase."""

    phase_number: int
    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    ingestion_results: list[IngestionResult] = field(default_factory=list)
    coverage: CoverageMetrics | None = None
    overall_status: IngestionStatus = IngestionStatus.PENDING
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    dead_letter_entries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_number": self.phase_number,
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "ingestion_results": [r.to_dict() for r in self.ingestion_results],
            "coverage": self.coverage.to_dict() if self.coverage else None,
            "overall_status": self.overall_status.value,
            "exceptions": self.exceptions,
            "dead_letter_entries": self.dead_letter_entries,
        }


class IngestionTarget(Protocol):
    """Protocol for ingestion targets."""

    name: str

    def ingest(
        self,
        phase: PhaseRow,
        repo_path: str,
        dry_run: bool = False,
    ) -> IngestionResult:
        """Execute ingestion for this target."""
        ...


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt."""
        delay = self.base_delay_seconds * (self.exponential_base**attempt)
        return min(delay, self.max_delay_seconds)


class CloseoutIngestionEngine:
    """Engine for automated phase closeout ingestion.

    Manages the ingestion workflow including:
    - Retry with exponential backoff
    - Dead-letter logging for persistent failures
    - Coverage tracking
    - Idempotent re-ingestion
    """

    def __init__(
        self,
        repo_path: str,
        retry_config: RetryConfig | None = None,
        dead_letter_path: Path | None = None,
    ):
        self.repo_path = Path(repo_path)
        self.retry_config = retry_config or RetryConfig()
        self.dead_letter_path = dead_letter_path or (
            Path(VECTOR_DB_DIR) / ".closeout-dead-letter.jsonl"
        )
        self._targets: list[IngestionTarget] = []

    def register_target(self, target: IngestionTarget) -> None:
        """Register an ingestion target."""
        self._targets.append(target)

    def run_closeout(
        self,
        phase: PhaseRow,
        run_id: str | None = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> CloseoutReport:
        """Execute full closeout ingestion for a phase.

        Args:
            phase: The phase row to process
            run_id: Optional run ID (generated if not provided)
            dry_run: If True, simulate without persisting
            force: If True, re-ingest even if already processed

        Returns:
            CloseoutReport with all results and coverage metrics
        """
        report = CloseoutReport(
            phase_number=phase.phase_number,
            run_id=run_id or str(uuid4()),
            started_at=datetime.now(UTC),
        )

        logger.info(
            "Starting closeout ingestion for phase %d (run_id=%s, dry_run=%s)",
            phase.phase_number,
            report.run_id,
            dry_run,
        )

        # Execute each target with retry
        for target in self._targets:
            result = self._ingest_with_retry(target, phase, dry_run)
            report.ingestion_results.append(result)

            if result.status == IngestionStatus.FAILED:
                # Write to dead letter
                self._write_dead_letter(report.phase_number, target.name, result)
                report.dead_letter_entries.append(
                    {"target": target.name, "error": result.error_message}
                )

        # Calculate coverage
        report.coverage = self._calculate_coverage(phase, report.ingestion_results)

        # Determine overall status
        statuses = [r.status for r in report.ingestion_results]
        if all(s == IngestionStatus.SUCCESS for s in statuses):
            report.overall_status = IngestionStatus.SUCCESS
        elif any(s == IngestionStatus.FAILED for s in statuses):
            report.overall_status = IngestionStatus.PARTIAL
        else:
            report.overall_status = IngestionStatus.PARTIAL

        report.completed_at = datetime.now(UTC)

        logger.info(
            "Closeout ingestion complete for phase %d: status=%s, coverage=%.1f%%",
            phase.phase_number,
            report.overall_status.value,
            report.coverage.coverage_percentage if report.coverage else 0.0,
        )

        return report

    def _ingest_with_retry(
        self,
        target: IngestionTarget,
        phase: PhaseRow,
        dry_run: bool,
    ) -> IngestionResult:
        """Execute ingestion with bounded retry."""
        last_result: IngestionResult | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            start_time = time.time()

            try:
                result = target.ingest(phase, str(self.repo_path), dry_run)
                result.duration_seconds = time.time() - start_time
                result.retry_count = attempt

                if result.status == IngestionStatus.SUCCESS:
                    logger.info(
                        "Target '%s' succeeded on attempt %d",
                        target.name,
                        attempt,
                    )
                    return result

                # Partial or failed - retry if we have attempts left
                last_result = result
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.calculate_delay(attempt)
                    logger.warning(
                        "Target '%s' %s on attempt %d, retrying in %.1fs: %s",
                        target.name,
                        result.status.value,
                        attempt,
                        delay,
                        result.error_message,
                    )
                    result.status = IngestionStatus.RETRYING
                    time.sleep(delay)

            except Exception as e:
                duration = time.time() - start_time
                last_result = IngestionResult(
                    target=target.name,
                    status=IngestionStatus.FAILED,
                    error_message=str(e),
                    retry_count=attempt,
                    duration_seconds=duration,
                )

                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.calculate_delay(attempt)
                    logger.exception(
                        "Target '%s' exception on attempt %d, retrying in %.1fs",
                        target.name,
                        attempt,
                        delay,
                    )
                    time.sleep(delay)

        # All retries exhausted
        if last_result:
            last_result.status = IngestionStatus.FAILED
            return last_result

        # Should not reach here, but defensive
        return IngestionResult(
            target=target.name,
            status=IngestionStatus.FAILED,
            error_message="All retries exhausted",
        )

    def _write_dead_letter(
        self,
        phase_number: int,
        target: str,
        result: IngestionResult,
    ) -> None:
        """Write failed ingestion to dead letter log."""
        try:
            self.dead_letter_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "phase_number": phase_number,
                "target": target,
                "error": result.error_message,
                "retry_count": result.retry_count,
                "metadata": result.metadata,
            }
            with open(self.dead_letter_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            logger.info(
                "Wrote dead letter entry for phase %d target '%s'",
                phase_number,
                target,
            )
        except Exception as e:
            logger.error("Failed to write dead letter entry: %s", e)

    def _calculate_coverage(
        self,
        phase: PhaseRow,
        results: list[IngestionResult],
    ) -> CoverageMetrics:
        """Calculate coverage metrics for the closeout."""
        coverage = CoverageMetrics()

        # Metadata coverage
        coverage.notion_status_normalized = phase.status == PhaseStatus.DONE
        coverage.commit_sha_present = bool(
            phase.metadata.get("commit_sha") or phase.metadata.get("notion_page_id")
        )
        coverage.finished_at_present = phase.lease_expires_at is not None
        coverage.validation_summary_present = phase.validation_summary is not None

        # Artifact coverage - check for expected files
        plan_doc = self.repo_path / f"docs/P{phase.phase_number:02d}_PLAN.md"
        completion_doc = self.repo_path / f"docs/P{phase.phase_number:02d}_COMPLETION_REPORT.md"
        coverage.plan_doc_exists = plan_doc.exists()
        coverage.completion_report_exists = completion_doc.exists()

        # Check artifact register for this phase
        artifact_register = self.repo_path / "docs/PHASE_ARTIFACT_REGISTER.md"
        if artifact_register.exists():
            content = artifact_register.read_text()
            coverage.artifact_register_updated = f"P{phase.phase_number:02d}" in content

        # Ingestion coverage
        result_map = {r.target: r for r in results}
        coverage.repo_docs_ingested = (
            result_map.get("repo_docs", IngestionResult("", IngestionStatus.PENDING)).status
            == IngestionStatus.SUCCESS
        )
        coverage.handoff_ingested = (
            result_map.get("handoff", IngestionResult("", IngestionStatus.PENDING)).status
            == IngestionStatus.SUCCESS
        )
        coverage.phase_summary_in_memory = (
            result_map.get("notion_memory", IngestionResult("", IngestionStatus.PENDING)).status
            == IngestionStatus.SUCCESS
        )
        coverage.task_patterns_logged = (
            result_map.get("task_patterns", IngestionResult("", IngestionStatus.PENDING)).status
            == IngestionStatus.SUCCESS
        )

        # Validation coverage
        coverage.validation_commands_run = bool(phase.validation_commands)
        coverage.test_outputs_captured = phase.validation_summary is not None

        # Failure visibility
        coverage.failures_recorded = any(r.status == IngestionStatus.FAILED for r in results)
        coverage.retry_state_visible = any(r.retry_count > 0 for r in results)

        return coverage

    def get_dead_letter_entries(
        self,
        since: datetime | None = None,
        phase_number: int | None = None,
    ) -> list[dict[str, Any]]:
        """Read dead letter entries with optional filtering."""
        if not self.dead_letter_path.exists():
            return []

        entries = []
        try:
            with open(self.dead_letter_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"])

                        if since and entry_time < since:
                            continue
                        if phase_number and entry["phase_number"] != phase_number:
                            continue

                        entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            logger.error("Failed to read dead letter: %s", e)

        return entries

    def clear_dead_letter(self, phase_number: int | None = None) -> int:
        """Clear dead letter entries, optionally for a specific phase."""
        if not self.dead_letter_path.exists():
            return 0

        if phase_number is None:
            # Clear all
            count = sum(1 for _ in open(self.dead_letter_path))
            self.dead_letter_path.write_text("")
            return count

        # Clear specific phase - rewrite without those entries
        kept = []
        removed = 0
        try:
            with open(self.dead_letter_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("phase_number") == phase_number:
                            removed += 1
                        else:
                            kept.append(line)
                    except json.JSONDecodeError:
                        kept.append(line)

            self.dead_letter_path.write_text("\n".join(kept) + "\n" if kept else "")
            return removed
        except Exception as e:
            logger.error("Failed to clear dead letter: %s", e)
            return 0
