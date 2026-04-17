"""MCP policy approval gates for P127.

This module enforces approval gates before high-risk tools execute,
integrating with Security Autopilot (P120) and Safe Remediation Runner (P122) semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ai.mcp_bridge.policy.models import (
    ApprovalMetadata,
    PolicyDecision,
    PolicyEvaluationResult,
)
from ai.security_autopilot.policy import PolicyMode as SAPolicyMode


class ApprovalGateError(Exception):
    """Error raised when approval gate rejects an action."""

    pass


@dataclass
class ApprovalGateResult:
    """Result of approval gate evaluation."""

    allowed: bool
    approval: ApprovalMetadata | None = None
    policy_result: PolicyEvaluationResult | None = None
    error: str | None = None
    decision_id: str | None = None


class ApprovalGate:
    """Enforces approval gates for high-risk MCP tool invocations."""

    def __init__(self, policy_mode: str = "recommend_only"):
        self.policy_mode = policy_mode
        self._pending_approvals: dict[str, ApprovalMetadata] = {}

    def check_approval(
        self,
        policy_result: PolicyEvaluationResult,
        approval: ApprovalMetadata | None = None,
    ) -> ApprovalGateResult:
        """Check if tool invocation is approved based on policy decision."""
        if policy_result.decision == PolicyDecision.ALLOW:
            return ApprovalGateResult(
                allowed=True,
                policy_result=policy_result,
                decision_id=policy_result.audit_id,
            )

        if policy_result.decision == PolicyDecision.DENY:
            return ApprovalGateResult(
                allowed=False,
                policy_result=policy_result,
                error=f"Tool '{policy_result.tool_name}' denied by policy: {policy_result.reason}",
                decision_id=policy_result.audit_id,
            )

        if policy_result.decision == PolicyDecision.APPROVAL_REQUIRED:
            if approval is None:
                return ApprovalGateResult(
                    allowed=False,
                    policy_result=policy_result,
                    error=f"Tool '{policy_result.tool_name}' requires approval. "
                    "No approval metadata provided.",
                    decision_id=policy_result.audit_id,
                )

            if not approval.approved:
                return ApprovalGateResult(
                    allowed=False,
                    policy_result=policy_result,
                    approval=approval,
                    error=f"Tool '{policy_result.tool_name}' approval rejected: "
                    f"{approval.reason or 'not approved'}",
                    decision_id=policy_result.audit_id,
                )

            if not approval.approver:
                return ApprovalGateResult(
                    allowed=False,
                    policy_result=policy_result,
                    approval=approval,
                    error="Approval missing approver identity",
                    decision_id=policy_result.audit_id,
                )

            if policy_result.risk_tier.value in ("high", "critical"):
                if not approval.ticket and not approval.phase_reference:
                    return ApprovalGateResult(
                        allowed=False,
                        policy_result=policy_result,
                        approval=approval,
                        error="High-risk tool requires ticket or phase reference for approval",
                        decision_id=policy_result.audit_id,
                    )

            return ApprovalGateResult(
                allowed=True,
                policy_result=policy_result,
                approval=approval,
                decision_id=policy_result.audit_id,
            )

        return ApprovalGateResult(
            allowed=False,
            policy_result=policy_result,
            error=f"Unknown policy decision: {policy_result.decision}",
            decision_id=policy_result.audit_id,
        )

    def create_pending_approval(self, tool_name: str, reason: str = "") -> str:
        """Create a pending approval request and return approval ID."""
        approval_id = f"approval-{tool_name}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        self._pending_approvals[approval_id] = ApprovalMetadata(
            approved=False,
            approver="",
            reason=reason,
        )
        return approval_id

    def approve(
        self,
        approval_id: str,
        approver: str,
        reason: str = "",
        ticket: str | None = None,
        phase_reference: str | None = None,
    ) -> bool:
        """Approve a pending approval request."""
        if approval_id not in self._pending_approvals:
            return False

        approval = self._pending_approvals[approval_id]
        approval.approved = True
        approval.approver = approver
        approval.approved_at = datetime.now(UTC)
        approval.reason = reason
        approval.ticket = ticket
        approval.phase_reference = phase_reference
        approval.decision_id = approval_id
        return True

    def reject(self, approval_id: str, reason: str = "") -> bool:
        """Reject a pending approval request."""
        if approval_id not in self._pending_approvals:
            return False

        approval = self._pending_approvals[approval_id]
        approval.approved = False
        approval.reason = reason
        return True

    def get_pending(self, approval_id: str) -> ApprovalMetadata | None:
        """Get pending approval metadata."""
        return self._pending_approvals.get(approval_id)


def map_policy_mode_to_approval(security_autopilot_mode: str | SAPolicyMode) -> str:
    """Map Security Autopilot policy mode to MCP policy mode."""
    if isinstance(security_autopilot_mode, SAPolicyMode):
        security_autopilot_mode = security_autopilot_mode.value

    mode_map = {
        "monitor_only": "monitor_only",
        "recommend_only": "recommend_only",
        "safe_auto": "safe_auto",
        "approval_required": "approval_required",
        "lockdown": "lockdown",
    }
    return mode_map.get(security_autopilot_mode, "recommend_only")


# Global approval gate instance
_approval_gate: ApprovalGate | None = None


def get_approval_gate(policy_mode: str = "recommend_only") -> ApprovalGate:
    """Get or create global approval gate instance."""
    global _approval_gate
    if _approval_gate is None:
        _approval_gate = ApprovalGate(policy_mode=policy_mode)
    return _approval_gate


def enforce_policy_and_approval(
    tool_name: str,
    arguments: dict | None = None,
    approval: ApprovalMetadata | None = None,
    mode: str = "recommend_only",
) -> ApprovalGateResult:
    """Convenience function to evaluate policy and check approval in one call."""
    from ai.mcp_bridge.policy.engine import evaluate_tool_policy

    policy_result = evaluate_tool_policy(
        tool_name=tool_name,
        arguments=arguments,
        mode=mode,
    )

    gate = get_approval_gate(policy_mode=mode)
    return gate.check_approval(policy_result, approval)
