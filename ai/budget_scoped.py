"""Budget model for P130 — Cost Quotas and Budget Automation.

This module provides scoped budget enforcement across providers,
Security Autopilot analysis, and Agent Workbench sessions.

Budget scopes:
- global: system-wide provider budget
- workspace: workspace-level budget
- project: project-specific budget
- session: workbench session budget
- autopilot_run: Security Autopilot analysis run budget
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

BUDGET_DB_PATH = Path.home() / ".config" / "bazzite-ai" / "budgets.json"
AUDIT_LOG_PATH = Path.home() / ".config" / "bazzite-ai" / "budget-audit.jsonl"


class BudgetScope(StrEnum):
    """Budget scope types."""

    GLOBAL = "global"
    WORKSPACE = "workspace"
    PROJECT = "project"
    SESSION = "session"
    AUTOPILOT_RUN = "autopilot_run"


class EnforcementState(StrEnum):
    """Budget enforcement state."""

    ACTIVE = "active"
    WARNING = "warning"
    STOPPED = "stopped"
    EXHAUSTED = "exhausted"


class AuditEventType(StrEnum):
    """Budget audit event types."""

    CREATED = "budget_created"
    ASSIGNED = "budget_assigned"
    WARNING_TRIGGERED = "warning_triggered"
    STOP_TRIGGERED = "stop_triggered"
    ROUTING_CONSTRAINED = "routing_constrained"
    STATE_CHANGED = "state_changed"


@dataclass
class Budget:
    """Canonical budget model."""

    budget_id: str
    scope_type: BudgetScope
    scope_id: str | None = None
    name: str = ""
    token_limit: int = 0
    cost_limit_usd: float = 0.0
    spent_tokens: int = 0
    spent_cost_usd: float = 0.0
    warning_threshold_pct: float = 80.0
    stop_threshold_pct: float = 100.0
    enforcement_state: EnforcementState = EnforcementState.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_tokens(self) -> int:
        """Remaining token budget."""
        return max(0, self.token_limit - self.spent_tokens)

    @property
    def remaining_cost_usd(self) -> float:
        """Remaining cost budget."""
        return max(0.0, self.cost_limit_usd - self.spent_cost_usd)

    @property
    def usage_pct(self) -> float:
        """Percentage of budget used."""
        if self.token_limit <= 0:
            return 0.0
        return (self.spent_tokens / self.token_limit) * 100

    @property
    def is_in_warning(self) -> bool:
        """Whether budget is in warning state."""
        return self.usage_pct >= self.warning_threshold_pct

    @property
    def is_stopped(self) -> bool:
        """Whether budget is stopped."""
        return self.usage_pct >= self.stop_threshold_pct

    def can_spend(self, tokens: int, cost: float = 0.0) -> tuple[bool, str]:
        """Check if budget can cover this spend.

        Returns:
            (allowed, reason) tuple
        """
        if self.enforcement_state == EnforcementState.STOPPED:
            return False, "budget_stopped"

        if self.enforcement_state == EnforcementState.EXHAUSTED:
            return False, "budget_exhausted"

        new_tokens = self.spent_tokens + tokens
        new_cost = self.spent_cost_usd + cost

        if self.token_limit > 0 and new_tokens > self.token_limit:
            return False, "token_limit_exceeded"

        if self.cost_limit_usd > 0 and new_cost > self.cost_limit_usd:
            return False, "cost_limit_exceeded"

        if self.usage_pct >= self.warning_threshold_pct:
            return True, "warning"

        return True, "ok"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        data = asdict(self)
        data["scope_type"] = self.scope_type.value
        data["enforcement_state"] = self.enforcement_state.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Budget:
        """Create from dict."""
        data = data.copy()
        data["scope_type"] = BudgetScope(data.get("scope_type", "global"))
        data["enforcement_state"] = EnforcementState(data.get("enforcement_state", "active"))
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class BudgetManager:
    """Manages budgets across scopes."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or BUDGET_DB_PATH
        self.budgets: dict[str, Budget] = {}
        self._load()

    def _load(self) -> None:
        """Load budgets from disk."""
        if not self.db_path.exists():
            return
        try:
            data = json.loads(self.db_path.read_text())
            for budget_data in data.get("budgets", []):
                budget = Budget.from_dict(budget_data)
                self.budgets[budget.budget_id] = budget
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load budgets: %s", e)

    def _save(self) -> None:
        """Save budgets to disk atomically."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.db_path.with_suffix(".json.tmp")
        data = {
            "budgets": [b.to_dict() for b in self.budgets.values()],
            "updated_at": datetime.now(UTC).isoformat(),
        }
        tmp_path.write_text(json.dumps(data, indent=2))
        tmp_path.replace(self.db_path)

    def create_budget(
        self,
        scope_type: BudgetScope,
        scope_id: str | None = None,
        name: str = "",
        token_limit: int = 0,
        cost_limit_usd: float = 0.0,
        warning_threshold_pct: float = 80.0,
        stop_threshold_pct: float = 100.0,
        metadata: dict[str, Any] | None = None,
    ) -> Budget:
        """Create a new budget."""
        budget = Budget(
            budget_id=f"budget-{uuid.uuid4().hex[:12]}",
            scope_type=scope_type,
            scope_id=scope_id,
            name=name or f"{scope_type.value}_budget",
            token_limit=token_limit,
            cost_limit_usd=cost_limit_usd,
            warning_threshold_pct=warning_threshold_pct,
            stop_threshold_pct=stop_threshold_pct,
            metadata=metadata or {},
        )
        self.budgets[budget.budget_id] = budget
        self._save()
        self._emit_audit(AuditEventType.CREATED, budget, {"action": "create"})
        return budget

    def get_budget(self, budget_id: str) -> Budget | None:
        """Get budget by ID."""
        return self.budgets.get(budget_id)

    def get_budget_for_scope(self, scope_type: BudgetScope, scope_id: str | None) -> Budget | None:
        """Get budget for a specific scope."""
        for budget in self.budgets.values():
            if budget.scope_type == scope_type and budget.scope_id == scope_id:
                return budget
        return None

    def assign_budget(self, target_id: str, budget_id: str) -> bool:
        """Assign budget to a target (session, project, etc.)."""
        budget = self.get_budget(budget_id)
        if budget is None:
            return False
        self._emit_audit(AuditEventType.ASSIGNED, budget, {"target_id": target_id})
        return True

    def record_spend(
        self,
        budget_id: str,
        tokens: int,
        cost_usd: float = 0.0,
    ) -> tuple[EnforcementState, str]:
        """Record spend and return enforcement state + event.

        Returns:
            (new_state, event_type)
        """
        budget = self.get_budget(budget_id)
        if budget is None:
            return EnforcementState.ACTIVE, "no_budget"

        old_state = budget.enforcement_state
        budget.spent_tokens += tokens
        budget.spent_cost_usd += cost_usd
        budget.updated_at = datetime.now(UTC)

        new_state = EnforcementState.ACTIVE
        audit_event = AuditEventType.STATE_CHANGED

        if budget.is_stopped:
            new_state = EnforcementState.STOPPED
            audit_event = AuditEventType.STOP_TRIGGERED
        elif budget.is_in_warning and old_state != EnforcementState.WARNING:
            new_state = EnforcementState.WARNING
            audit_event = AuditEventType.WARNING_TRIGGERED

        if new_state != old_state:
            budget.enforcement_state = new_state
            self._emit_audit(
                audit_event,
                budget,
                {
                    "spent_tokens": tokens,
                    "spent_cost_usd": cost_usd,
                },
            )

        self._save()
        return new_state, audit_event.value

    def check_can_spend(self, budget_id: str, tokens: int, cost: float = 0.0) -> dict[str, Any]:
        """Check if budget can cover spend and return state."""
        budget = self.get_budget(budget_id)
        if budget is None:
            return {"allowed": True, "reason": "no_budget", "state": "active"}

        allowed, reason = budget.can_spend(tokens, cost)
        return {
            "allowed": allowed,
            "reason": reason,
            "state": budget.enforcement_state.value,
            "budget_id": budget_id,
            "spent_tokens": budget.spent_tokens,
            "token_limit": budget.token_limit,
            "remaining_tokens": budget.remaining_tokens,
            "usage_pct": round(budget.usage_pct, 2),
        }

    def get_status(self, budget_id: str) -> dict[str, Any]:
        """Get full budget status."""
        budget = self.get_budget(budget_id)
        if budget is None:
            return {"error": "budget_not_found"}

        return {
            "budget_id": budget.budget_id,
            "name": budget.name,
            "scope_type": budget.scope_type.value,
            "scope_id": budget.scope_id,
            "spent_tokens": budget.spent_tokens,
            "token_limit": budget.token_limit,
            "remaining_tokens": budget.remaining_tokens,
            "spent_cost_usd": round(budget.spent_cost_usd, 4),
            "cost_limit_usd": round(budget.cost_limit_usd, 4),
            "usage_pct": round(budget.usage_pct, 2),
            "enforcement_state": budget.enforcement_state.value,
            "is_warning": budget.is_in_warning,
            "is_stopped": budget.is_stopped,
            "updated_at": budget.updated_at.isoformat(),
        }

    def _emit_audit(
        self, event_type: AuditEventType, budget: Budget, extra: dict[str, Any]
    ) -> None:
        """Emit audit event."""
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "event_type": event_type.value,
            "budget_id": budget.budget_id,
            "scope_type": budget.scope_type.value,
            "scope_id": budget.scope_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **extra,
        }
        with AUDIT_LOG_PATH.open("a") as f:
            f.write(json.dumps(event) + "\n")

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Get recent audit events."""
        if not AUDIT_LOG_PATH.exists():
            return []
        try:
            lines = AUDIT_LOG_PATH.read_text().strip().split("\n")
            return [json.loads(line) for line in lines[-limit:]]
        except (json.JSONDecodeError, OSError):
            return []


_budget_manager: BudgetManager | None = None


def get_budget_manager() -> BudgetManager:
    """Get global budget manager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager()
    return _budget_manager


def create_session_budget(
    session_id: str,
    token_limit: int = 100000,
    cost_limit_usd: float = 0.0,
    warning_threshold_pct: float = 80.0,
) -> Budget:
    """Create a budget for a workbench session."""
    manager = get_budget_manager()
    return manager.create_budget(
        scope_type=BudgetScope.SESSION,
        scope_id=session_id,
        name=f"session_{session_id[:12]}",
        token_limit=token_limit,
        cost_limit_usd=cost_limit_usd,
        warning_threshold_pct=warning_threshold_pct,
    )


def create_autopilot_budget(
    run_id: str,
    token_limit: int = 50000,
    cost_limit_usd: float = 0.0,
    warning_threshold_pct: float = 80.0,
) -> Budget:
    """Create a budget for a Security Autopilot run."""
    manager = get_budget_manager()
    return manager.create_budget(
        scope_type=BudgetScope.AUTOPILOT_RUN,
        scope_id=run_id,
        name=f"autopilot_{run_id[:12]}",
        token_limit=token_limit,
        cost_limit_usd=cost_limit_usd,
        warning_threshold_pct=warning_threshold_pct,
    )


def check_budget_and_record(
    budget_id: str,
    tokens: int,
    cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Check budget and record spend in one operation."""
    manager = get_budget_manager()
    check_result = manager.check_can_spend(budget_id, tokens, cost_usd)

    if check_result["allowed"]:
        state, event = manager.record_spend(budget_id, tokens, cost_usd)
        check_result["new_state"] = state.value
        check_result["event"] = event

    return check_result
