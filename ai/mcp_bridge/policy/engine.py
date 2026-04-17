"""MCP policy evaluation engine for P127.

This module provides a single policy evaluation path for MCP tool calls,
integrating with Security Autopilot (P120) and Safe Remediation Runner (P122).
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import yaml

from ai.config import CONFIGS_DIR
from ai.mcp_bridge.policy.models import (
    DEFAULT_DENY_METADATA,
    PolicyDecision,
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicySource,
    RiskTier,
    ToolPolicyMetadata,
)

DEFAULT_ALLOWLIST_PATH = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"


class MCPToolPolicyEngine:
    """Canonical policy evaluation for MCP tools."""

    def __init__(self, allowlist_path: Path | None = None):
        self.allowlist_path = allowlist_path or DEFAULT_ALLOWLIST_PATH
        self._tool_metadata_cache: dict[str, ToolPolicyMetadata] = {}
        self._allowlist_config: dict | None = None
        self._load_allowlist()

    def _load_allowlist(self) -> None:
        """Load and cache allowlist configuration."""
        with self.allowlist_path.open(encoding="utf-8") as f:
            self._allowlist_config = yaml.safe_load(f) or {}

        tools = self._allowlist_config.get("tools", {})
        for tool_name, tool_def in tools.items():
            self._tool_metadata_cache[tool_name] = self._extract_metadata(tool_name, tool_def)

    def _extract_metadata(self, tool_name: str, tool_def: dict) -> ToolPolicyMetadata:
        """Extract policy metadata from allowlist tool definition."""
        risk_tier = RiskTier.LOW
        requires_approval = False
        destructive = False
        secret_access = False
        shell_access = False
        network_access = False
        filesystem_scope = ""

        description = tool_def.get("description", "").lower()
        command = tool_def.get("command", [])
        source = tool_def.get("source", "")

        if any(x in description for x in ["write", "delete", "remove", "modify"]):
            destructive = True
            risk_tier = RiskTier.HIGH

        if any(x in description for x in ["secret", "key", "token", "password", "credential"]):
            secret_access = True
            risk_tier = RiskTier.HIGH

        if command and any(c in ["rm", "del", "shutdown", "reboot", "systemctl"] for c in command):
            destructive = True
            risk_tier = RiskTier.CRITICAL

        if source == "python" and "security" in tool_name:
            risk_tier = RiskTier.MEDIUM
            audit_required = True

        if "scan" in tool_name or "scan" in description:
            destructive = True
            risk_tier = RiskTier.HIGH

        if "sandbox" in tool_name or "quarantine" in tool_name:
            destructive = True
            risk_tier = RiskTier.HIGH
            requires_approval = True

        if source == "shell":
            shell_access = True
            risk_tier = RiskTier.MEDIUM

        if any(x in tool_name for x in ["network", "http", "request", "fetch", "curl", "wget"]):
            network_access = True

        if any(x in tool_name for x in ["provider", "settings", "config"]) and any(
            x in description for x in ["update", "set", "change", "modify"]
        ):
            requires_approval = True
            risk_tier = RiskTier.HIGH

        if any(x in tool_name for x in ["secret", "key", "credential"]):
            secret_access = True
            requires_approval = True
            risk_tier = RiskTier.HIGH

        if destructive or requires_approval or secret_access:
            audit_required = True

        if command and source == "shell":
            filesystem_scope = "limited"

        return ToolPolicyMetadata(
            tool_name=tool_name,
            namespace=tool_name.split(".")[0] if "." in tool_name else "",
            risk_tier=risk_tier,
            requires_approval=requires_approval,
            destructive=destructive,
            secret_access=secret_access,
            shell_access=shell_access,
            network_access=network_access,
            filesystem_scope=filesystem_scope,
            allowed_modes=["recommend_only", "approval_required", "safe_auto"],
            audit_required=audit_required if "audit_required" in dir() else True,
            rationale=f"Extracted from allowlist: {description[:100]}",
            policy_source=PolicySource.ALLOWLIST,
        )

    def _generate_audit_id(self, tool_name: str) -> str:
        """Generate unique audit ID for policy decision."""
        unique_str = f"{tool_name}:{uuid.uuid4().hex[:12]}"
        return f"pol-{hashlib.sha256(unique_str.encode()).hexdigest()[:16]}"

    def _check_alias_bypass(self, tool_name: str, arguments: dict) -> bool:
        """Check for alias/namespace bypass attempts."""
        if "alias" in arguments or "alternate_name" in arguments:
            return True

        if "__" in tool_name or tool_name.startswith("_"):
            return True

        for key in arguments:
            if key.startswith("_") or key.endswith("_alias"):
                return True

        return False

    def evaluate(self, request: PolicyEvaluationRequest) -> PolicyEvaluationResult:
        """Evaluate policy for a tool invocation."""
        tool_name = request.tool_name

        if self._check_alias_bypass(tool_name, request.arguments):
            return PolicyEvaluationResult(
                tool_name=tool_name,
                decision=PolicyDecision.DENY,
                risk_tier=RiskTier.CRITICAL,
                requires_approval=True,
                reason="Alias or namespace bypass attempt detected",
                policy_source=PolicySource.DEFAULT_DENY,
                audit_id=self._generate_audit_id(tool_name),
                redacted=True,
            )

        metadata = self._tool_metadata_cache.get(tool_name)
        if metadata is None:
            return PolicyEvaluationResult(
                tool_name=tool_name,
                decision=PolicyDecision.DENY,
                risk_tier=RiskTier.CRITICAL,
                requires_approval=True,
                reason="Tool not found in allowlist - default deny",
                policy_source=PolicySource.DEFAULT_DENY,
                audit_id=self._generate_audit_id(tool_name),
                redacted=True,
                metadata=DEFAULT_DENY_METADATA,
            )

        mode = request.mode
        if mode == "lockdown":
            return PolicyEvaluationResult(
                tool_name=tool_name,
                decision=PolicyDecision.DENY,
                risk_tier=metadata.risk_tier,
                requires_approval=True,
                reason="Tool denied in lockdown mode",
                policy_source=PolicySource.EXPLICIT,
                audit_id=self._generate_audit_id(tool_name),
                redacted=True,
                metadata=metadata,
            )

        if metadata.destructive and request.mode != "safe_auto":
            return PolicyEvaluationResult(
                tool_name=tool_name,
                decision=PolicyDecision.APPROVAL_REQUIRED,
                risk_tier=metadata.risk_tier,
                requires_approval=True,
                reason=f"Destructive tool '{tool_name}' requires approval in {request.mode} mode",
                policy_source=PolicySource.SECURITY_AUTOPILOT,
                audit_id=self._generate_audit_id(tool_name),
                redacted=True,
                metadata=metadata,
            )

        if metadata.requires_approval:
            return PolicyEvaluationResult(
                tool_name=tool_name,
                decision=PolicyDecision.APPROVAL_REQUIRED,
                risk_tier=metadata.risk_tier,
                requires_approval=True,
                reason=f"Tool '{tool_name}' requires approval (risk: {metadata.risk_tier.value})",
                policy_source=PolicySource.EXPLICIT,
                audit_id=self._generate_audit_id(tool_name),
                redacted=True,
                metadata=metadata,
            )

        if metadata.risk_tier in (RiskTier.HIGH, RiskTier.CRITICAL):
            return PolicyEvaluationResult(
                tool_name=tool_name,
                decision=PolicyDecision.APPROVAL_REQUIRED,
                risk_tier=metadata.risk_tier,
                requires_approval=True,
                reason=f"High-risk tool (tier: {metadata.risk_tier.value}) requires approval",
                policy_source=PolicySource.ALLOWLIST,
                audit_id=self._generate_audit_id(tool_name),
                redacted=True,
                metadata=metadata,
            )

        return PolicyEvaluationResult(
            tool_name=tool_name,
            decision=PolicyDecision.ALLOW,
            risk_tier=metadata.risk_tier,
            requires_approval=False,
            reason=f"Tool '{tool_name}' allowed (risk: {metadata.risk_tier.value})",
            policy_source=PolicySource.ALLOWLIST,
            audit_id=self._generate_audit_id(tool_name),
            redacted=True,
            metadata=metadata,
        )

    def get_metadata(self, tool_name: str) -> ToolPolicyMetadata | None:
        """Get policy metadata for a tool."""
        return self._tool_metadata_cache.get(tool_name)

    def list_tools(self) -> list[str]:
        """List all registered tools."""
        return sorted(self._tool_metadata_cache.keys())


# Global policy engine instance
_policy_engine: MCPToolPolicyEngine | None = None


def get_policy_engine() -> MCPToolPolicyEngine:
    """Get or create global policy engine instance."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = MCPToolPolicyEngine()
    return _policy_engine


def evaluate_tool_policy(
    tool_name: str,
    arguments: dict | None = None,
    session_id: str | None = None,
    mode: str = "recommend_only",
) -> PolicyEvaluationResult:
    """Convenience function to evaluate tool policy."""
    engine = get_policy_engine()
    request = PolicyEvaluationRequest(
        tool_name=tool_name,
        arguments=arguments or {},
        session_id=session_id,
        mode=mode,
    )
    return engine.evaluate(request)
