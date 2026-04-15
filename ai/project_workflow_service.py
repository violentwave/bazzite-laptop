"""Project and workflow aggregation service for P86/P93.

Repaired in P93 to derive current phase from HANDOFF truth with Notion parity,
eliminating stale phase badges and placeholder project state. Falls back to local
HANDOFF truth when Notion is unavailable and clearly marks sync degradation.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path.home() / "projects" / "bazzite-laptop"))
WORKFLOW_DB_PATH = Path.home() / "security" / "vector-db" / "workflow_runs.lance"


class NotionSyncStatus:
    """Tracks Notion sync state for the UI."""

    SYNCED = "synced"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


@dataclass
class PhaseInfo:
    """Current phase information."""

    phase_number: int
    phase_name: str
    status: str
    dependencies: list[int]
    blockers: list[str]
    readiness: str
    next_action: str
    execution_mode: str
    risk_tier: str
    backend: str
    notion_status: str | None = None


@dataclass
class WorkflowRun:
    """Workflow run summary."""

    run_id: str
    workflow_name: str
    status: str
    started_at: str
    completed_at: str | None
    triggered_by: str
    step_count: int
    current_step: int | None
    error_message: str | None


@dataclass
class ArtifactInfo:
    """Artifact/evidence summary."""

    name: str
    type: str
    path: str
    size_bytes: int
    created_at: str
    source_phase: str | None
    metadata: dict[str, Any]


@dataclass
class PreflightSummary:
    """Preflight intelligence summary."""

    schema_version: str
    generated_at: str
    gate_status: str
    gate_reason: str
    code_files_count: int
    impact_score: float | None
    health_status: str
    health_issues: list[str]


@dataclass
class ProjectContext:
    """Complete project context for UI."""

    current_phase: PhaseInfo | None
    latest_completed_phase: PhaseInfo | None
    recent_workflows: list[WorkflowRun]
    artifacts: list[ArtifactInfo]
    preflight: PreflightSummary | None
    handoff_summary: dict[str, Any]
    recommendations: list[str]
    notion_sync_status: str
    notion_sync_message: str


class ProjectWorkflowService:
    """Service for aggregating project and workflow data.

    Truth hierarchy (highest to lowest):
    1. Notion phase rows (when available)
    2. HANDOFF.md current-phase markers
    3. docs/ phase doc filesystem scan
    """

    def __init__(self) -> None:
        self._handoff_cache: dict[str, Any] = {}
        self._handoff_cache_timestamp: datetime | None = None
        self._notion_cache: list[dict[str, Any]] = []
        self._notion_cache_timestamp: datetime | None = None
        self._CACHE_TTL_SECONDS = 30

    def _is_cache_fresh(self, timestamp: datetime | None) -> bool:
        if timestamp is None:
            return False
        age = (datetime.now(tz=UTC) - timestamp).total_seconds()
        return age < self._CACHE_TTL_SECONDS

    def _read_handoff(self) -> dict[str, Any]:
        """Read and parse HANDOFF.md for current phase info.

        Parses the CURRENT phase marker, the completed phases list, and
        deferred phases. Returns structured truth about project state.
        """
        handoff_path = PROJECT_ROOT / "HANDOFF.md"
        if not handoff_path.exists():
            return {"error": "HANDOFF.md not found", "source": "filesystem"}

        try:
            content = handoff_path.read_text()
            lines = content.split("\n")

            current_phase_number: int | None = None
            current_phase_status: str = "unknown"
            current_phase_name: str | None = None
            completed_phases: dict[int, str] = {}
            deferred_phases: set[int] = set()

            for line in lines:
                # Primary marker: "## Current Phase: P93 — Name"
                header_match = re.match(r"^##\s+Current Phase:\s+P(\d+)", line)
                if header_match:
                    current_phase_number = int(header_match.group(1))
                    if "✅ COMPLETE" in line.upper() or "COMPLETE" in line:
                        current_phase_status = "completed"
                    elif "IN PROGRESS" in line.upper():
                        current_phase_status = "in_progress"
                    elif "BLOCKED" in line.upper():
                        current_phase_status = "blocked"
                    elif "DEFERRED" in line.upper():
                        current_phase_status = "deferred"
                    else:
                        current_phase_status = "active"
                    # Extract the em-dash name
                    name_match = re.search(r"P\d+\s*[—\-]\s*(.*?)(?:\s*✅|\s*⏸️|\s*🔄|\s*$)", line)
                    if name_match:
                        current_phase_name = name_match.group(1).strip()

                # Completed phase lines: "**P89 — Name** ✅ COMPLETE" or "## Completed Phase: P76"
                phase_bold_match = re.search(r"\*\*P(\d+)\s*[—\-]\s*(.*?)\*\*", line)
                if phase_bold_match:
                    pnum = int(phase_bold_match.group(1))
                    pname = phase_bold_match.group(2).strip().rstrip()
                    # Strip trailing status indicators from name
                    pname = re.sub(
                        r"\s*(✅\s*COMPLETE|⏸️\s*DEFERRED|🔄\s*IN PROGRESS)\s*$",
                        "",
                        pname,
                        flags=re.IGNORECASE,
                    ).strip()
                    if "✅ COMPLETE" in line.upper():
                        completed_phases[pnum] = pname
                    if "⏸️ DEFERRED" in line or "DEFERRED" in line.upper():
                        deferred_phases.add(pnum)

                # Back-compat section headers
                section_match = re.match(r"^##\s+Completed Phase:\s+P(\d+)", line)
                if section_match:
                    completed_phases[int(section_match.group(1))] = f"P{section_match.group(1)}"

            # Fallback for newer HANDOFF format where phase summaries are captured
            # in "Recent Sessions" entries (e.g., "P96 complete: ...").
            if not completed_phases:
                for line in lines:
                    done_match = re.search(r"\bP(\d+)\b\s+complete\b", line, flags=re.IGNORECASE)
                    if done_match:
                        pnum = int(done_match.group(1))
                        completed_phases[pnum] = f"P{pnum}"

            if current_phase_number is None:
                for line in lines:
                    progress_match = re.search(
                        r"\bP(\d+)\b\s+in\s+progress\b", line, flags=re.IGNORECASE
                    )
                    if progress_match:
                        current_phase_number = int(progress_match.group(1))
                        current_phase_status = "in_progress"
                        current_phase_name = f"P{current_phase_number}"
                        break

            # If HANDOFF "Current Phase" is completed, next phase is
            # the active one. If it's in-progress/blocked, it's active.
            # If it's deferred, mark as deferred.
            latest_completed = max(completed_phases.keys()) if completed_phases else None
            effective_current: int | None = None
            effective_status: str = "unknown"
            effective_name: str | None = None

            if current_phase_number is not None:
                if current_phase_status == "completed":
                    # The "current phase" line points to a completed phase.
                    # The actual active phase is the next one after it.
                    effective_current = current_phase_number + 1
                    effective_status = "ready"
                    effective_name = f"P{effective_current}"
                elif current_phase_status == "deferred":
                    # The "current" marker is on a deferred phase.
                    # Mark it as deferred and the next non-deferred phase as pending.
                    effective_current = current_phase_number
                    effective_status = "deferred"
                    effective_name = current_phase_name or f"P{current_phase_number}"
                else:
                    # In progress, blocked, or active
                    effective_current = current_phase_number
                    effective_status = current_phase_status
                    effective_name = current_phase_name or f"P{current_phase_number}"
            elif latest_completed is not None:
                # No explicit current phase marker; infer next phase after latest completed
                effective_current = latest_completed + 1
                effective_status = "ready"
                effective_name = f"P{effective_current}"

            # Also add current-header deferred phases to the deferred set
            if current_phase_number is not None and current_phase_status == "deferred":
                deferred_phases.add(current_phase_number)

            return {
                "current_phase": {
                    "number": effective_current,
                    "name": effective_name,
                    "status": effective_status,
                },
                "latest_completed_number": latest_completed,
                "completed_phases": dict(sorted(completed_phases.items())),
                "deferred_phases": sorted(deferred_phases),
                "raw_current_number": current_phase_number,
                "raw_current_status": current_phase_status,
                "last_updated": datetime.fromtimestamp(
                    handoff_path.stat().st_mtime, tz=UTC
                ).isoformat(),
                "source": "handoff",
            }
        except Exception as e:
            logger.warning(f"Failed to parse HANDOFF.md: {e}")
            return {"error": str(e), "source": "handoff"}

    def _read_phase_docs(self) -> list[dict[str, Any]]:
        """Read phase documentation files from docs/."""
        docs_dir = PROJECT_ROOT / "docs"
        phases = []

        try:
            for doc in sorted(docs_dir.glob("P*_*.md"), reverse=True)[:10]:
                name = doc.name.replace(".md", "").replace("_", " ")
                match = re.search(r"P(\d+)", name)
                if match:
                    phase_num = int(match.group(1))
                    phases.append(
                        {
                            "number": phase_num,
                            "name": name,
                            "doc_file": str(doc.name),
                            "modified": datetime.fromtimestamp(
                                doc.stat().st_mtime, tz=UTC
                            ).isoformat(),
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to read phase docs: {e}")

        return phases

    def _fetch_notion_phases(self) -> tuple[list[dict[str, Any]], str]:
        """Fetch phase data from Notion if available.

        Returns:
            (phases_list, sync_status) where sync_status is one of
            NotionSyncStatus values.
        """
        try:
            from ai.notion.client import is_notion_configured
            from ai.phase_control.notion_sync import NotionPhaseSync

            if not is_notion_configured():
                return [], NotionSyncStatus.UNAVAILABLE

            database_id = os.environ.get("NOTION_PHASE_DATABASE_ID", "")
            if not database_id:
                return [], NotionSyncStatus.UNAVAILABLE

            sync = NotionPhaseSync(database_id)
            rows = sync._list_rows()
            phases = []
            for row in rows:
                phases.append(
                    {
                        "phase_number": row.phase_number,
                        "phase_name": row.phase_name,
                        "status": row.status.value
                        if hasattr(row.status, "value")
                        else str(row.status),
                        "dependencies": row.dependencies,
                        "blocker": row.blocker,
                        "backend": row.backend,
                        "risk_tier": row.risk_tier,
                        "execution_mode": row.execution_mode,
                        "summary": row.summary or "",
                        "notion_page_id": row.metadata.get("notion_page_id"),
                    }
                )
            return phases, NotionSyncStatus.SYNCED

        except Exception as e:
            logger.warning(f"Notion sync failed: {e}")
            return [], NotionSyncStatus.DEGRADED

    def _get_workflow_runs(self, limit: int = 10) -> list[WorkflowRun]:
        """Get recent workflow runs from LanceDB if available."""
        runs = []

        try:
            from ai.rag.store import VectorStore, _get_schemas

            store = VectorStore()
            schemas = _get_schemas()
            table = store._ensure_table("workflow_runs", schemas["workflow_runs"])
            df = table.to_pandas()
            if df.empty:
                return []

            df = df.sort_values("started_at", ascending=False).head(limit)
            for _, row in df.iterrows():
                runs.append(
                    WorkflowRun(
                        run_id=str(row.get("run_id", "unknown")),
                        workflow_name=str(row.get("workflow_name", "unknown")),
                        status=str(row.get("status", "unknown")),
                        started_at=str(row.get("started_at", "")),
                        completed_at=str(row.get("completed_at"))
                        if row.get("completed_at")
                        else None,
                        triggered_by=str(row.get("triggered_by", "system")),
                        step_count=int(row.get("step_count", 0) or 0),
                        current_step=int(row.get("current_step"))
                        if row.get("current_step") is not None
                        else None,
                        error_message=str(row.get("error")) if row.get("error") else None,
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to get workflow runs: {e}")

        return runs

    def _get_artifacts(self, limit: int = 20) -> list[ArtifactInfo]:
        """Get recent artifacts from artifacts directory."""
        artifacts = []
        artifacts_dir = PROJECT_ROOT / "artifacts"

        try:
            if artifacts_dir.exists():
                for path in sorted(
                    artifacts_dir.rglob("*"), key=lambda p: p.stat().st_mtime, reverse=True
                )[:limit]:
                    if path.is_file():
                        stat = path.stat()
                        source_phase = None
                        parts = path.relative_to(artifacts_dir).parts
                        if parts:
                            match = re.search(r"P\d+", parts[0])
                            if match:
                                source_phase = match.group(0)

                        artifacts.append(
                            ArtifactInfo(
                                name=path.name,
                                type=path.suffix.lstrip(".") or "unknown",
                                path=str(path.relative_to(PROJECT_ROOT)),
                                size_bytes=stat.st_size,
                                created_at=datetime.fromtimestamp(
                                    stat.st_mtime, tz=UTC
                                ).isoformat(),
                                source_phase=source_phase,
                                metadata={},
                            )
                        )
        except Exception as e:
            logger.warning(f"Failed to get artifacts: {e}")

        return artifacts

    def _infer_current_phase(self) -> tuple[PhaseInfo | None, PhaseInfo | None]:
        """Infer current and latest completed phase from HANDOFF and Notion.

        Returns:
            (current_phase, latest_completed_phase)
        """
        handoff = self._read_handoff()

        current_meta = handoff.get("current_phase", {})
        completed_phases: dict[int, str] = handoff.get("completed_phases", {})
        deferred_phases: set[int] = set(handoff.get("deferred_phases", []))

        current_num = current_meta.get("number")
        current_status = str(current_meta.get("status") or "unknown").strip().lower()
        current_name = current_meta.get("name") or f"P{current_num}"

        if not current_num:
            return None, None

        # Build catalog from HANDOFF + phase docs + Notion
        phase_catalog: dict[int, dict[str, Any]] = {}
        for pnum, pname in completed_phases.items():
            phase_catalog[pnum] = {
                "number": pnum,
                "name": pname,
                "is_complete": True,
                "is_deferred": pnum in deferred_phases,
            }
        for pnum in range(76, 95):
            if pnum not in phase_catalog:
                phase_catalog[pnum] = {
                    "number": pnum,
                    "name": f"P{pnum}",
                    "is_complete": False,
                    "is_deferred": pnum in deferred_phases,
                }

        # Current phase info
        readiness = "ready"
        blockers: list[str] = []

        # Check dependency completion — only block on known incomplete phases.
        # A phase that doesn't appear in completed/deferred/current is simply
        # not tracked, not a blocker. Skip deferred phases in the dependency chain.
        known_phases = set(completed_phases.keys()) | deferred_phases
        if current_num:
            known_phases.add(current_num)
        # Only flag as blocked if a phase exists in the project (is known to be
        # incomplete but not deferred). We consider phase P76-P76+region as the
        # active UI console track, and only block on phases that appeared in
        # the HANDOFF but are neither completed nor deferred.
        range_start = min(completed_phases) if completed_phases else 76
        range_end = current_num
        relevant_deps = [p for p in range(range_start, range_end) if p not in deferred_phases]
        missing = [p for p in relevant_deps if p not in set(completed_phases.keys())]
        if missing:
            readiness = "blocked"
            missing_str = ", ".join(f"P{p}" for p in sorted(missing)[:5])
            blockers.append(f"Incomplete dependencies: {missing_str}")

        if "deferred" in current_status:
            readiness = "deferred"
        elif "blocked" in current_status:
            readiness = "blocked"
            blockers.append("Phase execution is currently blocked")
        elif "in_progress" in current_status or "active" in current_status:
            readiness = "in_progress"

        # Determine appropriate next action
        next_action = "Begin phase execution"
        if readiness == "blocked":
            next_action = "Resolve blockers before execution"
        elif readiness == "deferred":
            next_action = "Phase deferred — check HANDOFF.md for resumption criteria"
        elif readiness == "in_progress":
            next_action = "Continue phase execution"

        current_phase = PhaseInfo(
            phase_number=current_num,
            phase_name=current_name,
            status=current_status,
            dependencies=[p for p in range(76, current_num)],
            blockers=blockers,
            readiness=readiness,
            next_action=next_action,
            execution_mode="safe",
            risk_tier="medium",
            backend="opencode",
        )

        # Latest completed phase
        latest_completed: PhaseInfo | None = None
        latest_completed_num = handoff.get("latest_completed_number")
        if latest_completed_num and latest_completed_num in completed_phases:
            latest_completed = PhaseInfo(
                phase_number=latest_completed_num,
                phase_name=completed_phases[latest_completed_num],
                status="completed",
                dependencies=[],
                blockers=[],
                readiness="ready",
                next_action="Completed",
                execution_mode="safe",
                risk_tier="medium",
                backend="opencode",
            )

        return current_phase, latest_completed

    def _generate_recommendations(
        self,
        phase: PhaseInfo | None,
        latest_completed: PhaseInfo | None,
        workflows: list[WorkflowRun],
        artifacts: list[ArtifactInfo],
        notion_status: str,
    ) -> list[str]:
        """Generate next-action recommendations grounded in current state."""
        recommendations = []

        if not phase:
            recommendations.append("Initialize phase documentation in docs/ and HANDOFF.md")
            return recommendations

        # Phase-specific recommendations
        if phase.blockers:
            recommendations.append(f"Resolve blockers: {'; '.join(phase.blockers[:3])}")

        if phase.readiness == "ready":
            recommendations.append(f"Execute P{phase.phase_number} with preflight validation")
        elif phase.readiness == "deferred":
            recommendations.append(
                f"P{phase.phase_number} is deferred — review HANDOFF.md for resumption criteria"
            )
        elif phase.readiness == "in_progress":
            recommendations.append(
                f"Continue P{phase.phase_number} execution — follow phase prompt"
            )
        elif phase.readiness == "blocked":
            recommendations.append(
                "Complete prerequisite phases or resolve blockers before proceeding"
            )

        # Workflow failure check
        failed_runs = [w for w in workflows if w.status == "failed"]
        if failed_runs:
            recommendations.append(f"Review {len(failed_runs)} failed workflow run(s)")

        # Artifact generation check
        phase_artifacts = [a for a in artifacts if a.source_phase == f"P{phase.phase_number}"]
        if len(phase_artifacts) < 2 and phase.readiness in ("ready", "in_progress"):
            recommendations.append("Generate validation artifacts for phase closeout")

        # Notion sync status recommendation
        if notion_status == NotionSyncStatus.UNAVAILABLE:
            recommendations.append(
                "Notion sync unavailable — local HANDOFF.md truth is authoritative"
            )
        elif notion_status == NotionSyncStatus.DEGRADED:
            recommendations.append("Notion sync degraded — verify key configuration")

        return recommendations[:5]

    def get_project_context(self) -> ProjectContext:
        """Get complete project context with Notion parity."""
        current_phase, latest_completed = self._infer_current_phase()
        workflows = self._get_workflow_runs(limit=10)
        artifacts = self._get_artifacts(limit=20)

        # Fetch Notion parity
        notion_phases, notion_sync_status = self._fetch_notion_phases()

        # Build preflight summary
        preflight = PreflightSummary(
            schema_version="p75.v1",
            generated_at=datetime.now(tz=UTC).isoformat(),
            gate_status="pass" if current_phase and not current_phase.blockers else "fail",
            gate_reason="Dependencies satisfied"
            if current_phase and not current_phase.blockers
            else "Blockers exist",
            code_files_count=0,
            impact_score=None,
            health_status="healthy",
            health_issues=[],
        )

        # Determine Notion sync message
        notion_message = ""
        if notion_sync_status == NotionSyncStatus.SYNCED:
            notion_message = f"Notion synced ({len(notion_phases)} phases)"
        elif notion_sync_status == NotionSyncStatus.UNAVAILABLE:
            notion_message = "Notion not configured — using local HANDOFF.md truth"
        elif notion_sync_status == NotionSyncStatus.DEGRADED:
            notion_message = "Notion sync degraded — falling back to local truth"

        # Merge Notion status into current phase if available
        if current_phase and notion_sync_status == NotionSyncStatus.SYNCED and notion_phases:
            notion_phase = next(
                (p for p in notion_phases if p.get("phase_number") == current_phase.phase_number),
                None,
            )
            if notion_phase:
                current_phase.notion_status = notion_phase.get("status")

        return ProjectContext(
            current_phase=current_phase,
            latest_completed_phase=latest_completed,
            recent_workflows=workflows,
            artifacts=artifacts,
            preflight=preflight,
            handoff_summary=self._read_handoff(),
            recommendations=self._generate_recommendations(
                current_phase, latest_completed, workflows, artifacts, notion_sync_status
            ),
            notion_sync_status=notion_sync_status,
            notion_sync_message=notion_message,
        )

    def get_workflow_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get workflow run history."""
        runs = self._get_workflow_runs(limit=limit)
        return [
            {
                "run_id": r.run_id,
                "workflow_name": r.workflow_name,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "triggered_by": r.triggered_by,
                "step_count": r.step_count,
                "current_step": r.current_step,
                "error_message": r.error_message,
            }
            for r in runs
        ]

    def get_phase_timeline(self) -> list[dict[str, Any]]:
        """Get phase timeline from HANDOFF + docs + Notion parity."""
        docs = self._read_phase_docs()
        handoff = self._read_handoff()
        notion_phases, notion_sync_status = self._fetch_notion_phases()

        current_meta = handoff.get("current_phase", {})
        current = current_meta.get("number")
        current_status = str(current_meta.get("status") or "").strip().lower()
        completed_phases: dict[int, str] = handoff.get("completed_phases", {})
        deferred_phases: set[int] = set(handoff.get("deferred_phases", []))

        docs_by_number = {doc["number"]: doc for doc in docs}
        phase_numbers = set(docs_by_number)
        phase_numbers.update(completed_phases.keys())
        phase_numbers.update(deferred_phases)  # Show deferred phases in timeline
        if current:
            phase_numbers.add(current)

        # Include Notion phases
        notion_by_number: dict[int, dict[str, Any]] = {}
        if notion_sync_status in (NotionSyncStatus.SYNCED, NotionSyncStatus.DEGRADED):
            for np in notion_phases:
                pnum = np.get("phase_number", 0)
                notion_by_number[pnum] = np
                phase_numbers.add(pnum)

        timeline = []
        for phase_number in sorted(phase_numbers):
            doc = docs_by_number.get(phase_number)
            status = "planned"

            # HANDOFF truth
            if phase_number in completed_phases:
                status = "completed"
            elif phase_number in deferred_phases:
                status = "deferred"
            elif current and phase_number == current:
                if "in_progress" in current_status or "active" in current_status:
                    status = "in_progress"
                elif "deferred" in current_status:
                    status = "deferred"
                elif "blocked" in current_status:
                    status = "blocked"
                elif "completed" in current_status:
                    # Current phase marker is on a completed phase;
                    # this means the next phase is "ready"
                    status = "completed"
                else:
                    status = "ready"
            elif (
                current
                and phase_number < current
                and phase_number not in completed_phases
                and phase_number not in deferred_phases
            ):
                status = "blocked"

            # Notion override when synced
            if notion_sync_status == NotionSyncStatus.SYNCED and phase_number in notion_by_number:
                notion_status = notion_by_number[phase_number].get("status", "").lower()
                notion_mapped = {
                    "planned": "planned",
                    "ready": "ready",
                    "in progress": "in_progress",
                    "done": "completed",
                    "completed": "completed",
                    "needs review": "in_progress",
                    "blocked": "blocked",
                    "cancelled": "cancelled",
                }
                mapped = notion_mapped.get(notion_status)
                if mapped:
                    status = mapped

            phase_name = completed_phases.get(phase_number) or f"P{phase_number}"
            if not phase_name and doc:
                phase_name = doc["name"]
            if not phase_name:
                phase_name = f"P{phase_number}"

            timeline.append(
                {
                    "number": phase_number,
                    "name": phase_name,
                    "status": status,
                    "doc_file": doc["doc_file"] if doc else "",
                    "modified": doc["modified"] if doc else "",
                    "notion_status": notion_by_number.get(phase_number, {}).get("status"),
                }
            )

        return timeline


_project_workflow_service: ProjectWorkflowService | None = None


def get_project_workflow_service() -> ProjectWorkflowService:
    """Get the singleton service instance."""
    global _project_workflow_service
    if _project_workflow_service is None:
        _project_workflow_service = ProjectWorkflowService()
    return _project_workflow_service


def get_project_context() -> dict[str, Any]:
    """Get complete project context for MCP."""
    service = get_project_workflow_service()
    context = service.get_project_context()

    return {
        "success": True,
        "current_phase": {
            "phase_number": context.current_phase.phase_number if context.current_phase else None,
            "phase_name": context.current_phase.phase_name if context.current_phase else None,
            "status": context.current_phase.status if context.current_phase else None,
            "readiness": context.current_phase.readiness if context.current_phase else None,
            "blockers": context.current_phase.blockers if context.current_phase else [],
            "next_action": context.current_phase.next_action if context.current_phase else None,
            "risk_tier": context.current_phase.risk_tier if context.current_phase else None,
            "backend": context.current_phase.backend if context.current_phase else None,
            "notion_status": context.current_phase.notion_status if context.current_phase else None,
        },
        "latest_completed_phase": {
            "phase_number": context.latest_completed_phase.phase_number
            if context.latest_completed_phase
            else None,
            "phase_name": context.latest_completed_phase.phase_name
            if context.latest_completed_phase
            else None,
            "status": context.latest_completed_phase.status
            if context.latest_completed_phase
            else None,
        }
        if context.latest_completed_phase
        else None,
        "workflow_count": len(context.recent_workflows),
        "artifact_count": len(context.artifacts),
        "recommendations": context.recommendations,
        "preflight_status": context.preflight.gate_status if context.preflight else "unknown",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "notion_sync_status": context.notion_sync_status,
        "notion_sync_message": context.notion_sync_message,
    }


def get_workflow_history(limit: int = 20) -> list[dict[str, Any]]:
    """Get workflow history for MCP."""
    service = get_project_workflow_service()
    return service.get_workflow_history(limit=limit)


def get_phase_timeline() -> list[dict[str, Any]]:
    """Get phase timeline for MCP."""
    service = get_project_workflow_service()
    return service.get_phase_timeline()


def get_recent_artifacts(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent artifacts for MCP."""
    service = get_project_workflow_service()
    artifacts = service._get_artifacts(limit=limit)
    return [
        {
            "name": a.name,
            "type": a.type,
            "path": a.path,
            "size_bytes": a.size_bytes,
            "created_at": a.created_at,
            "source_phase": a.source_phase,
        }
        for a in artifacts
    ]
