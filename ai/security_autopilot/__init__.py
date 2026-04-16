"""Security Autopilot core package (P119).

This package is intentionally plan-only. It normalizes security signals,
classifies findings, groups incidents, produces remediation plans, and records
auditable evidence without executing destructive remediation actions.
"""

from ai.security_autopilot.audit import AuditLedger, EvidenceManager
from ai.security_autopilot.classifier import FindingClassifier
from ai.security_autopilot.models import (
    AuditEvent,
    AutopilotDecision,
    EvidenceBundle,
    EvidenceItem,
    RemediationAction,
    RemediationPlan,
    SecurityFinding,
    SecurityIncident,
)
from ai.security_autopilot.planner import RemediationPlanner
from ai.security_autopilot.sensors import BazziteSensorAdapter, SensorSnapshot

__all__ = [
    "AuditEvent",
    "AuditLedger",
    "AutopilotDecision",
    "BazziteSensorAdapter",
    "EvidenceBundle",
    "EvidenceItem",
    "EvidenceManager",
    "FindingClassifier",
    "RemediationAction",
    "RemediationPlan",
    "RemediationPlanner",
    "SecurityFinding",
    "SecurityIncident",
    "SensorSnapshot",
]
