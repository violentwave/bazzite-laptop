"""Policy checks for phase-control guardrails and approval gating."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.phase_control.models import PhaseRow
from ai.phase_control.result_models import ValidationSummary


@dataclass
class PolicyEvent:
    """Single policy event emitted during checks."""

    code: str
    message: str


@dataclass
class PolicyDecision:
    """Result from a policy check."""

    allowed: bool
    events: list[PolicyEvent] = field(default_factory=list)


def check_ready_requirements(phase: PhaseRow) -> PolicyDecision:
    """Ready requires prompt, validation commands, and done criteria."""
    events: list[PolicyEvent] = []
    if not phase.execution_prompt.strip():
        events.append(PolicyEvent(code="missing_prompt", message="execution prompt is required"))
    if not phase.validation_commands:
        events.append(
            PolicyEvent(
                code="missing_validation_commands",
                message="validation commands are required",
            )
        )
    if not phase.done_criteria:
        events.append(
            PolicyEvent(code="missing_done_criteria", message="done criteria are required")
        )
    return PolicyDecision(allowed=len(events) == 0, events=events)


def check_approval(phase: PhaseRow) -> PolicyDecision:
    """Approval check for transitions that need explicit authorization."""
    if not phase.approval_required:
        return PolicyDecision(allowed=True)
    if phase.approval_granted:
        return PolicyDecision(allowed=True)
    return PolicyDecision(
        allowed=False,
        events=[
            PolicyEvent(
                code="approval_required",
                message="approval is required before entering In Progress",
            )
        ],
    )


def check_done_validation(summary: ValidationSummary) -> PolicyDecision:
    """Done gate requires all required validations to pass."""
    if summary.passed:
        return PolicyDecision(allowed=True)
    return PolicyDecision(
        allowed=False,
        events=[
            PolicyEvent(
                code="validation_failed",
                message="required validation gates failed",
            )
        ],
    )


def check_preflight_gate(preflight: dict) -> PolicyDecision:
    """Execution preflight gate; blocks when preflight marks execution unsafe."""
    gate = preflight.get("gate", {}) if isinstance(preflight, dict) else {}
    if gate.get("allowed", False):
        warnings = gate.get("warnings", [])
        return PolicyDecision(
            allowed=True,
            events=[
                PolicyEvent(code="preflight_warning", message=str(warning))
                for warning in warnings[:10]
            ],
        )

    blockers = gate.get("blockers", [])
    if not blockers:
        blockers = ["preflight_blocked"]
    return PolicyDecision(
        allowed=False,
        events=[
            PolicyEvent(code="preflight_blocked", message=str(blocker)) for blocker in blockers[:10]
        ],
    )
