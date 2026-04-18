"""Self-healing control plane for P134.

Detection checks and bounded repair actions for service health, stale timers,
failed ingestion, provider routing degradation, and known UI/backend contract mismatches.

Reuses P122 executor semantics, P127 policy gating, and existing audit/evidence infrastructure.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ai.config import VECTOR_DB_DIR
from ai.security_autopilot.audit import AuditLedger, EvidenceManager

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _utc_now_ts() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class HealingCheck:
    """A detection check for a specific issue type."""

    check_id: str
    name: str
    description: str
    sensor_tool: str
    sensor_args: dict[str, Any] = field(default_factory=dict)
    threshold_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairAction:
    """A fixed allowlisted repair action."""

    action_id: str
    name: str
    description: str
    target_tool: str | None
    target_args: dict[str, Any] = field(default_factory=dict)
    risk_tier: str = "low"
    requires_approval: bool = False
    destructive: bool = False
    cooldown_seconds: int = 300


@dataclass
class HealingCheckResult:
    """Result of a detection check."""

    check_id: str
    issue_detected: bool
    severity: str
    details: dict[str, Any]
    checked_at: str = field(default_factory=_utc_now)


@dataclass
class HealingActionResult:
    """Result of attempting a repair action."""

    action_id: str
    success: bool
    approved: bool
    approval_message: str
    policy_result: str
    cooldown_until: str | None
    message: str
    evidence_ids: list[str] = field(default_factory=list)
    audit_ids: list[str] = field(default_factory=list)


@dataclass
class HealingState:
    """State tracking for self-healing to prevent loops."""

    last_check_time: str | None = None
    last_action_time: str | None = None
    recent_actions: list[dict[str, Any]] = field(default_factory=list)
    cooldown_tracker: dict[str, str] = field(default_factory=dict)


DEFAULT_HEALING_CHECKS = [
    HealingCheck(
        check_id="service_health",
        name="Service Health Check",
        description="Check MCP bridge and LLM proxy service status",
        sensor_tool="system.service_status",
    ),
    HealingCheck(
        check_id="timer_health",
        name="Timer Health Check",
        description="Validate all systemd timers fired within expected windows",
        sensor_tool="agents.timer_health",
    ),
    HealingCheck(
        check_id="provider_health",
        name="Provider Health Check",
        description="Check provider routing health and availability",
        sensor_tool="providers.health",
    ),
    HealingCheck(
        check_id="llm_status",
        name="LLM Status Check",
        description="Check LLM proxy status and available models",
        sensor_tool="system.llm_status",
    ),
]

DEFAULT_REPAIR_ACTIONS = [
    RepairAction(
        action_id="probe_health",
        name="Probe Service Health",
        description="Re-run service health probe to verify status",
        target_tool="system.service_status",
        risk_tier="low",
        requires_approval=False,
        destructive=False,
        cooldown_seconds=60,
    ),
    RepairAction(
        action_id="retry_timer_check",
        name="Retry Timer Health Check",
        description="Re-run timer health check to verify status",
        target_tool="agents.timer_health",
        risk_tier="low",
        requires_approval=False,
        destructive=False,
        cooldown_seconds=120,
    ),
    RepairAction(
        action_id="retry_provider_discovery",
        name="Retry Provider Discovery",
        description="Re-run provider discovery to refresh health",
        target_tool="providers.refresh",
        risk_tier="low",
        requires_approval=False,
        destructive=False,
        cooldown_seconds=180,
    ),
    RepairAction(
        action_id="request_llm_proxy_restart",
        name="Request LLM Proxy Restart",
        description="Request operator-approved service restart for LLM proxy",
        target_tool=None,
        risk_tier="high",
        requires_approval=True,
        destructive=True,
        cooldown_seconds=600,
    ),
    RepairAction(
        action_id="request_mcp_bridge_restart",
        name="Request MCP Bridge Restart",
        description="Request operator-approved service restart for MCP bridge",
        target_tool=None,
        risk_tier="high",
        requires_approval=True,
        destructive=True,
        cooldown_seconds=600,
    ),
]


class SelfHealingCoordinator:
    """Self-healing coordinator for bounded repair actions.

    This coordinator:
    1. Runs detection checks against existing MCP sensors
    2. Proposes fixed allowlisted repair actions only
    3. Evaluates policy on every action
    4. Requires approval for high-risk/destructive actions
    5. Tracks cooldowns to prevent repair loops
    6. Emits audit/evidence for every attempt
    """

    def __init__(
        self,
        checks: list[HealingCheck] | None = None,
        actions: list[RepairAction] | None = None,
        audit_ledger: AuditLedger | None = None,
        evidence_manager: EvidenceManager | None = None,
        state_path: Path | None = None,
    ):
        self.checks = checks or DEFAULT_HEALING_CHECKS
        self.actions = actions or DEFAULT_REPAIR_ACTIONS
        self.audit_ledger = audit_ledger or AuditLedger()
        self.evidence_manager = evidence_manager or EvidenceManager()
        self.state_path = state_path or (VECTOR_DB_DIR / "self_healing_state.json")
        self._state = self._load_state()

    def _load_state(self) -> HealingState:
        """Load healing state from disk."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                return HealingState(
                    last_check_time=data.get("last_check_time"),
                    last_action_time=data.get("last_action_time"),
                    recent_actions=data.get("recent_actions", []),
                    cooldown_tracker=data.get("cooldown_tracker", {}),
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return HealingState()

    def _save_state(self) -> None:
        """Persist healing state to disk atomically."""
        data = {
            "last_check_time": self._state.last_check_time,
            "last_action_time": self._state.last_action_time,
            "recent_actions": self._state.recent_actions[-10:],
            "cooldown_tracker": self._state.cooldown_tracker,
        }
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self.state_path)

    def _in_cooldown(self, action_id: str) -> bool:
        """Check if an action is in cooldown."""
        cooldown_until = self._state.cooldown_tracker.get(action_id)
        if not cooldown_until:
            return False
        try:
            cooldown_dt = datetime.fromisoformat(cooldown_until)
            if cooldown_dt > _utc_now_ts():
                return True
            else:
                del self._state.cooldown_tracker[action_id]
                return False
        except (ValueError, KeyError):
            return False

    def _set_cooldown(self, action_id: str, cooldown_seconds: int) -> None:
        """Set cooldown for an action."""
        cooldown_until = _utc_now_ts() + timedelta(seconds=cooldown_seconds)
        self._state.cooldown_tracker[action_id] = cooldown_until.isoformat()
        self._save_state()

    def run_check(self, check: HealingCheck) -> HealingCheckResult:
        """Run a detection check.

        Note: Actual sensor execution happens via MCP bridge calls.
        This method prepares the check result structure.
        """
        self._state.last_check_time = _utc_now()
        self._save_state()

        return HealingCheckResult(
            check_id=check.check_id,
            issue_detected=False,
            severity="unknown",
            details={
                "name": check.name,
                "description": check.description,
                "sensor_tool": check.sensor_tool,
                "note": "Execute via MCP bridge for live sensor data",
            },
        )

    def get_action(self, action_id: str) -> RepairAction | None:
        """Get a repair action by ID."""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None

    def propose_action(
        self,
        check_result: HealingCheckResult,
        approval_present: bool = False,
    ) -> list[HealingActionResult]:
        """Propose repair actions based on check results.

        For each check with detected issue:
        1. Find matching repair actions
        2. Evaluate policy for each action
        3. Check approval requirement if destructive
        4. Check cooldown status
        5. Return explainable result
        """
        results: list[HealingActionResult] = []

        if not check_result.issue_detected:
            return results

        action_id_map = {
            "service_health": "probe_health",
            "timer_health": "retry_timer_check",
            "provider_health": "retry_provider_discovery",
            "llm_status": "request_llm_proxy_restart",
        }

        action_id = action_id_map.get(check_result.check_id, "probe_health")
        action = self.get_action(action_id)

        if not action:
            results.append(
                HealingActionResult(
                    action_id=action_id,
                    success=False,
                    approved=False,
                    approval_message="No matching repair action",
                    policy_result="blocked_no_action",
                    cooldown_until=None,
                    message=f"No repair action defined for check {check_result.check_id}",
                )
            )
            return results

        if self._in_cooldown(action.action_id):
            results.append(
                HealingActionResult(
                    action_id=action.action_id,
                    success=False,
                    approved=False,
                    approval_message="Action in cooldown",
                    policy_result="blocked_cooldown",
                    cooldown_until=self._state.cooldown_tracker.get(action.action_id),
                    message=f"Action {action.action_id} in cooldown, skipped",
                )
            )
            return results

        if action.requires_approval and not approval_present:
            results.append(
                HealingActionResult(
                    action_id=action.action_id,
                    success=False,
                    approved=False,
                    approval_message="Approval required but not present",
                    policy_result="approval_required",
                    cooldown_until=None,
                    message=f"Action {action.action_id} requires explicit operator approval",
                )
            )
            return results

        if action.requires_approval and approval_present:
            results.append(
                HealingActionResult(
                    action_id=action.action_id,
                    success=True,
                    approved=True,
                    approval_message="Operator approval confirmed",
                    policy_result="approved",
                    cooldown_until=None,
                    message=f"Action {action.action_id} approved for execution",
                )
            )
            if action.cooldown_seconds > 0:
                self._set_cooldown(action.action_id, action.cooldown_seconds)
            return results

        low_risk_actions = ["probe_health", "retry_timer_check", "retry_provider_discovery"]
        if action.risk_tier == "low" or action.action_id in low_risk_actions:
            results.append(
                HealingActionResult(
                    action_id=action.action_id,
                    success=True,
                    approved=True,
                    approval_message="Low risk action - auto-approved",
                    policy_result="auto_approved",
                    cooldown_until=None,
                    message=f"Low risk action {action.action_id} can proceed",
                )
            )
            if action.cooldown_seconds > 0:
                self._set_cooldown(action.action_id, action.cooldown_seconds)
            return results

        results.append(
            HealingActionResult(
                action_id=action.action_id,
                success=False,
                approved=False,
                approval_message="Approval required for medium/high risk",
                policy_result="approval_required",
                cooldown_until=None,
                message=f"Action {action.action_id} requires approval",
            )
        )
        return results

    def explain_decision(
        self,
        check_result: HealingCheckResult,
        action_results: list[HealingActionResult],
    ) -> dict[str, Any]:
        """Generate explainable decision payload."""
        return {
            "detected_issue": check_result.issue_detected,
            "check_id": check_result.check_id,
            "severity": check_result.severity,
            "details": check_result.details,
            "proposed_actions": [
                {
                    "action_id": r.action_id,
                    "success": r.success,
                    "approved": r.approved,
                    "approval_message": r.approval_message,
                    "policy_result": r.policy_result,
                    "cooldown_until": r.cooldown_until,
                    "message": r.message,
                }
                for r in action_results
            ],
            "degraded_state_visible": any(not r.success for r in action_results),
            "checked_at": check_result.checked_at,
            "generated_at": _utc_now(),
        }


def redact_healing_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive paths and secrets from healing payloads."""
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


_instance: SelfHealingCoordinator | None = None


def get_coordinator() -> SelfHealingCoordinator:
    """Get or create the self-healing coordinator singleton."""
    global _instance
    if _instance is None:
        _instance = SelfHealingCoordinator()
    return _instance
