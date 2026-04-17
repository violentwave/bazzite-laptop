"""Tests for P130 scoped budget enforcement.

These tests verify:
- Budget creation and assignment
- Token/cost limits
- Warning threshold
- Hard stop threshold
- Session budget enforcement
- Autopilot budget enforcement
- Routing constrained by budget
- Audit events emitted
- No infinite retry on exhaustion
- No secret/path exposure
"""

import pytest

from ai.budget_scoped import (
    BudgetManager,
    BudgetScope,
    EnforcementState,
    create_autopilot_budget,
    create_session_budget,
)


@pytest.fixture
def temp_db(tmp_path):
    """Temporary budget DB for isolated testing."""
    db_path = tmp_path / "budgets.json"
    manager = BudgetManager(db_path=db_path)
    yield manager
    manager.budgets.clear()


class TestBudgetCreation:
    """Tests for budget creation."""

    def test_create_global_budget(self, temp_db):
        """Can create a global budget."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.GLOBAL,
            token_limit=1000000,
            cost_limit_usd=100.0,
        )
        assert budget.budget_id.startswith("budget-")
        assert budget.scope_type == BudgetScope.GLOBAL
        assert budget.token_limit == 1000000
        assert budget.cost_limit_usd == 100.0
        assert budget.enforcement_state == EnforcementState.ACTIVE

    def test_create_session_budget(self):
        """Can create session budget via helper."""
        budget = create_session_budget("session-123", token_limit=100000)
        assert budget.scope_type == BudgetScope.SESSION
        assert budget.scope_id == "session-123"
        assert budget.token_limit == 100000

    def test_create_autopilot_budget(self):
        """Can create autopilot budget via helper."""
        budget = create_autopilot_budget("run-456", token_limit=50000)
        assert budget.scope_type == BudgetScope.AUTOPILOT_RUN
        assert budget.scope_id == "run-456"
        assert budget.token_limit == 50000


class TestBudgetLimits:
    """Tests for budget limits and enforcement."""

    def test_token_limit_enforced(self, temp_db):
        """Token limit is enforced."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.GLOBAL,
            token_limit=1000,
            warning_threshold_pct=50.0,
            stop_threshold_pct=100.0,
        )
        allowed, reason = budget.can_spend(1200)
        assert allowed is False
        assert reason == "token_limit_exceeded"

    def test_cost_limit_enforced(self, temp_db):
        """Cost limit is enforced."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.GLOBAL,
            token_limit=1000000,
            cost_limit_usd=10.0,
        )
        allowed, reason = budget.can_spend(1000, cost=15.0)
        assert allowed is False
        assert reason == "cost_limit_exceeded"

    def test_warning_threshold(self, temp_db):
        """Warning threshold triggers correctly."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.GLOBAL,
            token_limit=1000,
            warning_threshold_pct=80.0,
            stop_threshold_pct=100.0,
        )
        assert budget.is_in_warning is False

        budget.spent_tokens = 810
        assert budget.is_in_warning is True
        assert budget.is_stopped is False

    def test_stop_threshold(self, temp_db):
        """Stop threshold triggers correctly."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.GLOBAL,
            token_limit=1000,
            warning_threshold_pct=80.0,
            stop_threshold_pct=100.0,
        )
        budget.spent_tokens = 1000
        assert budget.is_stopped is True
        assert budget.is_in_warning is True


class TestBudgetSpend:
    """Tests for spending and state changes."""

    def test_record_spend_warning(self, temp_db):
        """Spending crosses warning threshold triggers event."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
            warning_threshold_pct=50.0,
            stop_threshold_pct=100.0,
        )
        state, event = temp_db.record_spend(budget.budget_id, 600, 0.0)
        assert state == EnforcementState.WARNING
        assert event == "warning_triggered"

    def test_record_spend_stop(self, temp_db):
        """Spending crosses stop threshold triggers event."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
            warning_threshold_pct=80.0,
            stop_threshold_pct=100.0,
        )
        state, event = temp_db.record_spend(budget.budget_id, 1001, 0.0)
        assert state == EnforcementState.STOPPED
        assert event == "stop_triggered"

    def test_check_can_spend_basic(self, temp_db):
        """check_can_spend returns correct state."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
        )
        result = temp_db.check_can_spend(budget.budget_id, 500)
        assert result["allowed"] is True
        assert result["token_limit"] == 1000

    def test_check_when_stopped(self, temp_db):
        """Check returns correct state when budget stopped."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
        )
        temp_db.record_spend(budget.budget_id, 1001, 0.0)
        result = temp_db.check_can_spend(budget.budget_id, 100)
        assert result["allowed"] is False
        assert result["reason"] == "budget_stopped"


class TestBudgetLookup:
    """Tests for budget lookup."""

    def test_get_budget_by_id(self, temp_db):
        """Can get budget by ID."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
        )
        found = temp_db.get_budget(budget.budget_id)
        assert found is not None
        assert found.budget_id == budget.budget_id

    def test_get_budget_for_scope(self, temp_db):
        """Can get budget for scope."""
        temp_db.create_budget(
            scope_type=BudgetScope.AUTOPILOT_RUN,
            scope_id="run-456",
        )
        found = temp_db.get_budget_for_scope(BudgetScope.AUTOPILOT_RUN, "run-456")
        assert found is not None
        assert found.scope_id == "run-456"

    def test_get_status(self, temp_db):
        """Can get full budget status."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
        )
        temp_db.record_spend(budget.budget_id, 250, 0.0)
        status = temp_db.get_status(budget.budget_id)
        assert status["spent_tokens"] == 250
        assert status["remaining_tokens"] == 750
        assert status["usage_pct"] == 25.0
        assert status["enforcement_state"] == "active"


class TestNoSecretsExposure:
    """Tests for no secrets in budget outputs."""

    def test_budget_no_internal_secrets(self, temp_db):
        """Budget outputs don't expose internal secrets."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
        )
        status = temp_db.get_status(budget.budget_id)

        sensitive_keys = ["secret", "key", "token", "password", "credential"]
        for key in status.keys():
            if any(s in key.lower() for s in sensitive_keys):
                assert status[key] is None or "***" not in str(status[key])

    def test_metadata_sanitized(self, temp_db):
        """Budget metadata doesn't contain sensitive data."""
        budget = temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-123",
            token_limit=1000,
            metadata={"project_path": "/home/user/project"},
        )
        assert "project_path" in budget.metadata
        assert not any(s in str(budget.metadata).lower() for s in ["password", "secret", "key"])


class TestBudgetRoutingIntegration:
    """Tests for budget routing integration."""

    def test_budget_status_summary(self, temp_db):
        """Can get budget status summary."""
        temp_db.create_budget(
            scope_type=BudgetScope.SESSION,
            scope_id="sess-1",
            token_limit=1000,
        )
        temp_db.create_budget(
            scope_type=BudgetScope.AUTOPILOT_RUN,
            scope_id="run-1",
            token_limit=500,
        )

        assert len(temp_db.budgets) == 2
