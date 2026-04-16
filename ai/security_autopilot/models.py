"""Typed models for Security Autopilot core objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class Severity(StrEnum):
    """Normalized severity scale for findings/incidents."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    """Lifecycle state for an incident."""

    OPEN = "open"
    TRIAGE = "triage"
    PLAN_READY = "plan-ready"
    CLOSED = "closed"


class DecisionOutcome(StrEnum):
    """Autopilot outcomes for policy-safe operation."""

    PLAN_ONLY = "plan-only"
    MANUAL_REVIEW = "manual-review"
    NO_ACTION = "no-action"


@dataclass
class SecurityFinding:
    """Normalized security finding derived from one or more sensors."""

    finding_id: str
    title: str
    description: str
    severity: Severity
    category: str
    source: str
    detected_at: str = field(default_factory=_utc_now)
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            msg = "confidence must be between 0.0 and 1.0"
            raise ValueError(msg)


@dataclass
class SecurityIncident:
    """Clustered incident composed of one or more related findings."""

    incident_id: str
    title: str
    severity: Severity
    status: IncidentStatus
    findings: list[SecurityFinding]
    summary: str
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    tags: list[str] = field(default_factory=list)


@dataclass
class RemediationAction:
    """A non-destructive action candidate within a remediation plan."""

    action_id: str
    title: str
    description: str
    tool: str | None = None
    automated: bool = False
    destructive: bool = False
    requires_approval: bool = True

    def __post_init__(self) -> None:
        if self.destructive:
            msg = "destructive remediation is not permitted in Security Autopilot P119"
            raise ValueError(msg)


@dataclass
class RemediationPlan:
    """Plan-only remediation output for manual or policy-gated execution."""

    plan_id: str
    incident_id: str
    priority: Severity
    summary: str
    actions: list[RemediationAction]
    safety_constraints: list[str]
    execution_mode: str = "plan-only"
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.execution_mode != "plan-only":
            msg = "execution_mode must remain 'plan-only' in P119"
            raise ValueError(msg)


@dataclass
class AutopilotDecision:
    """Policy-facing decision generated from incident + plan state."""

    decision_id: str
    incident_id: str
    outcome: DecisionOutcome
    rationale: str
    policy_flags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)


@dataclass
class AuditEvent:
    """Append-only audit record for autopilot activity."""

    event_id: str
    event_type: str
    actor: str
    payload: dict[str, Any]
    incident_id: str | None = None
    evidence_bundle_id: str | None = None
    created_at: str = field(default_factory=_utc_now)
    prev_hash: str = ""
    event_hash: str = ""


@dataclass
class EvidenceItem:
    """Single evidence item after sanitization and normalization."""

    item_id: str
    key: str
    value: Any
    redacted: bool = False


@dataclass
class EvidenceBundle:
    """Redacted evidence package attached to findings/incidents."""

    bundle_id: str
    source: str
    items: list[EvidenceItem]
    redaction_count: int
    created_at: str = field(default_factory=_utc_now)


def as_payload(obj: Any) -> dict[str, Any]:
    """Convert a dataclass object to JSON-safe dictionary."""

    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    msg = "as_payload expects a dataclass instance"
    raise TypeError(msg)


def next_id(prefix: str) -> str:
    """Generate deterministic-shaped IDs with a UUID4 suffix."""

    return f"{prefix}-{uuid4()}"
