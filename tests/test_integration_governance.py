"""Tests for integration governance (P135)."""

from __future__ import annotations

import pytest

from ai.integration_governance import (
    DEFAULT_INTEGRATION_ACTIONS,
    IntegrationContext,
    IntegrationGovernance,
    IntegrationSystem,
    redact_integration_payload,
)


@pytest.fixture
def governance() -> IntegrationGovernance:
    return IntegrationGovernance()


class TestDefaultActions:
    def test_default_actions_exist(self) -> None:
        assert len(DEFAULT_INTEGRATION_ACTIONS) > 0

    def test_notion_actions_exist(self) -> None:
        notion_actions = [
            a for a in DEFAULT_INTEGRATION_ACTIONS if a.system == IntegrationSystem.NOTION
        ]
        assert len(notion_actions) >= 4

    def test_slack_actions_exist(self) -> None:
        slack_actions = [
            a for a in DEFAULT_INTEGRATION_ACTIONS if a.system == IntegrationSystem.SLACK
        ]
        assert len(slack_actions) >= 4

    def test_github_actions_exist(self) -> None:
        github_actions = [
            a for a in DEFAULT_INTEGRATION_ACTIONS if a.system == IntegrationSystem.GITHUB
        ]
        assert len(github_actions) >= 3


class TestGovernanceBase:
    def test_get_action_exists(self, governance: IntegrationGovernance) -> None:
        action = governance.get_action("notion.search")
        assert action is not None

    def test_get_action_not_found(self, governance: IntegrationGovernance) -> None:
        action = governance.get_action("unknown.action")
        assert action is None


class TestDefaultDeny:
    def test_unknown_action_denied(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "unknown.integration.action",
            IntegrationContext(),
            {},
        )
        assert not result.allowed
        assert "default deny" in result.reason.lower()

    def test_unknown_action_has_error_context(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "unknown.integration.action",
            IntegrationContext(),
            {},
        )
        assert result.context.get("error") == "action_not_found"


class TestApprovalRequirement:
    def test_high_risk_requires_approval(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "slack.broadcast",
            IntegrationContext(),
            {"channels": ["#general"], "text": "test"},
            approval_present=False,
        )
        assert not result.allowed

    def test_high_risk_allowed_with_approval_and_scope(
        self, governance: IntegrationGovernance
    ) -> None:
        result = governance.evaluate(
            "slack.broadcast",
            IntegrationContext(phase_id="P119"),
            {"channels": ["#general"], "text": "test"},
            approval_present=True,
        )
        assert result.allowed


class TestScopeRequirement:
    def test_scope_required_without_context(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.update_row",
            IntegrationContext(),
            {"database_id": "db1", "row_id": "r1", "properties": {}},
            approval_present=False,
        )
        assert not result.allowed

    def test_scope_satisfied_with_phase(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.update_row",
            IntegrationContext(phase_id="P119"),
            {"database_id": "db1", "row_id": "r1", "properties": {}},
            approval_present=False,
        )
        assert result.allowed

    def test_scope_satisfied_with_workflow(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.update_row",
            IntegrationContext(workflow_id="security-audit"),
            {"database_id": "db1", "row_id": "r1", "properties": {}},
            approval_present=False,
        )
        assert result.allowed

    def test_high_risk_needs_both_scope_and_approval(
        self, governance: IntegrationGovernance
    ) -> None:
        result = governance.evaluate(
            "slack.broadcast",
            IntegrationContext(phase_id="P119"),
            {"channels": ["#general"], "text": "test"},
            approval_present=True,
        )
        assert result.allowed


class TestLowRiskAllowed:
    def test_low_risk_read_allowed(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.search",
            IntegrationContext(),
            {"query": "test"},
            approval_present=False,
        )
        assert result.allowed

    def test_low_risk_slack_allowed(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "slack.list_channels",
            IntegrationContext(),
            {"limit": 10},
            approval_present=False,
        )
        assert result.allowed


class TestPayloadFiltering:
    def test_filters_extra_keys(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.search",
            IntegrationContext(),
            {"query": "test", "extra_key": "should be filtered"},
            approval_present=False,
        )
        assert result.allowed
        assert "extra_key" not in result.context.get("payload_keys", [])

    def test_allows_allowed_keys(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.search",
            IntegrationContext(),
            {"query": "test", "limit": 10},
            approval_present=False,
        )
        assert result.allowed


class TestAuditLinkage:
    def test_generates_audit_id(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.search",
            IntegrationContext(),
            {"query": "test"},
            approval_present=False,
        )
        assert result.audit_id is not None
        assert result.audit_id.startswith("audit_notion.search_")


class TestRedaction:
    def test_redacts_home_paths(self) -> None:
        data = {
            "text": "Check /home/user for issues",
            "channel": "#general",
        }
        result = redact_integration_payload(data)
        assert result["text"] == "[REDACTED]"

    def test_redacts_api_keys(self) -> None:
        data = {
            "text": "Using key sk-secret-key-123",
            "channel": "#general",
        }
        result = redact_integration_payload(data)
        assert result["text"] == "[REDACTED]"

    def test_preserves_normal_text(self) -> None:
        data = {
            "text": "System health check passed",
            "channel": "#general",
        }
        result = redact_integration_payload(data)
        assert result["text"] == "System health check passed"


class TestActionList:
    def test_list_all_actions(self, governance: IntegrationGovernance) -> None:
        actions = governance.list_actions()
        assert len(actions) > 10

    def test_filter_by_system(self, governance: IntegrationGovernance) -> None:
        notion_actions = governance.list_actions(IntegrationSystem.NOTION)
        assert all(a.system == IntegrationSystem.NOTION for a in notion_actions)


class TestRegressionCompat:
    def test_phase_control_unchanged(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "notion.search",
            IntegrationContext(),
            {"query": "test"},
            approval_present=False,
        )
        assert result.allowed

    def test_workflow_unchanged(self, governance: IntegrationGovernance) -> None:
        result = governance.evaluate(
            "slack.post_message",
            IntegrationContext(workflow_id="daily-security"),
            {"channel": "#security", "text": "status"},
            approval_present=False,
        )
        assert result.allowed
