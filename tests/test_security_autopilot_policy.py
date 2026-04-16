"""P120 tests for Security Autopilot policy engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai.security_autopilot.models import RemediationAction, next_id
from ai.security_autopilot.policy import (
    ActionCategory,
    PolicyDecision,
    PolicyMode,
    PolicyRequest,
    SecurityAutopilotPolicy,
    load_policy_config,
)


def _policy() -> SecurityAutopilotPolicy:
    return SecurityAutopilotPolicy()


def test_config_loading_works_and_default_mode_is_safe() -> None:
    cfg = load_policy_config()
    assert cfg.default_mode == PolicyMode.RECOMMEND_ONLY
    assert ActionCategory.ARBITRARY_SHELL in cfg.blocked_always
    assert ActionCategory.SUDO in cfg.blocked_always
    assert ActionCategory.SECRET_READ in cfg.blocked_always


def test_safe_read_only_action_allowed_in_safe_modes() -> None:
    policy = _policy()
    for mode in (
        PolicyMode.MONITOR_ONLY,
        PolicyMode.RECOMMEND_ONLY,
        PolicyMode.SAFE_AUTO,
        PolicyMode.APPROVAL_REQUIRED,
        PolicyMode.LOCKDOWN,
    ):
        result = policy.evaluate_action(
            PolicyRequest(action="status-check", category=ActionCategory.READ_ONLY, mode=mode)
        )
        assert result.decision == PolicyDecision.AUTO_ALLOWED


def test_scan_evidence_notify_auto_allowed_when_configured() -> None:
    policy = _policy()
    for category in (ActionCategory.SCAN, ActionCategory.EVIDENCE, ActionCategory.NOTIFY):
        result = policy.evaluate_action(
            PolicyRequest(action="safe-op", category=category, mode=PolicyMode.SAFE_AUTO)
        )
        assert result.decision == PolicyDecision.AUTO_ALLOWED


def test_risky_actions_require_approval_in_approval_required_mode() -> None:
    policy = _policy()
    risky = (
        ActionCategory.QUARANTINE,
        ActionCategory.TERMINATE_PROCESS,
        ActionCategory.DISABLE_SERVICE,
        ActionCategory.ROTATE_SECRET,
        ActionCategory.FIREWALL_CHANGE,
        ActionCategory.DELETE_FILE,
    )
    for category in risky:
        result = policy.evaluate_action(
            PolicyRequest(action="risky-op", category=category, mode=PolicyMode.APPROVAL_REQUIRED)
        )
        assert result.decision == PolicyDecision.APPROVAL_REQUIRED
        assert result.approval_required is True


def test_arbitrary_shell_blocked_in_all_modes() -> None:
    policy = _policy()
    for mode in PolicyMode:
        result = policy.evaluate_action(
            PolicyRequest(action="shell", category=ActionCategory.ARBITRARY_SHELL, mode=mode)
        )
        assert result.decision == PolicyDecision.BLOCKED


def test_sudo_and_secret_read_blocked_in_all_modes() -> None:
    policy = _policy()
    for mode in PolicyMode:
        sudo_result = policy.evaluate_action(
            PolicyRequest(action="sudo-op", category=ActionCategory.SUDO, mode=mode)
        )
        secret_result = policy.evaluate_action(
            PolicyRequest(action="secret-op", category=ActionCategory.SECRET_READ, mode=mode)
        )
        assert sudo_result.decision == PolicyDecision.BLOCKED
        assert secret_result.decision == PolicyDecision.BLOCKED


def test_lockdown_blocks_non_read_only_actions() -> None:
    policy = _policy()
    for category in (ActionCategory.SCAN, ActionCategory.NOTIFY, ActionCategory.INGEST):
        result = policy.evaluate_action(
            PolicyRequest(action="restricted", category=category, mode=PolicyMode.LOCKDOWN)
        )
        assert result.decision == PolicyDecision.BLOCKED


def test_malformed_mode_or_category_or_action_rejected() -> None:
    policy = _policy()
    with pytest.raises(ValueError, match="unknown policy mode"):
        policy.evaluate_action(
            PolicyRequest(action="x", category=ActionCategory.READ_ONLY, mode="not-a-mode")
        )

    category_result = policy.evaluate_action(PolicyRequest(action="x", category="bad-category"))
    action_result = policy.evaluate_action(
        PolicyRequest(action="   ", category=ActionCategory.READ_ONLY)
    )
    assert category_result.decision == PolicyDecision.BLOCKED
    assert action_result.decision == PolicyDecision.BLOCKED


def test_sensitive_strings_redacted_in_policy_output() -> None:
    policy = _policy()
    result = policy.evaluate_action(
        PolicyRequest(
            action="notify",
            category=ActionCategory.NOTIFY,
            mode=PolicyMode.SAFE_AUTO,
            payload={
                "message": "token=abc123 email=alice@example.com",
                "auth": "Authorization: Bearer super-secret-token",
            },
        )
    )

    payload_text = str(result.redacted_payload)
    assert "abc123" not in payload_text
    assert "alice@example.com" not in payload_text
    assert "super-secret-token" not in payload_text
    assert "[REDACTED]" in payload_text


def test_path_validation_blocks_outside_allowed_roots() -> None:
    policy = _policy()
    result = policy.evaluate_action(
        PolicyRequest(
            action="delete outside",
            category=ActionCategory.DELETE_FILE,
            mode=PolicyMode.APPROVAL_REQUIRED,
            target="/etc/shadow",
        )
    )
    assert result.decision == PolicyDecision.BLOCKED
    assert "outside allowed policy roots" in result.reason


def test_p119_remediation_action_is_evaluated_without_execution() -> None:
    policy = _policy()
    remediation = RemediationAction(
        action_id=next_id("action"),
        title="Collect latest status context",
        description="Refresh security status snapshots",
        tool="security.status",
        automated=True,
    )
    result = policy.evaluate_remediation_action(remediation, mode=PolicyMode.RECOMMEND_ONLY)
    assert result.decision == PolicyDecision.AUTO_ALLOWED
    assert result.audit_metadata["policy_version"]


def test_config_file_exists() -> None:
    path = Path("configs/security-autopilot-policy.yaml")
    assert path.exists()
