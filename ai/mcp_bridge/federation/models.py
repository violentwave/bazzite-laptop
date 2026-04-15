"""Federation models for P105.

Defines models for external MCP server identity, tool manifests,
trust state, capability maps, and policy results.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TrustState(StrEnum):
    """Trust state for external MCP server."""

    UNKNOWN = "unknown"
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPECTED = "suspected"
    BLOCKED = "blocked"


class ServerCapability(StrEnum):
    """Capabilities of an MCP server."""

    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    LOGGING = "logging"


class PolicyDecision(StrEnum):
    """Policy decision for federation action."""

    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"
    QUARANTINE = "quarantine"


class ExternalServerIdentity(BaseModel):
    """Identity information for external MCP server."""

    server_id: str
    name: str
    version: str = "1.0.0"
    url: str
    description: str = ""
    capabilities: list[ServerCapability] = Field(default_factory=list)
    trust_state: TrustState = TrustState.UNKNOWN
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    last_verified: datetime | None = None


class ExternalToolDefinition(BaseModel):
    """Tool definition from external MCP server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)


class ServerToolManifest(BaseModel):
    """Tool manifest from external MCP server."""

    server_id: str
    tools: list[ExternalToolDefinition] = Field(default_factory=list)
    resource_templates: list[dict[str, Any]] = Field(default_factory=list)
    prompt_templates: list[dict[str, Any]] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class CapabilityMap(BaseModel):
    """Capability map for external server."""

    server_id: str
    tools_count: int = 0
    resources_count: int = 0
    prompts_count: int = 0
    has_destructive_tools: bool = False
    has_system_tools: bool = False
    network_access: bool = False
    file_access: bool = False


class TrustScore(BaseModel):
    """Trust score for external MCP server."""

    server_id: str
    overall_score: float = Field(ge=0, le=100)
    factors: dict[str, float] = Field(default_factory=dict)
    last_calculated: datetime = Field(default_factory=datetime.utcnow)


class FederationPolicyResult(BaseModel):
    """Result of policy evaluation for federation action."""

    server_id: str
    action: str
    decision: PolicyDecision
    reasons: list[str] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class FederationAuditEntry(BaseModel):
    """Audit entry for federation actions."""

    id: str = Field(default_factory=lambda: f"audit_{datetime.utcnow().timestamp()}")
    server_id: str
    action: str
    decision: PolicyDecision
    actor: str = "system"
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FederationServerRecord(BaseModel):
    """Complete record for external MCP server."""

    identity: ExternalServerIdentity
    manifest: ServerToolManifest | None = None
    capability_map: CapabilityMap | None = None
    trust_score: TrustScore | None = None
    audit_history: list[FederationAuditEntry] = Field(default_factory=list)
