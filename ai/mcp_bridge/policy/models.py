"""Canonical MCP tool policy model for P127.

This module provides a unified policy layer for MCP tools that aligns with
Security Autopilot (P120) and Safe Remediation Runner (P122) semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RiskTier(StrEnum):
    """Risk tier classification for MCP tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecision(StrEnum):
    """Policy decision outcomes."""

    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"


class PolicySource(StrEnum):
    """Source of policy rules."""

    ALLOWLIST = "allowlist"
    GOVERNANCE = "governance"
    SECURITY_AUTOPILOT = "security_autopilot"
    EXPLICIT = "explicit"
    DEFAULT_DENY = "default_deny"


@dataclass
class ApprovalMetadata:
    """Approval metadata for high-risk tool invocations."""

    approved: bool = False
    approver: str = ""
    approved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""
    ticket: str | None = None
    phase_reference: str | None = None
    decision_id: str | None = None


@dataclass
class ToolPolicyMetadata:
    """Canonical policy metadata for MCP tools."""

    tool_name: str
    namespace: str = ""
    risk_tier: RiskTier = RiskTier.LOW
    requires_approval: bool = False
    destructive: bool = False
    secret_access: bool = False
    shell_access: bool = False
    network_access: bool = False
    provider_mutation: bool = False
    filesystem_scope: str = ""  # empty = no filesystem access
    allowed_modes: list[str] = field(default_factory=list)
    audit_required: bool = True
    rationale: str = ""
    policy_source: PolicySource = PolicySource.ALLOWLIST
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PolicyEvaluationRequest:
    """Input for policy evaluation."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    actor: str = "mcp_bridge"
    mode: str = "recommend_only"  # matches P120 PolicyMode


@dataclass
class PolicyEvaluationResult:
    """Output from policy evaluation."""

    tool_name: str
    decision: PolicyDecision
    risk_tier: RiskTier
    requires_approval: bool
    reason: str
    policy_source: PolicySource
    audit_id: str | None = None
    redacted: bool = True
    metadata: ToolPolicyMetadata | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# Default policy metadata for unknown tools (default-deny)
DEFAULT_DENY_METADATA = ToolPolicyMetadata(
    tool_name="__unknown__",
    risk_tier=RiskTier.CRITICAL,
    requires_approval=True,
    destructive=False,
    secret_access=False,
    shell_access=False,
    network_access=False,
    provider_mutation=False,
    filesystem_scope="",
    allowed_modes=[],
    audit_required=True,
    rationale="Tool not found in policy registry - default deny",
    policy_source=PolicySource.DEFAULT_DENY,
)
