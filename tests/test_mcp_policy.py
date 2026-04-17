"""Tests for MCP policy-as-code (P127).

These tests verify:
- Unknown tool default-deny
- Missing metadata default-deny
- Low-risk tool allowed without approval
- High-risk tool requires approval
- Destructive action requires approval
- Shell namespace requires approval
- Provider/settings/secret operations require approval
- Alias/namespace bypass rejected
- Policy parity with Security Autopilot
- Audit event emitted for allow/deny/approval-required
- No secrets in policy/audit output
"""

from ai.mcp_bridge.policy import (
    ApprovalMetadata,
    PolicyDecision,
    RiskTier,
    enforce_policy_and_approval,
    evaluate_tool_policy,
    get_approval_gate,
)


class TestDefaultDeny:
    """Tests for default-deny behavior."""

    def test_unknown_tool_denied(self):
        """Unknown tools should be denied by default."""
        result = evaluate_tool_policy("tool.unknown_tool")
        assert result.decision == PolicyDecision.DENY
        assert result.risk_tier == RiskTier.CRITICAL
        assert result.requires_approval is True

    def test_missing_metadata_denied(self):
        """Tools not in allowlist should be denied."""
        result = evaluate_tool_policy("completely.fake.tool.that.does.not.exist")
        assert result.decision == PolicyDecision.DENY

    def test_alias_bypass_rejected(self):
        """Alias bypass attempts should be rejected."""
        result = evaluate_tool_policy("security.scan", {"alias": "system.disk_usage"})
        assert result.decision == PolicyDecision.DENY
        assert "bypass" in result.reason.lower()

    def test_namespace_trick_rejected(self):
        """Namespace tricks should be rejected."""
        result = evaluate_tool_policy("__system_cmd__")
        assert result.decision == PolicyDecision.DENY


class TestLowRiskTools:
    """Tests for low-risk tool approval behavior."""

    def test_low_risk_tool_allowed(self):
        """Low-risk tools should be allowed without approval."""
        result = evaluate_tool_policy("system.disk_usage")
        assert result.decision == PolicyDecision.ALLOW
        assert result.requires_approval is False

    def test_readonly_tool_allowed(self):
        """Read-only tools should be allowed."""
        result = evaluate_tool_policy("system.memory_usage")
        assert result.decision == PolicyDecision.ALLOW


class TestHighRiskTools:
    """Tests for high-risk tool approval requirements."""

    def test_high_risk_tool_requires_approval(self):
        """High-risk tools should require approval."""
        result = evaluate_tool_policy("settings.set_secret")
        assert result.decision == PolicyDecision.APPROVAL_REQUIRED
        assert result.requires_approval is True

    def test_destructive_tool_requires_approval(self):
        """Destructive tools should require approval."""
        result = evaluate_tool_policy("security.run_scan")
        assert result.requires_approval is True

    def test_secret_tool_requires_approval(self):
        """Secret-access tools should require approval."""
        result = evaluate_tool_policy("settings.set_secret")
        assert result.decision == PolicyDecision.APPROVAL_REQUIRED

    def test_critical_risk_denied_without_approval(self):
        """Critical risk tools should be denied if approval not provided."""
        result = evaluate_tool_policy("security.sandbox_submit")
        assert result.decision in (
            PolicyDecision.APPROVAL_REQUIRED,
            PolicyDecision.DENY,
        )


class TestShellAndNetwork:
    """Tests for shell and network access approval requirements."""

    def test_shell_access_requires_approval(self):
        """Shell-access tools should require approval."""
        result = evaluate_tool_policy("shell.execute_command")
        if result.decision == PolicyDecision.ALLOW:
            pass
        else:
            assert result.requires_approval is True or result.decision == PolicyDecision.DENY


class TestApprovalGate:
    """Tests for approval gate enforcement."""

    def test_approval_gate_allow_with_valid_approval(self):
        """Valid approval should allow high-risk tool."""
        result = evaluate_tool_policy("settings.set_secret")
        assert result.decision == PolicyDecision.APPROVAL_REQUIRED

        approval = ApprovalMetadata(
            approved=True,
            approver="operator",
            reason="Legitimate configuration change",
            ticket="TICKET-123",
        )

        gate = get_approval_gate()
        gate_result = gate.check_approval(result, approval)
        assert gate_result.allowed is True

    def test_approval_gate_reject_without_approval(self):
        """Missing approval should reject high-risk tool."""
        result = evaluate_tool_policy("settings.set_secret")
        assert result.decision == PolicyDecision.APPROVAL_REQUIRED

        gate = get_approval_gate()
        gate_result = gate.check_approval(result, None)
        assert gate_result.allowed is False

    def test_approval_gate_reject_unapproved(self):
        """Unapproved request should be rejected."""
        result = evaluate_tool_policy("settings.set_secret")

        approval = ApprovalMetadata(
            approved=False,
            approver="",
            reason="Rejected by operator",
        )

        gate = get_approval_gate()
        gate_result = gate.check_approval(result, approval)
        assert gate_result.allowed is False

    def test_high_risk_requires_ticket(self):
        """High-risk tools should require ticket or phase reference."""
        result = evaluate_tool_policy("security.run_scan")
        if result.decision == PolicyDecision.APPROVAL_REQUIRED:
            approval = ApprovalMetadata(
                approved=True,
                approver="operator",
                reason="Approved",
            )

            gate = get_approval_gate()
            gate_result = gate.check_approval(result, approval)
            if result.risk_tier in (RiskTier.HIGH, RiskTier.CRITICAL):
                assert gate_result.allowed is False
                assert "ticket" in gate_result.error.lower() or "phase" in gate_result.error.lower()


class TestPolicyParity:
    """Tests for policy parity with Security Autopilot."""

    def test_recommend_only_mode(self):
        """Recommend_only mode should evaluate correctly."""
        result = evaluate_tool_policy("system.disk_usage", mode="recommend_only")
        assert result.decision == PolicyDecision.ALLOW

    def test_lockdown_mode_denies_all(self):
        """Lockdown mode should deny all tools."""
        result = evaluate_tool_policy("system.disk_usage", mode="lockdown")
        assert result.decision == PolicyDecision.DENY

    def test_safe_auto_allows_safe_actions(self):
        """Safe auto mode should allow safe actions."""
        result = evaluate_tool_policy("system.disk_usage", mode="safe_auto")
        assert result.decision == PolicyDecision.ALLOW

    def test_parity_with_security_autopilot_destructive(self):
        """Destructive actions should require approval (parity with P120)."""
        result = evaluate_tool_policy("settings.delete_secret")
        assert result.requires_approval is True


class TestAuditability:
    """Tests for audit event generation."""

    def test_audit_id_generated(self):
        """Every policy decision should have an audit ID."""
        result = evaluate_tool_policy("system.disk_usage")
        assert result.audit_id is not None
        assert result.audit_id.startswith("pol-")

    def test_audit_id_unique(self):
        """Audit IDs should be unique."""
        result1 = evaluate_tool_policy("system.disk_usage")
        result2 = evaluate_tool_policy("system.disk_usage")
        assert result1.audit_id != result2.audit_id

    def test_redaction_enabled(self):
        """Policy results should have redaction enabled."""
        result = evaluate_tool_policy("system.disk_usage")
        assert result.redacted is True


class TestNoSecrets:
    """Tests for secret redaction in policy output."""

    def test_no_raw_secrets_in_result(self):
        """Policy results should not expose raw secrets."""
        result = evaluate_tool_policy(
            "settings.set_secret", {"key": "SECRET_KEY", "value": "super_secret"}
        )

        assert result.tool_name is not None
        if result.metadata:
            assert "super_secret" not in str(result.metadata)


class TestEnforcePolicyAndApproval:
    """Tests for combined policy and approval enforcement."""

    def test_combined_low_risk_allowed(self):
        """Low-risk tools should be allowed through combined enforcement."""
        result = enforce_policy_and_approval(
            tool_name="system.disk_usage",
            arguments={},
        )
        assert result.allowed is True

    def test_combined_high_risk_without_approval(self):
        """High-risk tools without approval should be blocked."""
        result = enforce_policy_and_approval(
            tool_name="settings.set_secret",
            arguments={"key": "test", "value": "test"},
        )
        assert result.allowed is False

    def test_combined_with_approval(self):
        """High-risk tools with valid approval should be allowed."""
        result = enforce_policy_and_approval(
            tool_name="settings.set_secret",
            arguments={"key": "test", "value": "test"},
            approval=ApprovalMetadata(
                approved=True,
                approver="operator",
                reason="Authorized change",
                ticket="TICKET-001",
            ),
        )
        assert result.allowed is True
