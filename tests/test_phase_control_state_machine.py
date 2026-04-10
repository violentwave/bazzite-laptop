"""State machine tests for P55 phase control."""

import pytest

from ai.phase_control.models import PhaseRow, PhaseStatus
from ai.phase_control.state_machine import TransitionError, can_transition, transition_phase


def _ready_phase() -> PhaseRow:
    return PhaseRow(
        phase_name="P55",
        phase_number=55,
        status=PhaseStatus.READY,
        execution_prompt="do work",
        validation_commands=["python -V"],
        done_criteria=["tests pass"],
    )


def test_allowed_transition_matrix_core_paths():
    assert can_transition(PhaseStatus.PLANNED, PhaseStatus.READY)
    assert can_transition(PhaseStatus.READY, PhaseStatus.IN_PROGRESS)
    assert can_transition(PhaseStatus.IN_PROGRESS, PhaseStatus.DONE)
    assert can_transition(PhaseStatus.IN_PROGRESS, PhaseStatus.NEEDS_REVIEW)
    assert can_transition(PhaseStatus.IN_PROGRESS, PhaseStatus.BLOCKED)
    assert can_transition(PhaseStatus.READY, PhaseStatus.CANCELLED)
    assert can_transition(PhaseStatus.IN_PROGRESS, PhaseStatus.CANCELLED)
    assert can_transition(PhaseStatus.BLOCKED, PhaseStatus.READY)
    assert can_transition(PhaseStatus.NEEDS_REVIEW, PhaseStatus.READY)
    assert not can_transition(PhaseStatus.CANCELLED, PhaseStatus.READY)


def test_ready_requires_prompt_validation_done_criteria():
    phase = PhaseRow(phase_name="P55", phase_number=55, status=PhaseStatus.PLANNED)
    with pytest.raises(TransitionError):
        transition_phase(phase, PhaseStatus.READY)


def test_in_progress_requires_lease_and_approval_when_required():
    phase = _ready_phase()
    phase.approval_required = True

    with pytest.raises(TransitionError):
        transition_phase(
            phase, PhaseStatus.IN_PROGRESS, lease_acquired=False, approval_satisfied=False
        )

    with pytest.raises(TransitionError):
        transition_phase(
            phase, PhaseStatus.IN_PROGRESS, lease_acquired=True, approval_satisfied=False
        )

    transition_phase(phase, PhaseStatus.IN_PROGRESS, lease_acquired=True, approval_satisfied=True)
    assert phase.status == PhaseStatus.IN_PROGRESS


def test_done_requires_validation_passed():
    phase = _ready_phase()
    transition_phase(phase, PhaseStatus.IN_PROGRESS, lease_acquired=True, approval_satisfied=True)
    with pytest.raises(TransitionError):
        transition_phase(phase, PhaseStatus.DONE, validation_passed=False)
    transition_phase(phase, PhaseStatus.DONE, validation_passed=True)
    assert phase.status == PhaseStatus.DONE


def test_blocked_requires_blocker_and_validation_summary():
    phase = _ready_phase()
    transition_phase(phase, PhaseStatus.IN_PROGRESS, lease_acquired=True, approval_satisfied=True)
    with pytest.raises(TransitionError):
        transition_phase(phase, PhaseStatus.BLOCKED, blocker="", validation_summary={})
    with pytest.raises(TransitionError):
        transition_phase(phase, PhaseStatus.BLOCKED, blocker="failed", validation_summary=None)
    transition_phase(
        phase,
        PhaseStatus.BLOCKED,
        blocker="validation failed",
        validation_summary={"passed": False},
    )
    assert phase.status == PhaseStatus.BLOCKED


def test_cancelled_requires_explicit_reason():
    phase = _ready_phase()
    with pytest.raises(TransitionError):
        transition_phase(phase, PhaseStatus.CANCELLED, reason_text="")
    transition_phase(phase, PhaseStatus.CANCELLED, reason_text="human requested cancel")
    assert phase.status == PhaseStatus.CANCELLED
