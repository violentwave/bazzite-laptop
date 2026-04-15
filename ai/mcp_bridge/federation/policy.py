"""Federation policy evaluation for P105.

Evaluates policies for external MCP server interactions
without bypassing local governance or executing untrusted code.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.mcp_bridge.federation.models import (
    CapabilityMap,
    FederationAuditEntry,
    FederationPolicyResult,
    PolicyDecision,
    TrustScore,
)

logger = logging.getLogger("ai.mcp_bridge.federation.policy")


class FederationPolicy:
    """Evaluates federation policies for external servers.

    Default-deny policy: remote execution requires explicit safety gates.
    """

    def __init__(self, allow_remote_execution: bool = False):
        """Initialize policy.

        Args:
            allow_remote_execution: Whether to allow remote tool execution
        """
        self._allow_remote_execution = allow_remote_execution

    def evaluate_action(
        self,
        server_id: str,
        action: str,
        trust_score: TrustScore | None = None,
        capability_map: CapabilityMap | None = None,
    ) -> FederationPolicyResult:
        """Evaluate policy for federation action.

        Args:
            server_id: Server identifier
            action: Action to evaluate
            trust_score: Optional trust score
            capability_map: Optional capability map

        Returns:
            Policy result
        """
        reasons = []
        decision = PolicyDecision.DENY

        if trust_score:
            if trust_score.overall_score < 20:
                reasons.append(f"Low trust score: {trust_score.overall_score}")
                decision = PolicyDecision.QUARANTINE
            elif trust_score.overall_score < 40:
                reasons.append(f"Medium trust score: {trust_score.overall_score}")
                decision = PolicyDecision.AUDIT
            elif trust_score.overall_score >= 70:
                if self._allow_remote_execution:
                    decision = PolicyDecision.ALLOW
                    reasons.append("High trust score and remote execution allowed")
                else:
                    decision = PolicyDecision.ALLOW
                    reasons.append("High trust score")

        if capability_map and decision != PolicyDecision.DENY:
            if capability_map.has_destructive_tools:
                reasons.append("Server has destructive tools")
                decision = PolicyDecision.AUDIT

            if capability_map.has_system_tools:
                reasons.append("Server has system tools")
                decision = PolicyDecision.DENY

        if action in ("execute", "proxy"):
            if not self._allow_remote_execution:
                decision = PolicyDecision.DENY
                reasons.append("Remote execution is disabled")

        if not reasons:
            reasons.append("Default deny policy")

        result = FederationPolicyResult(
            server_id=server_id,
            action=action,
            decision=decision,
            reasons=reasons,
            conditions={"allow_remote": self._allow_remote_execution},
        )

        logger.info(f"Policy decision for {server_id}/{action}: {decision.value}")

        return result

    def check_tool_execution(
        self,
        server_id: str,
        tool_name: str,
        trust_score: TrustScore | None = None,
    ) -> tuple[bool, str]:
        """Check if tool execution is allowed.

        Args:
            server_id: Server identifier
            tool_name: Tool name
            trust_score: Optional trust score

        Returns:
            Tuple of (allowed, reason)
        """
        if not self._allow_remote_execution:
            return False, "Remote execution is disabled by policy"

        if trust_score and trust_score.overall_score < 50:
            return False, f"Trust score too low: {trust_score.overall_score}"

        if tool_name.startswith(("system.", "security.", "shell.")):
            return False, "System tools cannot be executed remotely"

        return True, "Allowed"


class FederationAuditor:
    """Audits federation actions."""

    def __init__(self):
        self._audit_log: list[FederationAuditEntry] = []

    def log_action(
        self,
        server_id: str,
        action: str,
        decision: PolicyDecision,
        reasons: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FederationAuditEntry:
        """Log federation action.

        Args:
            server_id: Server identifier
            action: Action performed
            decision: Policy decision
            reasons: Optional reasons
            metadata: Optional metadata

        Returns:
            Audit entry
        """
        entry = FederationAuditEntry(
            server_id=server_id,
            action=action,
            decision=decision,
            reasons=reasons or [],
            metadata=metadata or {},
        )

        self._audit_log.append(entry)
        logger.info(f"Audit: {server_id}/{action} -> {decision.value}")

        return entry

    def get_audit_log(
        self,
        server_id: str | None = None,
        limit: int = 100,
    ) -> list[FederationAuditEntry]:
        """Get audit log entries.

        Args:
            server_id: Optional server filter
            limit: Maximum entries

        Returns:
            Audit entries
        """
        entries = self._audit_log

        if server_id:
            entries = [e for e in entries if e.server_id == server_id]

        return entries[-limit:]
