"""Budget integration for provider routing.

Ensures provider routing respects quota constraints defined in ai/budget_scoped.py.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.budget_scoped import (
    BudgetScope,
    check_budget_and_record,
    get_budget_manager,
)
from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)


class BudgetRoutingGuard:
    """Guard that enforces budget constraints on provider routing."""

    def __init__(self):
        self._manager = get_budget_manager()

    def select_provider_with_budget(
        self,
        providers: list[dict[str, Any]],
        task_class: str,
        estimated_tokens: int,
        session_budget_id: str | None = None,
        autopilot_budget_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Select providers that fit within budget.

        Args:
            providers: List of available provider configs
            task_class: Budget tier (security, scheduled, interactive, coding)
            estimated_tokens: Estimated token count
            session_budget_id: Optional session budget ID
            autopilot_budget_id: Optional autopilot run budget ID

        Returns:
            (filtered_providers, constraint_info)
        """
        constraint_info = {
            "budget_constrained": False,
            "budget_id": None,
            "reason": "no_constraint",
            "remaining_tokens": None,
        }

        budget_id = session_budget_id or autopilot_budget_id

        if budget_id:
            check = self._manager.check_can_spend(budget_id, estimated_tokens)

            if not check["allowed"]:
                constraint_info = {
                    "budget_constrained": True,
                    "budget_id": budget_id,
                    "reason": check["reason"],
                    "remaining_tokens": check.get("remaining_tokens"),
                    "state": check.get("state"),
                }
                logger.warning(
                    "Budget constraint: no valid providers due to %s (budget_id=%s, remaining=%s)",
                    check["reason"],
                    budget_id,
                    check.get("remaining_tokens"),
                )
                return [], constraint_info

            constraint_info = {
                "budget_constrained": False,
                "budget_id": budget_id,
                "reason": "ok",
                "remaining_tokens": check.get("remaining_tokens"),
                "usage_pct": check.get("usage_pct"),
            }

        return providers, constraint_info

    def check_and_record_for_request(
        self,
        budget_id: str | None,
        tokens: int,
        cost_usd: float = 0.0,
    ) -> dict[str, Any]:
        """Check budget and record spend after LLM request.

        Returns dict with:
        - allowed: bool
        - state: enforcement state
        - is_warning: bool
        - is_stopped: bool
        """
        if not budget_id:
            return {"allowed": True, "state": "no_budget"}

        return check_budget_and_record(budget_id, tokens, cost_usd)

    def get_budget_status_summary(self) -> dict[str, Any]:
        """Get summary of all active budgets."""
        manager = get_budget_manager()
        budgets = []

        for budget in manager.budgets.values():
            budgets.append(
                {
                    "budget_id": budget.budget_id,
                    "name": budget.name,
                    "scope_type": budget.scope_type.value,
                    "scope_id": budget.scope_id,
                    "spent_tokens": budget.spent_tokens,
                    "token_limit": budget.token_limit,
                    "remaining_tokens": budget.remaining_tokens,
                    "usage_pct": round(budget.usage_pct, 2),
                    "enforcement_state": budget.enforcement_state.value,
                    "is_warning": budget.is_in_warning,
                    "is_stopped": budget.is_stopped,
                }
            )

        return {
            "total_budgets": len(budgets),
            "budgets": budgets,
        }


_budget_guard: BudgetRoutingGuard | None = None


def get_budget_routing_guard() -> BudgetRoutingGuard:
    """Get global budget routing guard."""
    global _budget_guard
    if _budget_guard is None:
        _budget_guard = BudgetRoutingGuard()
    return _budget_guard


def check_budget_for_operation(
    operation_type: str,
    target_id: str,
    tokens: int,
    cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Check budget for an operation (session, autopilot, etc).

    Args:
        operation_type: 'session' or 'autopilot'
        target_id: session_id or autopilot_run_id
        tokens: tokens to spend
        cost_usd: cost to spend

    Returns:
        dict with allowed, state, is_warning, is_stopped
    """
    manager = get_budget_manager()
    scope = BudgetScope.SESSION if operation_type == "session" else BudgetScope.AUTOPILOT_RUN
    budget = manager.get_budget_for_scope(scope, target_id)

    if not budget:
        return {"allowed": True, "state": "no_budget", "is_warning": False, "is_stopped": False}

    return check_budget_and_record(budget.budget_id, tokens, cost_usd)
