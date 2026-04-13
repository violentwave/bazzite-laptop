"""Ingestion target implementations for phase closeout.

These are the concrete implementations of IngestionTarget that the
CloseoutIngestionEngine uses to process different types of data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai.config import APP_NAME
from ai.phase_control.closeout import IngestionResult, IngestionStatus
from ai.phase_control.models import PhaseRow

logger = logging.getLogger(APP_NAME)


class RepoDocsIngestionTarget:
    """Ingest phase documentation into LanceDB."""

    name = "repo_docs"

    def ingest(
        self,
        phase: PhaseRow,
        repo_path: str,
        dry_run: bool = False,
    ) -> IngestionResult:
        """Ingest phase docs (P{NN}_PLAN.md, P{NN}_COMPLETION_REPORT.md) into LanceDB."""
        result = IngestionResult(target=self.name, status=IngestionStatus.PENDING)

        try:
            from ai.rag.ingest_docs import ingest_files

            docs_dir = Path(repo_path) / "docs"
            phase_prefix = f"P{phase.phase_number:02d}_"

            # Find phase-specific docs
            doc_files = []
            for pattern in [f"{phase_prefix}*.md"]:
                doc_files.extend(docs_dir.glob(pattern))

            if not doc_files:
                result.status = IngestionStatus.SUCCESS
                result.items_skipped = 0
                result.metadata["note"] = "No phase-specific docs found"
                return result

            if dry_run:
                result.status = IngestionStatus.SUCCESS
                result.items_processed = len(doc_files)
                result.metadata["files"] = [str(f) for f in doc_files]
                result.metadata["note"] = "Dry run - not actually ingested"
                return result

            # Ingest the docs
            ingest_result = ingest_files(doc_files, force=True)

            result.status = IngestionStatus.SUCCESS
            result.items_processed = ingest_result.get("processed", 0)
            result.items_skipped = (
                ingest_result.get("skipped_unchanged", 0)
                + ingest_result.get("skipped_size", 0)
                + ingest_result.get("skipped_deferred", 0)
            )
            result.metadata.update(ingest_result)

        except Exception as e:
            logger.exception("Failed to ingest repo docs for phase %d", phase.phase_number)
            result.status = IngestionStatus.FAILED
            result.error_message = str(e)

        return result


class NotionMemoryIngestionTarget:
    """Ingest phase metadata into RuFlo memory."""

    name = "notion_memory"

    def ingest(
        self,
        phase: PhaseRow,
        repo_path: str,
        dry_run: bool = False,
    ) -> IngestionResult:
        """Store phase summary in RuFlo memory for future retrieval."""
        result = IngestionResult(target=self.name, status=IngestionStatus.PENDING)

        try:
            # Build phase summary for memory
            summary = {
                "phase_number": phase.phase_number,
                "phase_name": phase.phase_name,
                "status": phase.status.value,
                "summary": phase.summary,
                "backend": phase.backend,
                "validation_summary": phase.validation_summary,
            }

            if dry_run:
                result.status = IngestionStatus.SUCCESS
                result.items_processed = 1
                result.metadata["summary_keys"] = list(summary.keys())
                result.metadata["note"] = "Dry run - not actually stored"
                return result

            # Try to store in RuFlo memory via MCP
            try:
                import subprocess

                namespace = "phase_closeout"
                key = f"phase_{phase.phase_number:02d}"
                value = json.dumps(summary, default=str)

                # Use ruflo_memory_store MCP tool via CLI
                # This is a static command with no user input - safe to run
                cmd = [
                    "ruflo",
                    "memory",
                    "store",
                    "--namespace",
                    namespace,
                    "--key",
                    key,
                    "--value",
                    value,
                ]

                proc = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if proc.returncode == 0:
                    result.status = IngestionStatus.SUCCESS
                    result.items_processed = 1
                    result.metadata["stored_key"] = key
                    result.metadata["namespace"] = namespace
                else:
                    # RuFlo might not be available, log but don't fail
                    logger.warning(
                        "RuFlo memory store returned %d: %s",
                        proc.returncode,
                        proc.stderr,
                    )
                    result.status = IngestionStatus.SUCCESS  # Graceful degradation
                    result.items_skipped = 1
                    result.metadata["note"] = "RuFlo not available, skipped gracefully"

            except FileNotFoundError:
                # ruflo CLI not available
                logger.info("RuFlo CLI not available, skipping memory ingestion")
                result.status = IngestionStatus.SUCCESS  # Graceful degradation
                result.items_skipped = 1
                result.metadata["note"] = "RuFlo CLI not available"

            except Exception as e:
                logger.warning("RuFlo memory ingestion failed: %s", e)
                result.status = IngestionStatus.SUCCESS  # Graceful degradation
                result.items_skipped = 1
                result.metadata["note"] = f"RuFlo error: {e}"

        except Exception as e:
            logger.exception("Failed to prepare notion memory for phase %d", phase.phase_number)
            result.status = IngestionStatus.FAILED
            result.error_message = str(e)

        return result


class TaskPatternIngestionTarget:
    """Log high-signal task patterns from phase execution."""

    name = "task_patterns"

    def ingest(
        self,
        phase: PhaseRow,
        repo_path: str,
        dry_run: bool = False,
    ) -> IngestionResult:
        """Log task pattern for successful phase completion."""
        result = IngestionResult(target=self.name, status=IngestionStatus.PENDING)

        try:
            # Only log for successful phases
            if phase.status.value not in ("Done", "Done"):
                result.status = IngestionStatus.SUCCESS
                result.items_skipped = 1
                result.metadata["note"] = (
                    f"Phase status is {phase.status.value}, not logging pattern"
                )
                return result

            # Build task pattern from phase
            description = f"Phase {phase.phase_number}: {phase.phase_name}"
            approach = phase.execution_prompt[:500] if phase.execution_prompt else "Phase execution"
            outcome = phase.summary[:500] if phase.summary else "Completed successfully"

            if dry_run:
                result.status = IngestionStatus.SUCCESS
                result.items_processed = 1
                result.metadata["description"] = description
                result.metadata["approach_preview"] = approach[:100]
                result.metadata["note"] = "Dry run - not actually logged"
                return result

            # Try to log to LanceDB task_patterns
            try:
                from ai.learning.task_logger import TaskLogger

                logger_instance = TaskLogger()

                # Extract tools used from phase
                tools_used = []
                if phase.allowed_tools:
                    tools_used = phase.allowed_tools

                # Count tests from validation summary
                tests_added = 0
                if phase.validation_summary:
                    val_sum = phase.validation_summary
                    if isinstance(val_sum, dict):
                        # Try to extract test count
                        commands = val_sum.get("commands", [])
                        for cmd in commands:
                            if isinstance(cmd, dict) and "pytest" in str(cmd.get("command", "")):
                                tests_added += 1

                pattern_id = logger_instance.log_success(
                    description=description,
                    approach=approach,
                    outcome=outcome,
                    tools_used=tools_used,
                    tests_added=tests_added,
                    phase=f"P{phase.phase_number:02d}",
                    agent="phase-control",
                )

                result.status = IngestionStatus.SUCCESS
                result.items_processed = 1
                result.metadata["pattern_id"] = pattern_id

            except Exception as e:
                logger.warning("Task pattern logging failed: %s", e)
                result.status = IngestionStatus.SUCCESS  # Graceful degradation
                result.items_skipped = 1
                result.metadata["note"] = f"Task logger error: {e}"

        except Exception as e:
            logger.exception("Failed to log task pattern for phase %d", phase.phase_number)
            result.status = IngestionStatus.FAILED
            result.error_message = str(e)

        return result


class HandoffIngestionTarget:
    """Ingest HANDOFF.md into shared context."""

    name = "handoff"

    def ingest(
        self,
        phase: PhaseRow,
        repo_path: str,
        dry_run: bool = False,
    ) -> IngestionResult:
        """Parse and ingest HANDOFF.md entries into shared context."""
        result = IngestionResult(target=self.name, status=IngestionStatus.PENDING)

        try:
            handoff_path = Path(repo_path) / "HANDOFF.md"
            if not handoff_path.exists():
                result.status = IngestionStatus.SUCCESS
                result.items_skipped = 0
                result.metadata["note"] = "No HANDOFF.md found"
                return result

            # Parse handoff
            from ai.learning.handoff_parser import parse_handoff

            entries = parse_handoff(handoff_path)

            if not entries:
                result.status = IngestionStatus.SUCCESS
                result.items_skipped = 0
                result.metadata["note"] = "No entries found in HANDOFF.md"
                return result

            # Filter to entries related to this phase
            phase_entries = []
            for entry in entries:
                # Check if this entry mentions the phase
                search_text = f"{entry.summary} {' '.join(entry.done_tasks)}"
                if (
                    f"P{phase.phase_number}" in search_text
                    or f"Phase {phase.phase_number}" in search_text
                ):
                    phase_entries.append(entry)

            if not phase_entries:
                # If no specific phase mention, take the most recent entry as fallback
                phase_entries = [entries[0]]

            if dry_run:
                result.status = IngestionStatus.SUCCESS
                result.items_processed = len(phase_entries)
                result.metadata["entries_found"] = len(entries)
                result.metadata["phase_entries"] = len(phase_entries)
                result.metadata["note"] = "Dry run - not actually ingested"
                return result

            # Store in shared context
            try:
                from ai.collab.shared_context import get_shared_context

                shared = get_shared_context()

                for entry in phase_entries:
                    content = f"""
Phase {phase.phase_number} Handoff
Agent: {entry.agent}
Timestamp: {entry.timestamp}
Summary: {entry.summary}

Completed Tasks:
{chr(10).join(f"- {task}" for task in entry.done_tasks)}

Open Tasks:
{chr(10).join(f"- {task}" for task in entry.open_tasks)}
""".strip()

                    shared.add_context(
                        context_type="handoff",
                        content=content,
                        agent=entry.agent,
                        files=[],
                        priority=3,
                        ttl_hours=720,  # 30 days
                    )

                result.status = IngestionStatus.SUCCESS
                result.items_processed = len(phase_entries)

            except Exception as e:
                logger.warning("Shared context ingestion failed: %s", e)
                result.status = IngestionStatus.SUCCESS  # Graceful degradation
                result.items_skipped = len(phase_entries)
                result.metadata["note"] = f"Shared context error: {e}"

        except Exception as e:
            logger.exception("Failed to ingest handoff for phase %d", phase.phase_number)
            result.status = IngestionStatus.FAILED
            result.error_message = str(e)

        return result


class ValidationCoverageIngestionTarget:
    """Capture validation/test results into coverage tracking."""

    name = "validation_coverage"

    def ingest(
        self,
        phase: PhaseRow,
        repo_path: str,
        dry_run: bool = False,
    ) -> IngestionResult:
        """Record validation coverage metrics."""
        result = IngestionResult(target=self.name, status=IngestionStatus.PENDING)

        try:
            validation_summary = phase.validation_summary or {}

            coverage_data = {
                "phase_number": phase.phase_number,
                "validation_commands": phase.validation_commands,
                "validation_summary": validation_summary,
                "has_validation_summary": validation_summary is not None,
                "command_count": len(phase.validation_commands),
            }

            if dry_run:
                result.status = IngestionStatus.SUCCESS
                result.items_processed = 1
                result.metadata.update(coverage_data)
                result.metadata["note"] = "Dry run - not actually recorded"
                return result

            # Store in shared context as coverage record
            try:
                from ai.collab.shared_context import get_shared_context

                shared = get_shared_context()

                content = json.dumps(coverage_data, indent=2, default=str)
                shared.add_context(
                    context_type="coverage",
                    content=content,
                    agent="phase-control",
                    files=[],
                    priority=2,
                    ttl_hours=2160,  # 90 days
                )

                result.status = IngestionStatus.SUCCESS
                result.items_processed = 1

            except Exception as e:
                logger.warning("Validation coverage recording failed: %s", e)
                result.status = IngestionStatus.SUCCESS  # Graceful degradation
                result.items_skipped = 1
                result.metadata["note"] = f"Coverage recording error: {e}"

        except Exception as e:
            logger.exception(
                "Failed to record validation coverage for phase %d", phase.phase_number
            )
            result.status = IngestionStatus.FAILED
            result.error_message = str(e)

        return result
