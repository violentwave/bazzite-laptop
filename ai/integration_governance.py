"""Integration governance for Notion, Slack, and GitHub Actions (P135).

Governs cross-tool operations with risk metadata, policy checks, scope requirements,
and audit linkage. Reuses P127 policy engine and existing audit patterns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ai.config import VECTOR_DB_DIR

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class IntegrationSystem(Enum):
    """Supported integration systems."""

    NOTION = "notion"
    SLACK = "slack"
    GITHUB = "github"


class IntegrationRisk(Enum):
    """Risk tier for integration actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class IntegrationAction:
    """An governable integration action."""

    action_id: str
    system: IntegrationSystem
    name: str
    description: str
    risk_tier: IntegrationRisk
    requires_approval: bool
    scope_required: bool
    allowed_payload_keys: tuple[str, ...]


@dataclass
class IntegrationContext:
    """Context for an integration action."""

    phase_id: str | None = None
    workflow_id: str | None = None
    session_id: str | None = None
    operator_id: str | None = None
    audit_id: str | None = None


@dataclass
class GovernanceResult:
    """Result of a governance evaluation."""

    allowed: bool
    action_id: str
    reason: str
    audit_id: str | None
    evidence_id: str | None
    context: dict[str, Any] = field(default_factory=dict)


DEFAULT_INTEGRATION_ACTIONS = [
    IntegrationAction(
        action_id="notion.search",
        system=IntegrationSystem.NOTION,
        name="Search Notion",
        description="Search pages and databases in Notion",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=("query", "filter_type", "limit"),
    ),
    IntegrationAction(
        action_id="notion.get_page",
        system=IntegrationSystem.NOTION,
        name="Get Notion Page",
        description="Get a Notion page by ID",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=("page_id",),
    ),
    IntegrationAction(
        action_id="notion.get_page_content",
        system=IntegrationSystem.NOTION,
        name="Get Notion Page Content",
        description="Get content blocks from a Notion page",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=("page_id",),
    ),
    IntegrationAction(
        action_id="notion.query_database",
        system=IntegrationSystem.NOTION,
        name="Query Notion Database",
        description="Query a Notion database",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=("database_id",),
    ),
    IntegrationAction(
        action_id="notion.update_row",
        system=IntegrationSystem.NOTION,
        name="Update Notion Row",
        description="Update a row in Notion database",
        risk_tier=IntegrationRisk.MEDIUM,
        requires_approval=False,
        scope_required=True,
        allowed_payload_keys=("database_id", "row_id", "properties"),
    ),
    IntegrationAction(
        action_id="notion.create_page",
        system=IntegrationSystem.NOTION,
        name="Create Notion Page",
        description="Create a new Notion page",
        risk_tier=IntegrationRisk.MEDIUM,
        requires_approval=False,
        scope_required=True,
        allowed_payload_keys=("parent_id", "title", "content"),
    ),
    IntegrationAction(
        action_id="slack.list_channels",
        system=IntegrationSystem.SLACK,
        name="List Slack Channels",
        description="List Slack channels",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=("limit",),
    ),
    IntegrationAction(
        action_id="slack.list_users",
        system=IntegrationSystem.SLACK,
        name="List Slack Users",
        description="List Slack users",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=(),
    ),
    IntegrationAction(
        action_id="slack.post_message",
        system=IntegrationSystem.SLACK,
        name="Post Slack Message",
        description="Post a message to a Slack channel",
        risk_tier=IntegrationRisk.MEDIUM,
        requires_approval=False,
        scope_required=True,
        allowed_payload_keys=("channel", "text", "thread_ts"),
    ),
    IntegrationAction(
        action_id="slack.get_history",
        system=IntegrationSystem.SLACK,
        name="Get Slack History",
        description="Get Slack channel history",
        risk_tier=IntegrationRisk.LOW,
        requires_approval=False,
        scope_required=False,
        allowed_payload_keys=("channel", "limit"),
    ),
    IntegrationAction(
        action_id="slack.broadcast",
        system=IntegrationSystem.SLACK,
        name="Broadcast to Multiple Channels",
        description="Post to multiple Slack channels (broad activity)",
        risk_tier=IntegrationRisk.HIGH,
        requires_approval=True,
        scope_required=True,
        allowed_payload_keys=("channels", "text"),
    ),
    IntegrationAction(
        action_id="github.pr_create",
        system=IntegrationSystem.GITHUB,
        name="Create GitHub PR",
        description="Create a pull request",
        risk_tier=IntegrationRisk.HIGH,
        requires_approval=True,
        scope_required=True,
        allowed_payload_keys=("owner", "repo", "title", "body", "head", "base"),
    ),
    IntegrationAction(
        action_id="github.issue_create",
        system=IntegrationSystem.GITHUB,
        name="Create GitHub Issue",
        description="Create a GitHub issue",
        risk_tier=IntegrationRisk.MEDIUM,
        requires_approval=False,
        scope_required=True,
        allowed_payload_keys=("owner", "repo", "title", "body", "labels"),
    ),
    IntegrationAction(
        action_id="github.workflow_trigger",
        system=IntegrationSystem.GITHUB,
        name="Trigger GitHub Workflow",
        description="Trigger a GitHub Actions workflow",
        risk_tier=IntegrationRisk.HIGH,
        requires_approval=True,
        scope_required=True,
        allowed_payload_keys=("owner", "repo", "workflow_id", "ref"),
    ),
]


class IntegrationGovernance:
    """Governance coordinator for integration actions.

    Enforces:
    1. Default deny for unknown actions
    2. Policy checks for mutation-capable actions
    3. Scope/attribution requirements
    4. Audit linkage
    5. Redaction for sensitive content
    """

    def __init__(
        self,
        actions: list[IntegrationAction] | None = None,
        state_path: Path | None = None,
    ):
        self.actions = actions or DEFAULT_INTEGRATION_ACTIONS
        self.state_path = state_path or (VECTOR_DB_DIR / "integration_governance.json")
        self._action_map = {a.action_id: a for a in self.actions}

    def get_action(self, action_id: str) -> IntegrationAction | None:
        """Get an action by ID."""
        return self._action_map.get(action_id)

    def evaluate(
        self,
        action_id: str,
        context: IntegrationContext,
        payload: dict[str, Any],
        approval_present: bool = False,
    ) -> GovernanceResult:
        """Evaluate whether an integration action is allowed."""

        action = self.get_action(action_id)

        if not action:
            return GovernanceResult(
                allowed=False,
                action_id=action_id,
                reason="Unknown integration action - default deny",
                audit_id=None,
                evidence_id=None,
                context={"error": "action_not_found"},
            )

        if action.requires_approval and not approval_present:
            return GovernanceResult(
                allowed=False,
                action_id=action_id,
                reason=f"Action {action_id} requires explicit operator approval",
                audit_id=None,
                evidence_id=None,
                context={"requires_approval": True},
            )

        if action.scope_required and not context.phase_id and not context.workflow_id:
            return GovernanceResult(
                allowed=False,
                action_id=action_id,
                reason=f"Action {action_id} requires phase or workflow context",
                audit_id=None,
                evidence_id=None,
                context={"scope_required": True},
            )

        if action.risk_tier == IntegrationRisk.HIGH and not approval_present:
            return GovernanceResult(
                allowed=False,
                action_id=action_id,
                reason=f"High-risk action {action_id} requires approval",
                audit_id=None,
                evidence_id=None,
                context={"risk_tier": "high"},
            )

        audit_id = (
            context.audit_id or f"audit_{action_id}_{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"
        )

        filtered_payload = self._filter_payload(payload, action.allowed_payload_keys)

        return GovernanceResult(
            allowed=True,
            action_id=action_id,
            reason=f"Action {action_id} approved",
            audit_id=audit_id,
            evidence_id=None,
            context={
                "system": action.system.value,
                "risk_tier": action.risk_tier.value,
                "payload_keys": list(filtered_payload.keys()),
            },
        )

    def _filter_payload(
        self,
        payload: dict[str, Any],
        allowed_keys: tuple[str, ...],
    ) -> dict[str, Any]:
        """Filter payload to only allowed keys."""
        if not allowed_keys:
            return {}
        return {k: v for k, v in payload.items() if k in allowed_keys}

    def list_actions(self, system: IntegrationSystem | None = None) -> list[IntegrationAction]:
        """List all registered actions, optionally filtered by system."""
        if system:
            return [a for a in self.actions if a.system == system]
        return list(self.actions)


def redact_integration_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive paths and secrets from integration payloads."""
    sensitive_patterns = [
        "/home/",
        "/root/",
        ".bashrc",
        ".ssh/",
        "password",
        "secret",
        "api_key",
        "token",
    ]

    def redact_value(value: Any) -> Any:
        if isinstance(value, str):
            for pattern in sensitive_patterns:
                if pattern in value.lower():
                    return "[REDACTED]"
            return value
        elif isinstance(value, dict):
            return {k: redact_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [redact_value(v) for v in value]
        return value

    return {k: redact_value(v) for k, v in data.items()}


_instance: IntegrationGovernance | None = None


def get_governance() -> IntegrationGovernance:
    """Get or create the governance singleton."""
    global _instance
    if _instance is None:
        _instance = IntegrationGovernance()
    return _instance
