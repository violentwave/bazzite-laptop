"""Structured HANDOFF helpers for Agent Workbench session closeout notes."""

from __future__ import annotations

from pathlib import Path

from ai.agent_workbench.models import HandoffNote
from ai.agent_workbench.paths import now_iso
from ai.config import PROJECT_ROOT


def append_handoff_note(
    *,
    summary: str,
    artifacts: list[str] | None = None,
    phase: str = "P123",
    session_id: str | None = None,
    handoff_path: Path = PROJECT_ROOT / "HANDOFF.md",
) -> dict:
    if not summary or not summary.strip():
        raise ValueError("Summary is required")

    note = HandoffNote(
        timestamp=now_iso(),
        phase=phase,
        summary=summary.strip(),
        artifacts=artifacts or [],
        session_id=session_id,
    )

    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    with open(handoff_path, "a", encoding="utf-8") as handle:
        handle.write("\n" + note.to_markdown())

    return {
        "success": True,
        "note": {
            "timestamp": note.timestamp,
            "phase": note.phase,
            "summary": note.summary,
            "artifacts": note.artifacts,
            "session_id": note.session_id,
        },
    }
