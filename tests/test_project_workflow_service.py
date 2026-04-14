"""Tests for project workflow phase truth parsing."""

from pathlib import Path

import ai.project_workflow_service as pws


def _write_handoff(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# Handoff — bazzite-laptop",
                "",
                "## Current Phase: P90 (Gated)",
                "",
                "**P77 — UI Architecture + Contracts Baseline** ✅ COMPLETE",
                "**P78 — Midnight Glass Design System + Figma Mapping** ✅ COMPLETE",
                "**P79 — Frontend Shell Bootstrap** ✅ COMPLETE",
                "**P80 — Auth, 2FA, Recovery, Gmail Notifications** ✅ COMPLETE",
                "**P81 — PIN-Gated Settings + Secrets Service** ✅ COMPLETE",
                "**P82 — Provider + Model Discovery / Routing Console** ✅ COMPLETE",
                "**P83 — Chat + MCP Workspace Integration** ✅ COMPLETE",
                "**P84 — Security Ops Center** ✅ COMPLETE",
                "**P85 — Interactive Shell Gateway** ✅ COMPLETE",
                "**P86 — Project + Workflow + Phase Panels** ✅ COMPLETE",
                "**P87 — Newelle/PySide Migration + Compatibility Cutover** ✅ COMPLETE",
                "**P88 — UI Hardening, Validation, Docs, Launch Handoff** ✅ COMPLETE",
                "**P89 — Security Improvement + Remediation Closure** ✅ COMPLETE",
            ]
        ),
        encoding="utf-8",
    )


def test_infer_current_phase_uses_handoff_truth(monkeypatch, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "P88_UI_HARDENING_LAUNCH_HANDOFF.md").write_text("# P88", encoding="utf-8")
    (docs / "P89_SECURITY_IMPROVEMENT_REMEDIATION_CLOSURE.md").write_text("# P89", encoding="utf-8")
    _write_handoff(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    phase = svc._infer_current_phase()

    assert phase is not None
    assert phase.phase_number == 90
    assert phase.status == "Gated"
    assert phase.readiness == "blocked"
    assert phase.blockers == ["Phase execution is currently gated in HANDOFF.md"]


def test_phase_timeline_includes_current_gated_phase(monkeypatch, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "P88_UI_HARDENING_LAUNCH_HANDOFF.md").write_text("# P88", encoding="utf-8")
    (docs / "P89_SECURITY_IMPROVEMENT_REMEDIATION_CLOSURE.md").write_text("# P89", encoding="utf-8")
    _write_handoff(tmp_path / "HANDOFF.md")

    monkeypatch.setattr(pws, "PROJECT_ROOT", tmp_path)

    svc = pws.ProjectWorkflowService()
    timeline = svc.get_phase_timeline()

    p90 = next((row for row in timeline if row["number"] == 90), None)
    p89 = next((row for row in timeline if row["number"] == 89), None)

    assert p90 is not None
    assert p90["status"] == "ready"
    assert p89 is not None
    assert p89["status"] == "completed"
