"""Plan-only remediation planning for Security Autopilot."""

from __future__ import annotations

from ai.security_autopilot.models import (
    AutopilotDecision,
    DecisionOutcome,
    IncidentStatus,
    RemediationAction,
    RemediationPlan,
    SecurityIncident,
    Severity,
    next_id,
)


class RemediationPlanner:
    """Generate non-destructive remediation plans from incidents."""

    GLOBAL_CONSTRAINTS = [
        "No destructive execution in autopilot mode",
        "All mutating steps require explicit operator approval",
        "Only allowlisted system and security tools may be referenced",
        "Evidence must be redacted before storage or sharing",
    ]

    def build_plan(self, incident: SecurityIncident) -> RemediationPlan:
        actions = self._actions_for_incident(incident)
        return RemediationPlan(
            plan_id=next_id("plan"),
            incident_id=incident.incident_id,
            priority=incident.severity,
            summary=f"Plan-only remediation for incident '{incident.title}'",
            actions=actions,
            safety_constraints=self.GLOBAL_CONSTRAINTS,
            execution_mode="plan-only",
        )

    def build_decision(
        self, incident: SecurityIncident, plan: RemediationPlan
    ) -> AutopilotDecision:
        if not plan.actions:
            return AutopilotDecision(
                decision_id=next_id("decision"),
                incident_id=incident.incident_id,
                outcome=DecisionOutcome.NO_ACTION,
                rationale="No actions generated; monitor incident for additional signals",
                policy_flags=["plan-empty", "manual-monitoring"],
            )

        outcome = (
            DecisionOutcome.MANUAL_REVIEW
            if incident.severity in {Severity.HIGH, Severity.CRITICAL}
            else DecisionOutcome.PLAN_ONLY
        )
        rationale = (
            "High-risk incident requires manual operator review before any execution"
            if outcome == DecisionOutcome.MANUAL_REVIEW
            else "Low/medium risk incident can remain in plan-only queue"
        )

        return AutopilotDecision(
            decision_id=next_id("decision"),
            incident_id=incident.incident_id,
            outcome=outcome,
            rationale=rationale,
            policy_flags=["no-destructive-remediation", "approval-required"],
        )

    def _actions_for_incident(self, incident: SecurityIncident) -> list[RemediationAction]:
        actions = [
            RemediationAction(
                action_id=next_id("action"),
                title="Collect latest status context",
                description="Refresh security.status and security.alert_summary snapshots",
                tool="security.status",
                automated=True,
                requires_approval=False,
            ),
            RemediationAction(
                action_id=next_id("action"),
                title="Review linked evidence",
                description="Inspect redacted evidence bundle before operator triage",
                tool=None,
                automated=False,
                requires_approval=True,
            ),
        ]

        categories = {finding.category for finding in incident.findings}

        if "vulnerability" in categories:
            actions.append(
                RemediationAction(
                    action_id=next_id("action"),
                    title="Validate package updates",
                    description="Check Fedora security updates and dependency audit details",
                    tool="system.fedora_updates",
                    automated=True,
                    requires_approval=False,
                )
            )

        if "threat" in categories or "anomaly" in categories:
            actions.append(
                RemediationAction(
                    action_id=next_id("action"),
                    title="Prepare containment checklist",
                    description="Draft manual containment checklist; do not isolate automatically",
                    tool="security.recommend_action",
                    automated=True,
                    requires_approval=True,
                )
            )

        if "operations" in categories:
            actions.append(
                RemediationAction(
                    action_id=next_id("action"),
                    title="Review service/timer drift",
                    description="Collect service and timer health for operator action",
                    tool="agents.timer_health",
                    automated=True,
                    requires_approval=False,
                )
            )

        if incident.status == IncidentStatus.TRIAGE:
            actions.append(
                RemediationAction(
                    action_id=next_id("action"),
                    title="Escalate to manual triage",
                    description="Assign incident owner and track operator acknowledgement",
                    tool=None,
                    automated=False,
                    requires_approval=True,
                )
            )

        return actions
