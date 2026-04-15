"""Tests for project workflow phase truth parsing (P93 truth integration)."""

from pathlib import Path

import ai.project_workflow_service as pws


def _patch_notion_unavailable(svc):
    """Mock Notion phases to return unavailable (no real API calls in tests)."""
    svc._fetch_notion_phases = lambda: ([], "unavailable")


def _write_handoff_completed(path: Path) -> None:
    """Write HANDOFF.md where P92 is current and marked COMPLETE."""
    path.write_text(
        "\n".join(
            [
                "# Handoff — bazzite-laptop",
                "",
                "## Current Phase: P92 ✅ COMPLETE",
                "",
                "**P77 — UI Architecture + Contracts Baseline** ✅ COMPLETE",
                "**P78 — Midnight Glass Design System + Figma Mapping** ✅ COMPLETE",
                "**P79 — Frontend Shell Bootstrap** ✅ COMPLETE",
                "**P80 — Auth, 2FA, Recovery, Gmail Notifications** ⏸️ DEFERRED",
                "**P81 — PIN-Gated Settings + Secrets Service** ✅ COMPLETE",
                "**P82 — Provider + Model Discovery / Routing Console** ✅ COMPLETE",
                "**P83 — Chat + MCP Workspace Integration** ✅ COMPLETE",
                "**P84 — Security Ops Center** ✅ COMPLETE",
                "**P85 — Interactive Shell Gateway** ✅ COMPLETE",
                "**P86 — Project + Workflow + Phase Panels** ✅ COMPLETE",
                "**P87 — Newelle/PySide Migration + Compatibility Cutover** ✅ COMPLETE",
                "**P88 — UI Hardening, Validation, Docs, Launch Handoff** ✅ COMPLETE",
                "**P89 — Security Improvement + Remediation Closure** ✅ COMPLETE",
                "**P90 — Console Runtime Recovery + Contract Reconciliation** ✅ COMPLETE",
                "**P91 — Settings, Secrets, and PIN End-to-End Hardening** ✅ COMPLETE",
                "**P92 — Providers + Security Surfaces Live Integration** ✅ COMPLETE",
            ]
        ),
        encoding="utf-8",
    )


def _write_handoff_in_progress(path: Path) -> None:
    """Write HANDOFF.md where P93 is actively in progress."""
    path.write_text(
        "\n".join(
            [
                "# Handoff — bazzite-laptop",
                "",
                "## Current Phase: P93 — Project, Workflow, and Phase Truth Integration",
                "",
                "**P91 — Settings, Secrets, and PIN End-to-End Hardening** ✅ COMPLETE",
                "**P92 — Providers + Security Surfaces Live Integration** ✅ COMPLETE",
            ]
        ),
        encoding="utf-8",
    )


def _write_handoff_deferred(path: Path) -> None:
    """Write HANDOFF.md where current phase is deferred."""
    path.write_text(
        "\n".join(
            [
                "# Handoff — bazzite-laptop",
                "",
                "## Current Phase: P80 — Auth, 2FA, Recovery, Gmail Notifications ⏸️ DEFERRED",
                "",
                "**P77 — UI Architecture** ✅ COMPLETE",
                "**P78 — Design System** ✅ COMPLETE",
                "**P79 — Frontend Shell Bootstrap** ✅ COMPLETE",
            ]
        ),
        encoding="utf-8",
    )


def test_completed_header_infers_next_phase(monkeypatch, tmp_path: Path):
    """When HANDOFF says 'P92 COMPLETE', effective current is P93 (ready)."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    current, latest_completed = svc._infer_current_phase()

    assert current is not None
    assert current.phase_number == 93
    # P93 with all deps (except deferred P80) completed should be ready
    assert current.readiness == "ready"

    assert latest_completed is not None
    assert latest_completed.phase_number == 92
    assert latest_completed.status == "completed"


def test_in_progress_header_keeps_phase(monkeypatch, tmp_path: Path):
    """When HANDOFF says P93 in progress, P93 is the current phase."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_in_progress(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    current, latest_completed = svc._infer_current_phase()

    assert current is not None
    assert current.phase_number == 93
    assert current.status == "active"
    assert current.readiness == "in_progress"

    assert latest_completed is not None
    assert latest_completed.phase_number == 92


def test_deferred_phase_detected(monkeypatch, tmp_path: Path):
    """Deferred phases are properly tracked in handoff parse."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_deferred(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    handoff = svc._read_handoff()

    assert 80 in handoff.get("deferred_phases", [])
    current, _ = svc._infer_current_phase()

    assert current is not None
    assert current.phase_number == 80
    assert current.readiness == "deferred"


def test_deferred_deps_dont_block(monkeypatch, tmp_path: Path):
    """P80 (deferred) should not block P93 as a missing dependency."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    current, _ = svc._infer_current_phase()

    assert current is not None
    assert current.phase_number == 93
    # P80 is deferred, so it should not appear as a blocker
    assert current.readiness == "ready"
    assert len(current.blockers) == 0


def test_phase_timeline_completed_and_deferred_status(monkeypatch, tmp_path: Path):
    """Timeline shows completed and deferred phases correctly."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    _patch_notion_unavailable(svc)
    timeline = svc.get_phase_timeline()

    # P77-P79, P81-P92 should show as completed
    p92 = next((row for row in timeline if row["number"] == 92), None)
    assert p92 is not None
    assert p92["status"] == "completed"

    # P80 should show as deferred
    p80 = next((row for row in timeline if row["number"] == 80), None)
    assert p80 is not None
    assert p80["status"] == "deferred"


def test_phase_timeline_shows_ready_for_next_phase(monkeypatch, tmp_path: Path):
    """When last completed is P92, P93 shows as ready."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    _patch_notion_unavailable(svc)
    timeline = svc.get_phase_timeline()

    # P93 should appear as ready
    p93 = next((row for row in timeline if row["number"] == 93), None)
    assert p93 is not None
    assert p93["status"] == "ready"


def test_project_context_includes_notion_sync_status(monkeypatch, tmp_path: Path):
    """Project context includes Notion sync status fields."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    context = svc.get_project_context()

    assert context.notion_sync_status in ("synced", "unavailable", "degraded", "stale")
    # Notion status should not be empty
    assert context.notion_sync_message != ""


def test_project_context_includes_latest_completed(monkeypatch, tmp_path: Path):
    """Project context includes latest completed phase."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    context = svc.get_project_context()

    assert context.latest_completed_phase is not None
    assert context.latest_completed_phase.phase_number == 92


def test_recommendations_not_hardcoded(monkeypatch, tmp_path: Path):
    """Recommendations are derived from state, not hardcoded."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    context = svc.get_project_context()

    # Recommendations should exist and be context-aware
    assert len(context.recommendations) > 0


def test_get_project_context_mcp_includes_new_fields(monkeypatch, tmp_path: Path):
    """MCP get_project_context returns success and new fields."""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    _write_handoff_completed(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    result = pws.get_project_context()
    assert result.get("success") is True
    assert "notion_sync_status" in result
    assert "notion_sync_message" in result
    assert "latest_completed_phase" in result
