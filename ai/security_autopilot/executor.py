"""Safe remediation runner for Security Autopilot (P122).

The runner executes only fixed allowlisted actions with policy checks,
approval enforcement, and audit/evidence recording.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.security_autopilot.audit import AuditLedger, EvidenceManager
from ai.security_autopilot.models import AuditEvent, next_id
from ai.security_autopilot.policy import (
    ActionCategory,
    PolicyDecision,
    PolicyMode,
    PolicyRequest,
    PolicyResult,
    SecurityAutopilotPolicy,
    redact_policy_payload,
)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


_UNSAFE_SHELL_PATTERN = re.compile(
    r"(;|&&|\|\||`|\$\(|\b(?:bash|sh|sudo|rm\s+-rf|curl\s+.+\||wget\s+.+\|)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ActionDefinition:
    action_id: str
    category: ActionCategory
    destructive: bool
    requires_approval: bool
    rollback_possible: bool
    allowed_payload_keys: tuple[str, ...]


@dataclass
class ExecutionApproval:
    approved: bool = False
    approver: str = ""
    reason: str = ""
    approved_at: str = field(default_factory=_utc_now)


@dataclass
class RemediationExecutionRequest:
    action_id: str
    mode: PolicyMode | str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    target: str = ""
    actor: str = "security_autopilot_executor"
    approval: ExecutionApproval | None = None
    request_id: str = field(default_factory=lambda: next_id("exec"))


@dataclass
class RollbackMetadata:
    rollback_possible: bool
    rollback_action: str | None = None
    instructions: list[str] = field(default_factory=list)


@dataclass
class RemediationExecutionResult:
    request_id: str
    action_id: str
    status: str
    executed: bool
    policy_decision: str
    approval_required: bool
    approval_state: str
    reason: str
    output: dict[str, Any] = field(default_factory=dict)
    rollback: RollbackMetadata = field(default_factory=lambda: RollbackMetadata(False))
    audit_event_id: str = ""
    evidence_bundle_id: str = ""
    created_at: str = field(default_factory=_utc_now)


def _default_tool_runner(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute fixed tool calls via MCP bridge dispatcher."""

    from ai.mcp_bridge.tools import execute_tool

    raw = asyncio.run(execute_tool(tool_name, args))
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


class SafeRemediationExecutor:
    """Execute fixed remediation actions with strict safety boundaries."""

    ACTIONS: dict[str, ActionDefinition] = {
        "refresh_threat_intel": ActionDefinition(
            action_id="refresh_threat_intel",
            category=ActionCategory.INGEST,
            destructive=False,
            requires_approval=False,
            rollback_possible=False,
            allowed_payload_keys=(),
        ),
        "run_clamav_quick_scan": ActionDefinition(
            action_id="run_clamav_quick_scan",
            category=ActionCategory.SCAN,
            destructive=False,
            requires_approval=False,
            rollback_possible=False,
            allowed_payload_keys=("reason",),
        ),
        "run_health_snapshot": ActionDefinition(
            action_id="run_health_snapshot",
            category=ActionCategory.SCAN,
            destructive=False,
            requires_approval=False,
            rollback_possible=False,
            allowed_payload_keys=("reason",),
        ),
        "run_log_ingest": ActionDefinition(
            action_id="run_log_ingest",
            category=ActionCategory.INGEST,
            destructive=False,
            requires_approval=False,
            rollback_possible=False,
            allowed_payload_keys=("reason",),
        ),
        "notify_operator": ActionDefinition(
            action_id="notify_operator",
            category=ActionCategory.NOTIFY,
            destructive=False,
            requires_approval=False,
            rollback_possible=False,
            allowed_payload_keys=("message", "channel"),
        ),
        "prepare_quarantine_request": ActionDefinition(
            action_id="prepare_quarantine_request",
            category=ActionCategory.QUARANTINE,
            destructive=True,
            requires_approval=True,
            rollback_possible=True,
            allowed_payload_keys=("artifact", "reason"),
        ),
        "prepare_service_disable_request": ActionDefinition(
            action_id="prepare_service_disable_request",
            category=ActionCategory.DISABLE_SERVICE,
            destructive=True,
            requires_approval=True,
            rollback_possible=True,
            allowed_payload_keys=("service", "reason"),
        ),
        "prepare_secret_rotation_request": ActionDefinition(
            action_id="prepare_secret_rotation_request",
            category=ActionCategory.ROTATE_SECRET,
            destructive=True,
            requires_approval=True,
            rollback_possible=True,
            allowed_payload_keys=("secret_name", "reason"),
        ),
    }

    def __init__(
        self,
        *,
        policy: SecurityAutopilotPolicy | None = None,
        audit_ledger: AuditLedger | None = None,
        evidence_manager: EvidenceManager | None = None,
        tool_runner: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.policy = policy or SecurityAutopilotPolicy()
        self.audit_ledger = audit_ledger or AuditLedger()
        self.evidence_manager = evidence_manager or EvidenceManager()
        self.tool_runner = tool_runner or _default_tool_runner

    def execute(self, request: RemediationExecutionRequest) -> RemediationExecutionResult:
        """Execute one fixed remediation request with policy and approval gates."""

        action_id = request.action_id.strip().lower()
        action_def = self.ACTIONS.get(action_id)

        if action_def is None:
            return self._reject(
                request=request,
                action_id=action_id,
                policy_result=None,
                reason="Unknown remediation action",
                approval_required=False,
            )

        validation_issue = self._validate_request(request, action_def)
        if validation_issue:
            return self._reject(
                request=request,
                action_id=action_id,
                policy_result=None,
                reason=validation_issue,
                approval_required=action_def.requires_approval,
            )

        try:
            policy_result = self.policy.evaluate_action(
                PolicyRequest(
                    action=action_id,
                    category=action_def.category,
                    mode=request.mode,
                    target=request.target,
                    payload=request.payload,
                    actor=request.actor,
                )
            )
        except ValueError as exc:
            return self._reject(
                request=request,
                action_id=action_id,
                policy_result=None,
                reason=str(exc),
                approval_required=action_def.requires_approval,
            )

        if policy_result.decision == PolicyDecision.BLOCKED:
            return self._reject(
                request=request,
                action_id=action_id,
                policy_result=policy_result,
                reason=policy_result.reason,
                approval_required=policy_result.approval_required,
            )

        if (
            action_def.requires_approval
            or policy_result.decision == PolicyDecision.APPROVAL_REQUIRED
        ):
            approval = request.approval
            if approval is None or not approval.approved or not approval.approver.strip():
                return self._reject(
                    request=request,
                    action_id=action_id,
                    policy_result=policy_result,
                    reason="Approval required but missing or invalid approval state",
                    approval_required=True,
                )

        status, executed, output, rollback = self._run_fixed_action(request, action_def)
        reason = "Action executed" if executed else "Action prepared"

        result = RemediationExecutionResult(
            request_id=request.request_id,
            action_id=action_id,
            status=status,
            executed=executed,
            policy_decision=policy_result.decision.value,
            approval_required=policy_result.approval_required or action_def.requires_approval,
            approval_state=self._approval_state(request.approval),
            reason=reason,
            output=output,
            rollback=rollback,
        )
        return self._audit_and_attach(request=request, policy_result=policy_result, result=result)

    def _validate_request(
        self, request: RemediationExecutionRequest, action: ActionDefinition
    ) -> str | None:
        if not isinstance(request.payload, dict):
            return "Malformed payload: expected object"

        unknown_keys = set(request.payload) - set(action.allowed_payload_keys)
        if unknown_keys:
            return f"Malformed payload keys: {sorted(unknown_keys)}"

        if request.target and self._is_path_unsafe(request.target):
            return "Unsafe target path rejected"

        if self._has_unsafe_shell_content(request.payload):
            return "Unsafe shell-like content rejected"

        if self._has_raw_secret_material(request.payload):
            return "Raw secret-like content rejected"

        return None

    def _run_fixed_action(
        self,
        request: RemediationExecutionRequest,
        action: ActionDefinition,
    ) -> tuple[str, bool, dict[str, Any], RollbackMetadata]:
        if action.action_id == "refresh_threat_intel":
            output = self.tool_runner("intel.scrape_now", {})
            return ("executed", True, output, RollbackMetadata(False))

        if action.action_id == "run_clamav_quick_scan":
            output = self.tool_runner("security.run_scan", {"scan_type": "quick"})
            return ("executed", True, output, RollbackMetadata(False))

        if action.action_id == "run_health_snapshot":
            output = self.tool_runner("security.run_health", {})
            return ("executed", True, output, RollbackMetadata(False))

        if action.action_id == "run_log_ingest":
            output = self.tool_runner("security.run_ingest", {})
            return ("executed", True, output, RollbackMetadata(False))

        if action.action_id == "notify_operator":
            message = str(request.payload.get("message", "Operator notification requested"))
            channel = str(request.payload.get("channel", "local-audit"))
            output = {
                "notified": True,
                "channel": channel,
                "message": message,
                "timestamp": _utc_now(),
            }
            return ("executed", True, output, RollbackMetadata(False))

        if action.action_id == "prepare_quarantine_request":
            output = {
                "prepared": True,
                "artifact": request.payload.get("artifact", ""),
                "reason": request.payload.get("reason", ""),
            }
            rollback = RollbackMetadata(
                rollback_possible=True,
                rollback_action="cancel_quarantine_request",
                instructions=["Mark request as cancelled in incident tracker"],
            )
            return ("prepared", False, output, rollback)

        if action.action_id == "prepare_service_disable_request":
            output = {
                "prepared": True,
                "service": request.payload.get("service", ""),
                "reason": request.payload.get("reason", ""),
            }
            rollback = RollbackMetadata(
                rollback_possible=True,
                rollback_action="cancel_service_disable_request",
                instructions=["Clear pending service-disable change request"],
            )
            return ("prepared", False, output, rollback)

        if action.action_id == "prepare_secret_rotation_request":
            output = {
                "prepared": True,
                "secret_name": request.payload.get("secret_name", ""),
                "reason": request.payload.get("reason", ""),
            }
            rollback = RollbackMetadata(
                rollback_possible=True,
                rollback_action="cancel_secret_rotation_request",
                instructions=["Cancel rotation ticket and invalidate request reference"],
            )
            return ("prepared", False, output, rollback)

        return (
            "rejected",
            False,
            {"error": "Action mapped but no execution handler present"},
            RollbackMetadata(False),
        )

    def _reject(
        self,
        *,
        request: RemediationExecutionRequest,
        action_id: str,
        policy_result: PolicyResult | None,
        reason: str,
        approval_required: bool,
    ) -> RemediationExecutionResult:
        result = RemediationExecutionResult(
            request_id=request.request_id,
            action_id=action_id,
            status="rejected",
            executed=False,
            policy_decision=(policy_result.decision.value if policy_result else "blocked"),
            approval_required=approval_required,
            approval_state=self._approval_state(request.approval),
            reason=reason,
            output={"error": reason},
            rollback=RollbackMetadata(False),
        )
        return self._audit_and_attach(request=request, policy_result=policy_result, result=result)

    def _audit_and_attach(
        self,
        *,
        request: RemediationExecutionRequest,
        policy_result: PolicyResult | None,
        result: RemediationExecutionResult,
    ) -> RemediationExecutionResult:
        redacted_payload = redact_policy_payload(
            request.payload,
            patterns=self.policy.config.redaction_patterns,
        )
        raw_evidence = {
            "request_id": request.request_id,
            "action_id": result.action_id,
            "status": result.status,
            "executed": result.executed,
            "reason": result.reason,
            "approval_state": result.approval_state,
            "approval_required": result.approval_required,
            "policy_decision": result.policy_decision,
            "payload": redacted_payload,
            "rollback": asdict(result.rollback),
        }
        bundle = self.evidence_manager.create_bundle(
            source=f"executor:{result.action_id}",
            raw_items=raw_evidence,
        )

        event = AuditEvent(
            event_id=next_id("event"),
            event_type=f"remediation.{result.status}",
            actor=request.actor,
            payload={
                "request_id": request.request_id,
                "action_id": result.action_id,
                "policy": (
                    {
                        "decision": policy_result.decision.value,
                        "reason": policy_result.reason,
                        "mode": policy_result.mode.value,
                        "category": policy_result.category.value,
                    }
                    if policy_result
                    else {"decision": "blocked", "reason": result.reason}
                ),
                "approval_state": result.approval_state,
                "executed": result.executed,
                "rollback": asdict(result.rollback),
                "evidence_bundle_id": bundle.bundle_id,
            },
            evidence_bundle_id=bundle.bundle_id,
        )
        stored_event = self.audit_ledger.append_event(event)
        result.audit_event_id = stored_event.event_id
        result.evidence_bundle_id = bundle.bundle_id
        return result

    @staticmethod
    def _approval_state(approval: ExecutionApproval | None) -> str:
        if approval is None:
            return "missing"
        return "approved" if approval.approved else "rejected"

    @staticmethod
    def _is_path_unsafe(target: str) -> bool:
        try:
            path = Path(target)
        except Exception:
            return True
        if ".." in path.parts:
            return True
        disallowed_roots = ("/usr", "/boot", "/ostree")
        normalized = str(path)
        return any(normalized.startswith(root) for root in disallowed_roots)

    @staticmethod
    def _has_unsafe_shell_content(payload: dict[str, Any]) -> bool:
        for value in _flatten_values(payload):
            if not isinstance(value, str):
                continue
            if _UNSAFE_SHELL_PATTERN.search(value):
                return True
        return False

    @staticmethod
    def _has_raw_secret_material(payload: dict[str, Any]) -> bool:
        for value in _flatten_values(payload):
            if not isinstance(value, str):
                continue
            lowered = value.lower()
            if any(token in lowered for token in ("api_key=", "token=", "password=", "secret=")):
                return True
        return False


def _flatten_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        out: list[Any] = []
        for child in value.values():
            out.extend(_flatten_values(child))
        return out
    if isinstance(value, list):
        out: list[Any] = []
        for child in value:
            out.extend(_flatten_values(child))
        return out
    return [value]
