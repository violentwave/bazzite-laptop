"""State transition logic for the phase-control lifecycle."""

from __future__ import annotations

from ai.phase_control.models import PhaseRow, PhaseStatus


class TransitionError(ValueError):
    """Raised when a state transition is invalid or violates rules."""


ALLOWED_TRANSITIONS: dict[PhaseStatus, set[PhaseStatus]] = {
    PhaseStatus.PLANNED: {PhaseStatus.READY},
    PhaseStatus.READY: {PhaseStatus.IN_PROGRESS, PhaseStatus.CANCELLED},
    PhaseStatus.IN_PROGRESS: {
        PhaseStatus.DONE,
        PhaseStatus.NEEDS_REVIEW,
        PhaseStatus.BLOCKED,
        PhaseStatus.CANCELLED,
    },
    PhaseStatus.BLOCKED: {PhaseStatus.READY},
    PhaseStatus.NEEDS_REVIEW: {PhaseStatus.READY},
    PhaseStatus.DONE: set(),
    PhaseStatus.CANCELLED: set(),
}


def can_transition(from_status: PhaseStatus, to_status: PhaseStatus) -> bool:
    """Return True when the state transition is allowed."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


def transition_phase(
    phase: PhaseRow,
    to_status: PhaseStatus,
    *,
    lease_acquired: bool = False,
    approval_satisfied: bool = False,
    validation_passed: bool = False,
    blocker: str | None = None,
    validation_summary: dict | None = None,
    reason_text: str = "",
) -> PhaseRow:
    """Apply a validated state transition to a phase row."""
    if not can_transition(phase.status, to_status):
        raise TransitionError(f"invalid transition: {phase.status} -> {to_status}")

    if to_status == PhaseStatus.READY:
        if (
            not phase.execution_prompt.strip()
            or not phase.validation_commands
            or not phase.done_criteria
        ):
            raise TransitionError("Ready requires prompt, validation commands, and done criteria")

    if to_status == PhaseStatus.IN_PROGRESS:
        if not lease_acquired:
            raise TransitionError("In Progress requires an acquired lease")
        if phase.approval_required and not approval_satisfied:
            raise TransitionError("In Progress requires approval when policy requires it")

    if to_status == PhaseStatus.DONE and not validation_passed:
        raise TransitionError("Done requires successful validation gates")

    if to_status == PhaseStatus.BLOCKED:
        if not blocker:
            raise TransitionError("Blocked requires a blocker reason")
        if validation_summary is None:
            raise TransitionError("Blocked requires validation summary")
        phase.blocker = blocker
        phase.validation_summary = validation_summary

    if to_status == PhaseStatus.CANCELLED and not reason_text.strip():
        raise TransitionError("Cancelled must include explicit reason text")

    if to_status != PhaseStatus.BLOCKED:
        phase.blocker = None

    phase.status = to_status
    return phase
