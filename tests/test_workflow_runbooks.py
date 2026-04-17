"""Tests for machine-readable runbook workflow integration (P132)."""

from __future__ import annotations

import pytest

from ai.workflows.runbooks import get_runbook_registry, load_runbook_definitions


def test_runbook_registry_is_materialized() -> None:
    registry = get_runbook_registry()
    assert len(registry) == 5
    assert "security_incident_triage" in registry
    assert "remediation_approval_flow" in registry


def test_workflow_plan_steps_have_unique_ids() -> None:
    for definition in load_runbook_definitions():
        step_ids = [step["id"] for step in definition.workflow_plan]
        assert len(step_ids) == len(set(step_ids))


def test_manual_approval_step_present_in_each_runbook() -> None:
    for definition in load_runbook_definitions():
        assert any(step.get("manual_approval") is True for step in definition.operator_steps)


def test_escalation_and_verification_are_explicit() -> None:
    for definition in load_runbook_definitions():
        escalation = definition.escalation
        assert escalation.get("owner_role")
        assert escalation.get("conditions")
        assert definition.verification


@pytest.mark.asyncio
async def test_workflow_list_surfaces_runbook_metadata() -> None:
    from ai.mcp_bridge.handlers.workflow_tools import workflow_list

    result = await workflow_list({})
    assert "runbooks" in result
    assert any(entry["runbook_id"] == "remediation_approval_flow" for entry in result["runbooks"])


@pytest.mark.asyncio
async def test_workflow_run_returns_manual_required_for_runbook() -> None:
    from ai.mcp_bridge.handlers.workflow_tools import workflow_run

    result = await workflow_run({"name": "phase_execution_handoff", "triggered_by": "test"})
    assert result["status"] == "manual_required"
    assert result["approval_required"] is True
    assert result["approval_state"] == "pending"
    assert result["operator_steps"]
