"""Tests for P133 provenance graph inserts, links, and scoped retrieval."""

from __future__ import annotations

from pathlib import Path

from ai.provenance import ProvenanceGraph


def _graph(tmp_path: Path) -> ProvenanceGraph:
    return ProvenanceGraph(db_path=tmp_path / "vector-db")


def test_security_chain_insert_and_explain(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    ids = graph.record_security_execution(
        incident_id="incident-123",
        finding_id="finding-123",
        evidence_bundle_id="bundle-123",
        recommendation_id="recommendation-123",
        action_id="action-123",
        execution_id="exec-123",
        audit_event_id="event-123",
        policy_decision="approval_required",
        workspace_id="ws-alpha",
        actor_id="actor-alpha",
        project_id="proj-alpha",
        session_id="session-alpha",
        phase="P133",
    )

    assert ids["incident_id"] == "incident-123"
    timeline = graph.query_timeline(workspace_id="ws-alpha", actor_id="actor-alpha", limit=20)
    types = {row["record_type"] for row in timeline["timeline"]}
    assert "incident" in types
    assert "evidence_bundle" in types
    assert "execution_record" in types

    explanation = graph.explain_record(
        record_id="incident-123",
        workspace_id="ws-alpha",
        actor_id="actor-alpha",
        project_id="proj-alpha",
    )
    assert explanation["found"] is True
    assert explanation["evidence_supported"]
    assert any(item["relation"] == "supported_by" for item in explanation["why"])


def test_workbench_change_chain_and_what_changed(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    result = graph.record_workbench_session_change(
        session_id="sess-42",
        git_diff="modified ai/provenance.py",
        test_summary={"summary": "pytest passed 4 tests", "passed": 4},
        artifacts=["docs/evidence/p133/validation.md", "HANDOFF.md"],
        handoff_summary="Recorded P133 evidence and handoff",
        workspace_id="ws-beta",
        actor_id="actor-beta",
        project_id="proj-beta",
        phase="P133",
    )

    assert result["session_id"] == "sess-42"
    assert len(result["artifact_ids"]) == 2

    changed = graph.query_what_changed(
        workspace_id="ws-beta",
        actor_id="actor-beta",
        project_id="proj-beta",
        session_id="sess-42",
    )
    changed_types = {item["record_type"] for item in changed["changes"]}
    assert "git_diff" in changed_types
    assert "test_result" in changed_types
    assert "artifact" in changed_types
    assert "handoff_note" in changed_types


def test_phase_artifact_links(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    payload = graph.record_phase_artifacts(
        phase="P133",
        artifact_paths=["docs/P133_PLAN.md"],
        evidence_paths=["docs/evidence/p133/validation.md"],
        workspace_id="ws-gamma",
        actor_id="actor-gamma",
        project_id="proj-gamma",
    )
    assert payload["phase_record_id"] == "P133"

    explained = graph.explain_record(
        record_id="P133",
        workspace_id="ws-gamma",
        actor_id="actor-gamma",
        project_id="proj-gamma",
    )
    assert explained["found"] is True
    relations = {edge["relation"] for edge in explained["why"]}
    assert "generated_artifact" in relations
    assert "generated_evidence" in relations


def test_scope_isolation_blocks_cross_workspace_reads(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    graph.create_record(
        record_type="incident",
        title="alpha incident",
        workspace_id="ws-alpha",
        actor_id="actor-a",
        project_id="proj-a",
    )
    graph.create_record(
        record_type="incident",
        title="beta incident",
        workspace_id="ws-beta",
        actor_id="actor-b",
        project_id="proj-b",
    )

    alpha = graph.query_timeline(workspace_id="ws-alpha")
    beta = graph.query_timeline(workspace_id="ws-beta")
    assert all(item["attribution"]["workspace_id"] == "ws-alpha" for item in alpha["timeline"])
    assert all(item["attribution"]["workspace_id"] == "ws-beta" for item in beta["timeline"])


def test_redaction_removes_secrets_and_sensitive_paths(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    graph.create_record(
        record_type="artifact",
        title="contains secret",
        summary="token=SUPERSECRET in /var/home/lch/projects/bazzite-laptop/private.txt",
        payload={
            "secret": "api_key=ABC123",
            "path": "/var/home/lch/projects/bazzite-laptop/.config/local.env",
        },
        workspace_id="ws-redact",
        actor_id="actor-redact",
    )

    result = graph.query_timeline(workspace_id="ws-redact", actor_id="actor-redact")
    serialized = str(result)
    assert "SUPERSECRET" not in serialized
    assert "ABC123" not in serialized
    assert "/var/home/lch/projects" not in serialized
    assert "[PATH_REDACTED]" in serialized
