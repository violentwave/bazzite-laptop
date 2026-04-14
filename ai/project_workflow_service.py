"""Project and workflow aggregation service for P86.

This service aggregates data from phase-control, workflow runs, and project
intelligence sources to provide a unified view for the Project + Workflow panel.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Data paths
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path.home() / "projects" / "bazzite-laptop"))
WORKFLOW_DB_PATH = Path.home() / "security" / "vector-db" / "workflow_runs.lance"


@dataclass
class PhaseInfo:
    """Current phase information."""

    phase_number: int
    phase_name: str
    status: str
    dependencies: list[int]
    blockers: list[str]
    readiness: str  # ready, blocked, degraded, unknown
    next_action: str
    execution_mode: str
    risk_tier: str
    backend: str


@dataclass
class WorkflowRun:
    """Workflow run summary."""

    run_id: str
    workflow_name: str
    status: str  # pending, running, completed, failed, cancelled
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
    gate_status: str  # pass, fail, warn
    gate_reason: str
    code_files_count: int
    impact_score: float | None
    health_status: str
    health_issues: list[str]


@dataclass
class ProjectContext:
    """Complete project context for UI."""

    current_phase: PhaseInfo | None
    recent_workflows: list[WorkflowRun]
    artifacts: list[ArtifactInfo]
    preflight: PreflightSummary | None
    handoff_summary: dict[str, Any]
    recommendations: list[str]


class ProjectWorkflowService:
    """Service for aggregating project and workflow data."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._cache: dict[str, Any] = {}
        self._cache_timestamp: datetime | None = None

    def _read_handoff(self) -> dict[str, Any]:
        """Read and parse HANDOFF.md for current phase info."""
        handoff_path = PROJECT_ROOT / "HANDOFF.md"
        if not handoff_path.exists():
            return {"error": "HANDOFF.md not found"}

        try:
            content = handoff_path.read_text()
            # Extract current phase from the header
            current_phase = {"number": None, "name": None, "status": "unknown"}

            for line in content.split("\n")[:50]:
                if "Current Phase:" in line:
                    # Format: "Current Phase: P86 (Next)" or similar
                    import re

                    match = re.search(r"P(\d+)", line)
                    if match:
                        current_phase["number"] = int(match.group(1))
                if line.startswith("## Completed Phase: P"):
                    import re

                    match = re.search(r"P(\d+)", line)
                    if match:
                        current_phase["completed"] = int(match.group(1))

            # Find the most recently completed phase section
            return {
                "current_phase": current_phase,
                "last_updated": datetime.fromtimestamp(
                    handoff_path.stat().st_mtime, tz=UTC
                ).isoformat(),
            }
        except Exception as e:
            logger.warning(f"Failed to parse HANDOFF.md: {e}")
            return {"error": str(e)}

    def _read_phase_docs(self) -> list[dict[str, Any]]:
        """Read phase documentation files."""
        docs_dir = PROJECT_ROOT / "docs"
        phases = []

        try:
            for doc in sorted(docs_dir.glob("P*_*.md"), reverse=True)[:10]:
                name = doc.name.replace(".md", "").replace("_", " ")
                import re

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

    def _get_workflow_runs(self, limit: int = 10) -> list[WorkflowRun]:
        """Get recent workflow runs from LanceDB if available."""
        runs = []

        try:
            # Try to query workflow_runs table via existing workflow tools
            from ai.mcp_bridge.handlers.workflow_tools import get_workflow_history

            history = get_workflow_history(limit=limit)
            for item in history:
                runs.append(
                    WorkflowRun(
                        run_id=item.get("run_id", "unknown"),
                        workflow_name=item.get("workflow_name", "unknown"),
                        status=item.get("status", "unknown"),
                        started_at=item.get("started_at", ""),
                        completed_at=item.get("completed_at"),
                        triggered_by=item.get("triggered_by", "system"),
                        step_count=item.get("step_count", 0),
                        current_step=item.get("current_step"),
                        error_message=item.get("error_message"),
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
                        # Try to determine source phase from path
                        source_phase = None
                        parts = path.relative_to(artifacts_dir).parts
                        if parts:
                            import re

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

    def _infer_current_phase(self) -> PhaseInfo | None:
        """Infer current phase from HANDOFF and phase docs."""
        handoff = self._read_handoff()
        phase_docs = self._read_phase_docs()

        current_phase_num = handoff.get("current_phase", {}).get("number")
        if not current_phase_num and phase_docs:
            # Infer from most recent completed + 1
            completed = [p["number"] for p in phase_docs]
            if completed:
                current_phase_num = max(completed) + 1

        if not current_phase_num:
            return None

        # Find phase doc for current phase
        phase_doc = next(
            (p for p in phase_docs if p["number"] == current_phase_num),
            None,
        )

        # Determine readiness based on dependencies
        readiness = "ready"
        blockers = []

        # Check if previous phases are complete
        if phase_docs:
            prev_phases = [p["number"] for p in phase_docs if p["number"] < current_phase_num]
            expected_prev = list(range(77, current_phase_num))  # P77 is first UI phase
            missing = set(expected_prev) - set(prev_phases)
            if missing:
                readiness = "blocked"
                blockers.append(
                    f"Dependencies incomplete: P{', P'.join(map(str, sorted(missing)))}"
                )

        return PhaseInfo(
            phase_number=current_phase_num,
            phase_name=phase_doc["name"] if phase_doc else f"P{current_phase_num}",
            status="In Progress" if phase_doc else "Planned",
            dependencies=list(range(77, current_phase_num)),
            blockers=blockers,
            readiness=readiness,
            next_action="Continue implementation" if readiness == "ready" else "Resolve blockers",
            execution_mode="safe",
            risk_tier="medium",
            backend="opencode",
        )

    def _generate_recommendations(
        self, phase: PhaseInfo | None, workflows: list[WorkflowRun], artifacts: list[ArtifactInfo]
    ) -> list[str]:
        """Generate next-action recommendations."""
        recommendations = []

        if not phase:
            recommendations.append("Initialize phase documentation in docs/")
            return recommendations

        if phase.blockers:
            recommendations.append(f"Resolve blockers: {', '.join(phase.blockers)}")

        # Check for recent workflow failures
        failed_runs = [w for w in workflows if w.status == "failed"]
        if failed_runs:
            recommendations.append(f"Review {len(failed_runs)} failed workflow runs")

        # Check artifact generation
        if len(artifacts) < 3:
            recommendations.append("Generate validation artifacts for phase closeout")

        # Add phase-specific recommendations
        if phase.readiness == "ready":
            recommendations.append("Execute phase with preflight validation")
        else:
            recommendations.append("Complete prerequisite phases before execution")

        return recommendations[:5]

    def get_project_context(self) -> ProjectContext:
        """Get complete project context."""
        current_phase = self._infer_current_phase()
        workflows = self._get_workflow_runs(limit=10)
        artifacts = self._get_artifacts(limit=20)

        # Build preflight summary placeholder
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

        return ProjectContext(
            current_phase=current_phase,
            recent_workflows=workflows,
            artifacts=artifacts,
            preflight=preflight,
            handoff_summary=self._read_handoff(),
            recommendations=self._generate_recommendations(current_phase, workflows, artifacts),
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
        """Get phase timeline from docs."""
        docs = self._read_phase_docs()
        handoff = self._read_handoff()
        current = handoff.get("current_phase", {}).get("number")

        timeline = []
        for doc in sorted(docs, key=lambda x: x["number"]):
            status = "completed"
            if current and doc["number"] == current:
                status = "in_progress"
            elif current and doc["number"] > current:
                status = "planned"

            timeline.append(
                {
                    "number": doc["number"],
                    "name": doc["name"],
                    "status": status,
                    "doc_file": doc["doc_file"],
                    "modified": doc["modified"],
                }
            )

        return timeline


# Singleton instance
_project_workflow_service: ProjectWorkflowService | None = None


def get_project_workflow_service() -> ProjectWorkflowService:
    """Get the singleton service instance."""
    global _project_workflow_service
    if _project_workflow_service is None:
        _project_workflow_service = ProjectWorkflowService()
    return _project_workflow_service


# MCP tool functions


def get_project_context() -> dict[str, Any]:
    """Get complete project context for MCP."""
    service = get_project_workflow_service()
    context = service.get_project_context()

    return {
        "current_phase": {
            "phase_number": context.current_phase.phase_number if context.current_phase else None,
            "phase_name": context.current_phase.phase_name if context.current_phase else None,
            "status": context.current_phase.status if context.current_phase else None,
            "readiness": context.current_phase.readiness if context.current_phase else None,
            "blockers": context.current_phase.blockers if context.current_phase else [],
            "next_action": context.current_phase.next_action if context.current_phase else None,
            "risk_tier": context.current_phase.risk_tier if context.current_phase else None,
            "backend": context.current_phase.backend if context.current_phase else None,
        },
        "workflow_count": len(context.recent_workflows),
        "artifact_count": len(context.artifacts),
        "recommendations": context.recommendations,
        "preflight_status": context.preflight.gate_status if context.preflight else "unknown",
        "generated_at": datetime.now(tz=UTC).isoformat(),
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
