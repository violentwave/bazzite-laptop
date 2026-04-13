"""Tests for P75 project-intelligence preflight and gating."""

from unittest.mock import patch

from ai.phase_control.models import PhaseRow, PhaseStatus
from ai.phase_control.policy import check_preflight_gate
from ai.phase_control.preflight import build_preflight_record


def _phase() -> PhaseRow:
    return PhaseRow(
        phase_name="P75",
        phase_number=75,
        status=PhaseStatus.READY,
        execution_prompt="Implement preflight gate",
        validation_commands=["python -V"],
        done_criteria=["tests pass"],
        backend="opencode",
        risk_tier="high",
    )


def test_check_preflight_gate_blocks_when_not_allowed():
    record = {
        "gate": {
            "allowed": False,
            "blockers": ["timer_health_critical"],
            "warnings": [],
        }
    }
    decision = check_preflight_gate(record)
    assert decision.allowed is False
    assert any(e.code == "preflight_blocked" for e in decision.events)


def test_build_preflight_record_allowed_path():
    phase = _phase()
    with (
        patch(
            "ai.phase_control.preflight._artifact_context",
            return_value={"phase_docs": ["docs/P74_PLAN.md"], "handoff_entries": []},
        ),
        patch(
            "ai.phase_control.preflight._code_context",
            return_value={
                "fused": {"results": [{"relative_path": "ai/router.py"}]},
                "changed_files": ["ai/router.py"],
            },
        ),
        patch(
            "ai.phase_control.preflight._pattern_context",
            return_value={
                "task_patterns": [{"id": "1"}],
                "agent_knowledge": [],
                "shared_context": [],
            },
        ),
        patch(
            "ai.phase_control.preflight._health_context",
            return_value={
                "timers": {"status": "healthy"},
                "pipeline": {"status": "healthy"},
                "providers": {},
            },
        ),
        patch("ai.phase_control.preflight._persist_preflight_summary"),
    ):
        record = build_preflight_record(phase, repo_path="/tmp")

    payload = record.to_dict()
    assert payload["schema_version"] == "p75.v1"
    assert payload["gate"]["allowed"] is True
    assert payload["phase_context"]["phase_number"] == 75


def test_build_preflight_record_blocks_on_critical_timer():
    phase = _phase()
    with (
        patch(
            "ai.phase_control.preflight._artifact_context",
            return_value={"phase_docs": ["docs/P74_PLAN.md"], "handoff_entries": []},
        ),
        patch(
            "ai.phase_control.preflight._code_context",
            return_value={
                "fused": {"results": [{"relative_path": "ai/router.py"}]},
                "changed_files": ["ai/router.py"],
            },
        ),
        patch(
            "ai.phase_control.preflight._pattern_context",
            return_value={
                "task_patterns": [{"id": "1"}],
                "agent_knowledge": [],
                "shared_context": [],
            },
        ),
        patch(
            "ai.phase_control.preflight._health_context",
            return_value={
                "timers": {"status": "critical"},
                "pipeline": {"status": "healthy"},
                "providers": {},
            },
        ),
        patch("ai.phase_control.preflight._persist_preflight_summary"),
    ):
        record = build_preflight_record(phase, repo_path="/tmp")

    assert record.gate["allowed"] is False
    assert "timer_health_critical" in record.gate["blockers"]
