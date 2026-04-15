"""Federation Module for P105.

Provides safe external MCP server federation with read-only discovery,
trust scoring, policy evaluation, and auditing.

Key features:
- Read-only discovery without executing remote code
- Trust scoring based on server characteristics
- Policy evaluation with default-deny
- Audit logging for all federation actions
"""

from ai.mcp_bridge.federation.discovery import (
    DiscoveryError,
    ExternalServerDiscovery,
)
from ai.mcp_bridge.federation.models import (
    CapabilityMap,
    ExternalServerIdentity,
    ExternalToolDefinition,
    FederationAuditEntry,
    FederationPolicyResult,
    FederationServerRecord,
    PolicyDecision,
    ServerCapability,
    ServerToolManifest,
    TrustScore,
    TrustState,
)
from ai.mcp_bridge.federation.policy import FederationAuditor, FederationPolicy
from ai.mcp_bridge.federation.trust import TrustScorer

__all__ = [
    "CapabilityMap",
    "DiscoveryError",
    "ExternalServerDiscovery",
    "ExternalServerIdentity",
    "ExternalToolDefinition",
    "FederationAuditor",
    "FederationAuditEntry",
    "FederationPolicy",
    "FederationPolicyResult",
    "FederationServerRecord",
    "PolicyDecision",
    "ServerCapability",
    "ServerToolManifest",
    "TrustScorer",
    "TrustScore",
    "TrustState",
]
