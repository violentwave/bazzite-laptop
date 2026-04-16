"""Security Autopilot policy engine for P120.

This module evaluates requested actions and returns policy outcomes without
executing remediation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from ai.config import CONFIGS_DIR
from ai.security_autopilot.models import RemediationAction

DEFAULT_POLICY_PATH = CONFIGS_DIR / "security-autopilot-policy.yaml"


class PolicyMode(StrEnum):
    """Operational mode for Security Autopilot policy evaluation."""

    MONITOR_ONLY = "monitor_only"
    RECOMMEND_ONLY = "recommend_only"
    SAFE_AUTO = "safe_auto"
    APPROVAL_REQUIRED = "approval_required"
    LOCKDOWN = "lockdown"


class PolicyDecision(StrEnum):
    """Decision outcome produced by policy evaluation."""

    AUTO_ALLOWED = "auto_allowed"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


class ActionCategory(StrEnum):
    """Security action category used by policy mappings."""

    READ_ONLY = "read_only"
    SCAN = "scan"
    EVIDENCE = "evidence"
    NOTIFY = "notify"
    INGEST = "ingest"
    QUARANTINE = "quarantine"
    TERMINATE_PROCESS = "terminate_process"
    DISABLE_SERVICE = "disable_service"
    ROTATE_SECRET = "rotate_secret"  # noqa: S105
    FIREWALL_CHANGE = "firewall_change"
    DELETE_FILE = "delete_file"
    ARBITRARY_SHELL = "arbitrary_shell"
    SUDO = "sudo"
    SECRET_READ = "secret_read"  # noqa: S105
    SYSTEM_WRITE = "system_write"
    UNKNOWN = "unknown"


@dataclass
class PolicyRequest:
    """Input model for policy evaluation."""

    action: str
    category: ActionCategory | str
    mode: PolicyMode | str | None = None
    target: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    actor: str = "security_autopilot"


@dataclass
class PolicyResult:
    """Output model from policy evaluation."""

    decision: PolicyDecision
    reason: str
    approval_required: bool
    mode: PolicyMode
    action: str
    category: ActionCategory
    audit_metadata: dict[str, Any] = field(default_factory=dict)
    redacted_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAutopilotPolicyConfig:
    """Normalized policy config loaded from YAML."""

    default_mode: PolicyMode
    mode_rules: dict[PolicyMode, dict[str, set[ActionCategory]]]
    blocked_always: set[ActionCategory]
    destructive_actions: set[ActionCategory]
    allowed_path_prefixes: list[str]
    redaction_patterns: list[str]
    policy_version: str = "p120-v1"


def load_policy_config(path: Path | None = None) -> SecurityAutopilotPolicyConfig:
    """Load and validate policy configuration YAML."""

    config_path = path or DEFAULT_POLICY_PATH
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    default_mode = PolicyMode(raw.get("default_mode", PolicyMode.RECOMMEND_ONLY.value))

    blocked_always = {ActionCategory(value) for value in raw.get("blocked_always", [])}
    destructive_actions = {ActionCategory(value) for value in raw.get("destructive_actions", [])}

    mode_rules: dict[PolicyMode, dict[str, set[ActionCategory]]] = {}
    for mode_value, rule_body in (raw.get("modes") or {}).items():
        mode = PolicyMode(mode_value)
        body = rule_body or {}
        mode_rules[mode] = {
            "auto_allowed": {ActionCategory(v) for v in body.get("auto_allowed", [])},
            "approval_required": {ActionCategory(v) for v in body.get("approval_required", [])},
            "blocked": {ActionCategory(v) for v in body.get("blocked", [])},
        }

    required_modes = {mode for mode in PolicyMode}
    if set(mode_rules) != required_modes:
        missing = sorted(mode.value for mode in required_modes - set(mode_rules))
        msg = f"policy config missing mode definitions: {missing}"
        raise ValueError(msg)

    return SecurityAutopilotPolicyConfig(
        default_mode=default_mode,
        mode_rules=mode_rules,
        blocked_always=blocked_always,
        destructive_actions=destructive_actions,
        allowed_path_prefixes=list(raw.get("allowed_path_prefixes", [])),
        redaction_patterns=list(raw.get("redaction_patterns", [])),
        policy_version=str(raw.get("policy_version", "p120-v1")),
    )


def redact_policy_payload(value: Any, patterns: list[str] | None = None) -> Any:
    """Redact sensitive fragments from policy payload values."""

    compiled = [re.compile(p) for p in (patterns or [])]

    if isinstance(value, str):
        redacted = value
        for pattern in compiled:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    if isinstance(value, dict):
        return {k: redact_policy_payload(v, patterns=patterns) for k, v in value.items()}

    if isinstance(value, list):
        return [redact_policy_payload(item, patterns=patterns) for item in value]

    return value


class SecurityAutopilotPolicy:
    """Policy evaluator for Security Autopilot actions."""

    def __init__(self, config: SecurityAutopilotPolicyConfig | None = None) -> None:
        self.config = config or load_policy_config()

    def evaluate_action(self, request: PolicyRequest) -> PolicyResult:
        """Evaluate a single policy request and return a structured decision."""

        mode = self._normalize_mode(request.mode)
        action = request.action.strip()
        if not action:
            return self._blocked(
                mode=mode,
                action="",
                category=ActionCategory.UNKNOWN,
                reason="Malformed request: action must be non-empty",
                request=request,
            )

        category = self._normalize_category(request.category)
        if category is None:
            return self._blocked(
                mode=mode,
                action=action,
                category=ActionCategory.UNKNOWN,
                reason="Malformed request: unknown action category",
                request=request,
            )

        path_check = self._validate_target_path(category=category, target=request.target)
        if path_check is not None:
            return self._blocked(
                mode=mode,
                action=action,
                category=category,
                reason=path_check,
                request=request,
            )

        if category in {
            ActionCategory.ARBITRARY_SHELL,
            ActionCategory.SUDO,
            ActionCategory.SECRET_READ,
        }:
            return self._blocked(
                mode=mode,
                action=action,
                category=category,
                reason=f"Category '{category.value}' is globally blocked",
                request=request,
            )

        if category in self.config.blocked_always:
            return self._blocked(
                mode=mode,
                action=action,
                category=category,
                reason=f"Category '{category.value}' blocked by global policy",
                request=request,
            )

        rules = self.config.mode_rules[mode]

        if mode == PolicyMode.LOCKDOWN and category not in {
            ActionCategory.READ_ONLY,
            ActionCategory.EVIDENCE,
        }:
            return self._blocked(
                mode=mode,
                action=action,
                category=category,
                reason="Lockdown mode only allows read_only/evidence actions",
                request=request,
            )

        if category in rules["blocked"]:
            return self._blocked(
                mode=mode,
                action=action,
                category=category,
                reason=f"Category '{category.value}' is blocked in mode '{mode.value}'",
                request=request,
            )

        if category in rules["approval_required"]:
            return self._approval(
                mode=mode,
                action=action,
                category=category,
                reason=(
                    f"Category '{category.value}' requires manual approval in mode '{mode.value}'"
                ),
                request=request,
            )

        if category in rules["auto_allowed"]:
            if category in self.config.destructive_actions:
                return self._approval(
                    mode=mode,
                    action=action,
                    category=category,
                    reason=(
                        f"Category '{category.value}' is destructive and cannot be auto-allowed"
                    ),
                    request=request,
                )
            return self._allowed(
                mode=mode,
                action=action,
                category=category,
                reason=f"Category '{category.value}' is auto-allowed in mode '{mode.value}'",
                request=request,
            )

        return self._blocked(
            mode=mode,
            action=action,
            category=category,
            reason=f"Category '{category.value}' has no rule in mode '{mode.value}'",
            request=request,
        )

    def evaluate_remediation_action(
        self,
        remediation_action: RemediationAction,
        mode: PolicyMode | str | None = None,
        target: str = "",
        payload: dict[str, Any] | None = None,
    ) -> PolicyResult:
        """Evaluate P119 remediation actions without executing them."""

        request = PolicyRequest(
            action=remediation_action.title,
            category=self._infer_category_from_tool(remediation_action.tool),
            mode=mode,
            target=target,
            payload=payload
            or {
                "description": remediation_action.description,
                "tool": remediation_action.tool,
                "automated": remediation_action.automated,
            },
        )
        return self.evaluate_action(request)

    def _normalize_mode(self, mode: PolicyMode | str | None) -> PolicyMode:
        if mode is None:
            return self.config.default_mode
        if isinstance(mode, PolicyMode):
            return mode
        try:
            return PolicyMode(mode)
        except ValueError as exc:
            msg = f"Malformed request: unknown policy mode '{mode}'"
            raise ValueError(msg) from exc

    def _normalize_category(self, category: ActionCategory | str) -> ActionCategory | None:
        if isinstance(category, ActionCategory):
            return category
        try:
            return ActionCategory(category)
        except ValueError:
            return None

    def _validate_target_path(self, category: ActionCategory, target: str) -> str | None:
        if not target:
            return None

        if category not in {ActionCategory.SYSTEM_WRITE, ActionCategory.DELETE_FILE}:
            return None

        target_path = Path(target).expanduser().resolve(strict=False)
        for allowed_prefix in self.config.allowed_path_prefixes:
            prefix_path = Path(allowed_prefix).expanduser().resolve(strict=False)
            if target_path == prefix_path or prefix_path in target_path.parents:
                return None
        return f"Target path '{target_path}' is outside allowed policy roots"

    def _infer_category_from_tool(self, tool: str | None) -> ActionCategory:
        if not tool:
            return ActionCategory.UNKNOWN
        if tool.startswith("security.") or tool.startswith("system."):
            if any(token in tool for token in ("status", "summary", "health", "check")):
                return ActionCategory.READ_ONLY
            if "scan" in tool:
                return ActionCategory.SCAN
        if tool.startswith("logs."):
            return ActionCategory.EVIDENCE
        if tool.startswith("workflow."):
            return ActionCategory.NOTIFY
        return ActionCategory.UNKNOWN

    def _audit_metadata(
        self,
        mode: PolicyMode,
        request: PolicyRequest,
    ) -> dict[str, Any]:
        return {
            "evaluated_at": datetime.now(tz=UTC).isoformat(),
            "policy_version": self.config.policy_version,
            "mode": mode.value,
            "actor": request.actor,
        }

    def _allowed(
        self,
        *,
        mode: PolicyMode,
        action: str,
        category: ActionCategory,
        reason: str,
        request: PolicyRequest,
    ) -> PolicyResult:
        return PolicyResult(
            decision=PolicyDecision.AUTO_ALLOWED,
            reason=reason,
            approval_required=False,
            mode=mode,
            action=action,
            category=category,
            audit_metadata=self._audit_metadata(mode=mode, request=request),
            redacted_payload=redact_policy_payload(
                request.payload,
                patterns=self.config.redaction_patterns,
            ),
        )

    def _approval(
        self,
        *,
        mode: PolicyMode,
        action: str,
        category: ActionCategory,
        reason: str,
        request: PolicyRequest,
    ) -> PolicyResult:
        return PolicyResult(
            decision=PolicyDecision.APPROVAL_REQUIRED,
            reason=reason,
            approval_required=True,
            mode=mode,
            action=action,
            category=category,
            audit_metadata=self._audit_metadata(mode=mode, request=request),
            redacted_payload=redact_policy_payload(
                request.payload,
                patterns=self.config.redaction_patterns,
            ),
        )

    def _blocked(
        self,
        *,
        mode: PolicyMode,
        action: str,
        category: ActionCategory,
        reason: str,
        request: PolicyRequest,
    ) -> PolicyResult:
        return PolicyResult(
            decision=PolicyDecision.BLOCKED,
            reason=reason,
            approval_required=False,
            mode=mode,
            action=action,
            category=category,
            audit_metadata=self._audit_metadata(mode=mode, request=request),
            redacted_payload=redact_policy_payload(
                request.payload,
                patterns=self.config.redaction_patterns,
            ),
        )
