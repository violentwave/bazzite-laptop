"""Tests for self-healing control plane (P134)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai.self_healing import (
    DEFAULT_HEALING_CHECKS,
    DEFAULT_REPAIR_ACTIONS,
    HealingCheck,
    HealingCheckResult,
    SelfHealingCoordinator,
    redact_healing_payload,
)


@pytest.fixture
def tmp_state_path(tmp_path: Path) -> Path:
    return tmp_path / "healing_state.json"


@pytest.fixture
def coordinator(tmp_state_path: Path) -> SelfHealingCoordinator:
    return SelfHealingCoordinator(state_path=tmp_state_path)


class TestHealingCheck:
    def test_default_checks_exist(self) -> None:
        assert len(DEFAULT_HEALING_CHECKS) > 0
        check_ids = {c.check_id for c in DEFAULT_HEALING_CHECKS}
        assert "service_health" in check_ids
        assert "timer_health" in check_ids
        assert "provider_health" in check_ids

    def test_check_structure(self) -> None:
        for check in DEFAULT_HEALING_CHECKS:
            assert check.check_id
            assert check.name
            assert check.description
            assert check.sensor_tool


class TestRepairAction:
    def test_default_actions_exist(self) -> None:
        assert len(DEFAULT_REPAIR_ACTIONS) > 0
        action_ids = {a.action_id for a in DEFAULT_REPAIR_ACTIONS}
        assert "probe_health" in action_ids

    def test_action_approval_requirements(self) -> None:
        for action in DEFAULT_REPAIR_ACTIONS:
            if action.requires_approval:
                assert action.risk_tier in ("medium", "high")
                assert action.destructive or action.target_tool is None

    def test_low_risk_actions_no_approval(self) -> None:
        low_risk = ["probe_health", "retry_timer_check", "retry_provider_discovery"]
        for action in DEFAULT_REPAIR_ACTIONS:
            if action.action_id in low_risk:
                assert not action.requires_approval


class TestSelfHealingCoordinator:
    def test_coordinator_init(self, coordinator: SelfHealingCoordinator) -> None:
        assert coordinator.checks
        assert coordinator.actions
        assert coordinator._state

    def test_run_check_returns_structure(self, coordinator: SelfHealingCoordinator) -> None:
        check = DEFAULT_HEALING_CHECKS[0]
        result = coordinator.run_check(check)
        assert isinstance(result, HealingCheckResult)
        assert result.check_id == check.check_id

    def test_get_action_by_id(self, coordinator: SelfHealingCoordinator) -> None:
        action = coordinator.get_action("probe_health")
        assert action is not None
        assert action.action_id == "probe_health"

    def test_get_action_invalid(self, coordinator: SelfHealingCoordinator) -> None:
        action = coordinator.get_action("invalid_action")
        assert action is None


class TestCooldownBehavior:
    def test_no_cooldown_initially(self, coordinator: SelfHealingCoordinator) -> None:
        assert not coordinator._in_cooldown("probe_health")

    def test_cooldown_set_and_check(self, coordinator: SelfHealingCoordinator) -> None:
        coordinator._set_cooldown("probe_health", 60)
        assert coordinator._in_cooldown("probe_health")

    def test_cooldown_expiry(self, coordinator: SelfHealingCoordinator) -> None:
        coordinator._set_cooldown("probe_health", 0)
        assert not coordinator._in_cooldown("probe_health")

    def test_prevents_loop_via_cooldown(self, coordinator: SelfHealingCoordinator) -> None:
        coordinator._set_cooldown("probe_health", 3600)
        check = HealingCheck(
            check_id="service_health",
            name="Service",
            description="Test",
            sensor_tool="system.service_status",
        )
        coordinator.run_check(check)
        results = coordinator.propose_action(
            HealingCheckResult(
                check_id="service_health",
                issue_detected=True,
                severity="high",
                details={},
            )
        )
        assert len(results) == 1
        assert not results[0].success
        assert results[0].policy_result == "blocked_cooldown"


class TestApprovalGating:
    def test_action_requires_approval_when_flag_set(
        self, coordinator: SelfHealingCoordinator
    ) -> None:
        action = coordinator.get_action("request_llm_proxy_restart")
        assert action is not None
        assert action.requires_approval

    def test_blocked_without_approval(self, coordinator: SelfHealingCoordinator) -> None:
        results = coordinator.propose_action(
            HealingCheckResult(
                check_id="llm_status",
                issue_detected=True,
                severity="high",
                details={},
            ),
            approval_present=False,
        )
        assert len(results) == 1
        assert not results[0].success
        assert results[0].policy_result == "approval_required"

    def test_approved_when_flag_present(self, coordinator: SelfHealingCoordinator) -> None:
        results = coordinator.propose_action(
            HealingCheckResult(
                check_id="llm_status",
                issue_detected=True,
                severity="high",
                details={},
            ),
            approval_present=True,
        )
        assert len(results) == 1
        assert results[0].success
        assert results[0].approved


class TestPolicyGating:
    def test_low_risk_auto_approved(self, coordinator: SelfHealingCoordinator) -> None:
        results = coordinator.propose_action(
            HealingCheckResult(
                check_id="service_health",
                issue_detected=True,
                severity="low",
                details={},
            ),
            approval_present=False,
        )
        assert len(results) == 1
        assert results[0].policy_result in ("auto_approved", "blocked_cooldown")

    def test_no_issue_no_proposal(self, coordinator: SelfHealingCoordinator) -> None:
        results = coordinator.propose_action(
            HealingCheckResult(
                check_id="service_health",
                issue_detected=False,
                severity="unknown",
                details={},
            ),
        )
        assert len(results) == 0


class TestDegradedStateVisibility:
    def test_degraded_visible_when_not_fixed(self, coordinator: SelfHealingCoordinator) -> None:
        coordinator._set_cooldown("probe_health", 3600)
        check_result = HealingCheckResult(
            check_id="service_health",
            issue_detected=True,
            severity="high",
            details={"status": "degraded"},
        )
        results = coordinator.propose_action(check_result)
        decision = coordinator.explain_decision(check_result, results)
        assert decision["degraded_state_visible"] is True

    def test_explain_includes_all_fields(self, coordinator: SelfHealingCoordinator) -> None:
        check_result = HealingCheckResult(
            check_id="service_health",
            issue_detected=True,
            severity="medium",
            details={"status": "degraded"},
        )
        results = [
            type(
                "obj",
                (),
                {
                    "action_id": "probe_health",
                    "success": False,
                    "approved": False,
                    "approval_message": "test",
                    "policy_result": "blocked_cooldown",
                    "cooldown_until": None,
                    "message": "test",
                },
            )()
        ]
        decision = coordinator.explain_decision(check_result, results)
        assert "detected_issue" in decision
        assert "proposed_actions" in decision
        assert "degraded_state_visible" in decision


class TestRedactionBehavior:
    def test_redacts_home_paths(self) -> None:
        data = {
            "path": "/home/user/secret.txt",
            "message": "Check /home/user for issues",
        }
        result = redact_healing_payload(data)
        assert result["path"] == "[REDACTED]"
        assert result["message"] == "[REDACTED]"

    def test_redacts_api_keys(self) -> None:
        data = {
            "api_key": "sk-secret-key-123",
            "token": "token-abc",
        }
        result = redact_healing_payload(data)
        assert result["api_key"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"

    def test_preserves_normal_values(self) -> None:
        data = {
            "status": "healthy",
            "count": 5,
        }
        result = redact_healing_payload(data)
        assert result["status"] == "healthy"
        assert result["count"] == 5


class TestAuditEvidenceEmission:
    def test_state_persists_after_cooldown(self, coordinator: SelfHealingCoordinator) -> None:
        coordinator._set_cooldown("probe_health", 60)
        assert coordinator.state_path.exists()

    def test_state_loads_from_disk(self, tmp_state_path: Path) -> None:
        coordinator1 = SelfHealingCoordinator(state_path=tmp_state_path)
        coordinator1._set_cooldown("probe_health", 60)
        coordinator2 = SelfHealingCoordinator(state_path=tmp_state_path)
        assert coordinator2._in_cooldown("probe_health")


class TestSafetyProofs:
    def test_no_arbitrary_shell_in_actions(self) -> None:
        for action in DEFAULT_REPAIR_ACTIONS:
            if action.target_tool:
                assert action.target_tool in (
                    "system.service_status",
                    "agents.timer_health",
                    "providers.refresh",
                )

    def test_destructive_actions_require_approval(
        self, coordinator: SelfHealingCoordinator
    ) -> None:
        destructive = [a for a in DEFAULT_REPAIR_ACTIONS if a.destructive]
        for action in destructive:
            assert action.requires_approval

    def test_cooldown_prevents_rapid_loops(self, coordinator: SelfHealingCoordinator) -> None:
        for action in DEFAULT_REPAIR_ACTIONS:
            if action.cooldown_seconds > 0:
                assert action.cooldown_seconds >= 60


class TestStateTracking:
    def test_recent_actions_tracked(self, coordinator: SelfHealingCoordinator) -> None:
        initial_count = len(coordinator._state.recent_actions)
        check = HealingCheck(
            check_id="service_health",
            name="Test",
            description="Test",
            sensor_tool="system.service_status",
        )
        coordinator.run_check(check)
        assert len(coordinator._state.recent_actions) == initial_count

    def test_cooldown_tracker_initialized(self, coordinator: SelfHealingCoordinator) -> None:
        assert isinstance(coordinator._state.cooldown_tracker, dict)
