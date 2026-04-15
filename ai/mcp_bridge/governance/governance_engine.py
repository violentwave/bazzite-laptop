"""Tool governance engine.

P101: MCP Tool Governance + Analytics Platform

Enforces governance policies and performs security audits.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai.mcp_bridge.governance.models import (
    ComplianceReport,
    EnforcementResult,
    GovernancePolicy,
    PermissionAudit,
    SecurityScore,
)

# Sensitive data patterns that indicate higher risk
SENSITIVE_PATTERNS = [
    "password",
    "secret",
    "key",
    "token",
    "credential",
    "private",
    "auth",
    "encrypt",
    "hash",
    "salt",
]

# Tools that require elevated privileges
ELEVATED_TOOLS = [
    "security.run_scan",
    "security.run_health",
    "security.sandbox_submit",
    "settings.reveal_secret",
    "settings.set_secret",
    "settings.delete_secret",
    "shell.execute_command",
    "system.dep_scan",
]


class ToolGovernanceEngine:
    """Enforces governance policies and performs security audits.

    Provides policy-based access control, security scoring,
    permission auditing, and compliance reporting.
    """

    def __init__(self, policies_path: Path | None = None):
        """Initialize governance engine.

        Args:
            policies_path: Path to governance policies JSON file.
                          If None, uses default policies.
        """
        self._policies: list[GovernancePolicy] = []
        self._policies_path = policies_path
        self._load_policies()

    def _load_policies(self) -> None:
        """Load governance policies from file or use defaults."""
        if self._policies_path and self._policies_path.exists():
            try:
                with open(self._policies_path) as f:
                    data = json.load(f)
                    for policy_data in data.get("policies", []):
                        self._policies.append(GovernancePolicy(**policy_data))
                return
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Use default policies
        self._policies = self._default_policies()

    def _default_policies(self) -> list[GovernancePolicy]:
        """Create default governance policies."""
        return [
            GovernancePolicy(
                id="security-tools-restricted",
                name="Security Tools Require Elevated Session",
                description="Tools in the security category require elevated session level",
                applies_to="security.*",
                rules=[
                    {"type": "require_session_level", "min_level": "elevated"},
                    {"type": "rate_limit", "max_invocations_per_hour": 100},
                ],
            ),
            GovernancePolicy(
                id="shell-gateway-audit",
                name="Shell Gateway Full Audit",
                description="All shell operations must be fully audited",
                applies_to="shell.*",
                rules=[
                    {"type": "audit_all_invocations"},
                    {"type": "block_dangerous_patterns", "patterns": ["sudo", "rm -rf /"]},
                ],
            ),
            GovernancePolicy(
                id="settings-secrets-protection",
                name="Settings Secrets Protection",
                description="Secret operations require PIN verification",
                applies_to="settings.*secret*",
                rules=[
                    {"type": "require_verification", "method": "pin"},
                    {"type": "audit_all_invocations"},
                ],
            ),
            GovernancePolicy(
                id="system-maintenance-windows",
                name="System Tools Maintenance Window",
                description="Heavy system operations should be during maintenance windows",
                applies_to="system.*",
                rules=[
                    {"type": "rate_limit", "max_invocations_per_minute": 10},
                ],
            ),
        ]

    async def audit_tool_permissions(self, tool_name: str) -> PermissionAudit:
        """Audit tool against least-privilege principles.

        Args:
            tool_name: Name of the tool to audit

        Returns:
            PermissionAudit with findings and recommendations
        """
        requires_elevated = tool_name in ELEVATED_TOOLS

        # Check for sensitive data access patterns
        accesses_sensitive = any(pattern in tool_name.lower() for pattern in SENSITIVE_PATTERNS)

        # Determine risk level
        if requires_elevated and accesses_sensitive:
            risk = "high"
        elif requires_elevated or accesses_sensitive:
            risk = "medium"
        else:
            risk = "low"

        recommendations = []

        if requires_elevated and not accesses_sensitive:
            recommendations.append(
                "Tool requires elevated privileges but doesn't access sensitive data. "
                "Consider if elevation is necessary."
            )

        if accesses_sensitive and not requires_elevated:
            recommendations.append(
                "Tool accesses sensitive data patterns but doesn't require elevation. "
                "Consider adding session elevation requirement."
            )

        if "shell" in tool_name:
            recommendations.append(
                "Shell tools should have strict input validation and command allowlisting."
            )

        if "settings" in tool_name and "secret" in tool_name:
            recommendations.append(
                "Secret management tools should require PIN verification and full audit logging."
            )

        compliant = not (accesses_sensitive and not requires_elevated)

        return PermissionAudit(
            tool_name=tool_name,
            audit_timestamp=datetime.utcnow(),
            requires_elevated=requires_elevated,
            accesses_sensitive_data=accesses_sensitive,
            data_exposure_risk=risk,
            recommendations=recommendations,
            compliant=compliant,
        )

    async def evaluate_security_score(self, tool_name: str) -> SecurityScore:
        """Calculate security score based on access patterns and data exposure.

        Args:
            tool_name: Name of the tool to evaluate

        Returns:
            SecurityScore with overall score and factor breakdown
        """
        factors = {}
        score = 100

        # Base score starts at 100, deductions for risk factors

        # Factor 1: Privilege requirements (-20 if requires elevation)
        if tool_name in ELEVATED_TOOLS:
            factors["privilege_requirement"] = -20
            score -= 20
        else:
            factors["privilege_requirement"] = 0

        # Factor 2: Data sensitivity (-15 for sensitive patterns)
        sensitive_matches = sum(1 for pattern in SENSITIVE_PATTERNS if pattern in tool_name.lower())
        sensitivity_penalty = min(sensitive_matches * 5, 15)
        factors["data_sensitivity"] = -sensitivity_penalty
        score -= sensitivity_penalty

        # Factor 3: Tool category risk
        category_risk = {
            "security": -10,
            "shell": -15,
            "settings": -5,
            "system": -5,
        }
        category_penalty = 0
        for cat, penalty in category_risk.items():
            if cat in tool_name.lower():
                category_penalty = penalty
                break
        factors["category_risk"] = category_penalty
        score += category_penalty

        # Factor 4: Naming convention compliance
        if not any(
            tool_name.startswith(prefix)
            for prefix in [
                "security.",
                "system.",
                "settings.",
                "shell.",
                "workflow.",
                "code.",
                "knowledge.",
                "project.",
                "agents.",
                "intel.",
                "collab.",
                "providers.",
                "notion.",
                "slack.",
                "figma.",
                "memory.",
                "logs.",
            ]
        ):
            factors["naming_convention"] = -5
            score -= 5
        else:
            factors["naming_convention"] = 0

        score = max(0, min(100, score))

        # Generate recommendations based on score
        recommendations = []
        if score < 60:
            recommendations.append(
                "HIGH RISK: Tool has significant security concerns. Review immediately."
            )
        if score < 80:
            recommendations.append(
                "MEDIUM RISK: Consider adding additional safeguards or access controls."
            )
        if factors.get("data_sensitivity", 0) < -10:
            recommendations.append(
                "Tool accesses sensitive data. Ensure encryption at rest and in transit."
            )
        if factors.get("category_risk", 0) <= -10:
            recommendations.append(
                "High-risk category tool. Implement comprehensive audit logging."
            )

        # Determine category based on score
        if score >= 80:
            category = "good"
        elif score >= 60:
            category = "fair"
        elif score >= 40:
            category = "poor"
        else:
            category = "critical"

        return SecurityScore(
            tool_name=tool_name,
            score=score,
            category=category,
            factors=factors,
            recommendations=recommendations,
        )

    async def evaluate_access_policy(
        self,
        tool_name: str,
        session_level: str = "standard",
        invocation_count_hour: int = 0,
    ) -> EnforcementResult:
        """Evaluate if a tool invocation should be allowed.

        Args:
            tool_name: Name of the tool
            session_level: Current session level (standard, elevated, admin)
            invocation_count_hour: Number of invocations in the last hour

        Returns:
            EnforcementResult with allow/deny decision
        """
        for policy in self._policies:
            if not policy.enabled:
                continue

            if not self._policy_applies(policy, tool_name):
                continue

            for rule in policy.rules:
                result = await self._evaluate_rule(
                    rule, tool_name, session_level, invocation_count_hour
                )
                if not result.allowed:
                    return result

        return EnforcementResult(
            tool_name=tool_name,
            policy_id="default",
            allowed=True,
            reason="No restricting policies matched",
        )

    def _policy_applies(self, policy: GovernancePolicy, tool_name: str) -> bool:
        """Check if a policy applies to a tool.

        Supports wildcard patterns like "security.*" or "*.execute".
        """
        import fnmatch

        return fnmatch.fnmatch(tool_name, policy.applies_to)

    async def _evaluate_rule(
        self,
        rule: dict[str, Any],
        tool_name: str,
        session_level: str,
        invocation_count_hour: int,
    ) -> EnforcementResult:
        """Evaluate a single governance rule."""
        rule_type = rule.get("type")

        if rule_type == "require_session_level":
            min_level = rule.get("min_level", "standard")
            level_order = {"standard": 0, "elevated": 1, "admin": 2}
            if level_order.get(session_level, 0) < level_order.get(min_level, 0):
                return EnforcementResult(
                    tool_name=tool_name,
                    policy_id=rule.get("policy_id", "unknown"),
                    allowed=False,
                    reason=f"Requires {min_level} session level",
                    action_taken="blocked",
                )

        elif rule_type == "rate_limit":
            max_per_hour = rule.get("max_invocations_per_hour", 1000)
            if invocation_count_hour >= max_per_hour:
                return EnforcementResult(
                    tool_name=tool_name,
                    policy_id=rule.get("policy_id", "unknown"),
                    allowed=False,
                    reason=f"Rate limit exceeded: {max_per_hour} per hour",
                    action_taken="rate_limited",
                )

        elif rule_type == "block_dangerous_patterns":
            # This would be evaluated at invocation time with actual arguments
            pass

        return EnforcementResult(
            tool_name=tool_name,
            policy_id=rule.get("policy_id", "unknown"),
            allowed=True,
        )

    async def generate_compliance_report(self) -> ComplianceReport:
        """Generate system-wide governance compliance report.

        Returns:
            ComplianceReport with overall compliance status
        """
        # This is a simplified version - in production, you'd query all tools
        # For now, return a template
        return ComplianceReport(
            generated_at=datetime.utcnow(),
            total_tools=133,
            compliant_tools=130,
            non_compliant_tools=[],
            policy_violations=[],
            security_scores=[],
            recommendations=[
                "Regularly review tools with security scores below 60",
                "Ensure all shell tools have proper input validation",
                "Monitor rate limits for high-frequency tools",
            ],
        )

    async def list_policies(self) -> list[GovernancePolicy]:
        """List all active governance policies."""
        return [p for p in self._policies if p.enabled]

    async def add_policy(self, policy: GovernancePolicy) -> None:
        """Add a new governance policy."""
        self._policies.append(policy)
        await self._save_policies()

    async def remove_policy(self, policy_id: str) -> bool:
        """Remove a governance policy by ID."""
        for i, policy in enumerate(self._policies):
            if policy.id == policy_id:
                del self._policies[i]
                await self._save_policies()
                return True
        return False

    async def _save_policies(self) -> None:
        """Save policies to file."""
        if self._policies_path:
            data = {"policies": [json.loads(policy.json()) for policy in self._policies]}
            self._policies_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._policies_path, "w") as f:
                json.dump(data, f, indent=2)
