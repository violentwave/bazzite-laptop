"""MCP Policy-as-Code module for P127.

This module provides:
- Canonical tool policy metadata model
- Policy evaluation engine with default-deny semantics
- Approval gate enforcement
- Audit event generation

It integrates with:
- Security Autopilot (P120) policy modes
- Safe Remediation Runner (P122) approval semantics
- MCP bridge allowlist/governance
"""

from ai.mcp_bridge.policy.approval import (
    ApprovalGate,
    ApprovalGateError,
    ApprovalGateResult,
    enforce_policy_and_approval,
    get_approval_gate,
    map_policy_mode_to_approval,
)
from ai.mcp_bridge.policy.engine import (
    MCPToolPolicyEngine,
    evaluate_tool_policy,
    get_policy_engine,
)
from ai.mcp_bridge.policy.models import (
    DEFAULT_DENY_METADATA,
    ApprovalMetadata,
    PolicyDecision,
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicySource,
    RiskTier,
    ToolPolicyMetadata,
)

__all__ = [
    "ApprovalMetadata",
    "ApprovalGate",
    "ApprovalGateError",
    "ApprovalGateResult",
    "DEFAULT_DENY_METADATA",
    "MCPToolPolicyEngine",
    "PolicyDecision",
    "PolicyEvaluationRequest",
    "PolicyEvaluationResult",
    "PolicySource",
    "RiskTier",
    "ToolPolicyMetadata",
    "evaluate_tool_policy",
    "enforce_policy_and_approval",
    "get_approval_gate",
    "get_policy_engine",
    "map_policy_mode_to_approval",
]
