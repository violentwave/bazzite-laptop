"""Tests for P132 runbook corpus and safety checks."""

from __future__ import annotations

from ai.workflows.runbooks import (
    default_runbook_docs_dir,
    load_runbook_definitions,
    validate_runbook_docs,
)


def test_runbook_inventory_has_required_flows() -> None:
    definitions = load_runbook_definitions()
    ids = sorted(item.runbook_id for item in definitions)
    assert ids == [
        "phase_execution_handoff",
        "privileged_workbench_actions",
        "provider_outage_failover",
        "remediation_approval_flow",
        "security_incident_triage",
    ]


def test_runbooks_use_explicit_approval_metadata() -> None:
    definitions = load_runbook_definitions()
    assert all(item.approval_required is True for item in definitions)
    assert all(item.approval_state == "pending" for item in definitions)
    assert all(item.execution_mode == "manual-approval" for item in definitions)


def test_runbooks_align_with_policy_dependencies() -> None:
    definitions = {item.runbook_id: item for item in load_runbook_definitions()}

    remediation = definitions["remediation_approval_flow"]
    assert "p122_safe_remediation_runner" in remediation.policy_alignment
    assert "p127_mcp_policy_approval" in remediation.policy_alignment
    assert "p128_stepup_security" in remediation.policy_alignment

    provider = definitions["provider_outage_failover"]
    assert "p131_routing_replay" in provider.policy_alignment


def test_markdown_runbooks_have_no_bypass_or_secret_markers() -> None:
    result = validate_runbook_docs(default_runbook_docs_dir())
    assert result["count"] >= 5
