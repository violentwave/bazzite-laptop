"""Provenance graph for incidents, actions, sessions, artifacts, and phases.

P133 stores a scoped provenance graph in the existing LanceDB backend so the
control plane can explain what happened, why it happened, what evidence backed
it, which tool/session produced it, and what changed.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from ai.config import VECTOR_DB_DIR

_PATH_PATTERN = re.compile(r"(?:(?:/var/home|/home|~)/[^\s\"'`]+)")
_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+")

_NODES_TABLE = "provenance_nodes"
_EDGES_TABLE = "provenance_edges"

logger = logging.getLogger(__name__)

_NODE_SCHEMA = pa.schema(
    [
        pa.field("record_id", pa.string()),
        pa.field("record_type", pa.string()),
        pa.field("title", pa.string()),
        pa.field("summary", pa.string()),
        pa.field("payload_json", pa.string()),
        pa.field("workspace_id", pa.string()),
        pa.field("actor_id", pa.string()),
        pa.field("project_id", pa.string()),
        pa.field("session_id", pa.string()),
        pa.field("phase", pa.string()),
        pa.field("source_tool", pa.string()),
        pa.field("created_at", pa.string()),
    ]
)

_EDGE_SCHEMA = pa.schema(
    [
        pa.field("edge_id", pa.string()),
        pa.field("from_record_id", pa.string()),
        pa.field("to_record_id", pa.string()),
        pa.field("relation", pa.string()),
        pa.field("rationale", pa.string()),
        pa.field("metadata_json", pa.string()),
        pa.field("workspace_id", pa.string()),
        pa.field("actor_id", pa.string()),
        pa.field("project_id", pa.string()),
        pa.field("session_id", pa.string()),
        pa.field("phase", pa.string()),
        pa.field("source_tool", pa.string()),
        pa.field("created_at", pa.string()),
    ]
)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


class ProvenanceGraph:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or VECTOR_DB_DIR
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._nodes = None
        self._edges = None
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        listing = self._db.list_tables()
        if hasattr(listing, "tables"):
            table_names = set(getattr(listing, "tables", []))
        else:
            table_names = set(listing)
        if _NODES_TABLE in table_names:
            self._nodes = self._db.open_table(_NODES_TABLE)
        else:
            self._nodes = self._db.create_table(_NODES_TABLE, schema=_NODE_SCHEMA)

        if _EDGES_TABLE in table_names:
            self._edges = self._db.open_table(_EDGES_TABLE)
        else:
            self._edges = self._db.create_table(_EDGES_TABLE, schema=_EDGE_SCHEMA)

    def _redact_text(self, text: str) -> str:
        redacted = text
        try:
            from ai.security.inputvalidator import InputValidator

            validator = InputValidator()
            redacted = validator.redact_secrets(redacted)
        except Exception as exc:
            logger.debug("InputValidator redaction unavailable: %s", exc)
        redacted = _SECRET_PATTERN.sub(r"\1=[REDACTED]", redacted)
        return _PATH_PATTERN.sub("[PATH_REDACTED]", redacted)

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact_text(value)
        if isinstance(value, dict):
            return {str(k): self._redact_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        return value

    def _scope_filter(
        self,
        rows: list[dict[str, Any]],
        *,
        workspace_id: str,
        actor_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not workspace_id.strip():
            raise ValueError("workspace_id is required for scoped provenance queries")

        scoped = [row for row in rows if _safe_str(row.get("workspace_id")) == workspace_id]
        if actor_id:
            scoped = [row for row in scoped if _safe_str(row.get("actor_id")) == actor_id]
        if project_id:
            scoped = [row for row in scoped if _safe_str(row.get("project_id")) == project_id]
        if session_id:
            scoped = [row for row in scoped if _safe_str(row.get("session_id")) == session_id]
        return scoped

    @staticmethod
    def _table_rows(table: Any) -> list[dict[str, Any]]:
        frame = table.to_pandas()
        if frame.empty:
            return []
        return frame.to_dict("records")

    def create_record(
        self,
        *,
        record_type: str,
        title: str,
        summary: str = "",
        payload: dict[str, Any] | None = None,
        workspace_id: str,
        actor_id: str = "",
        project_id: str = "",
        session_id: str = "",
        phase: str = "",
        source_tool: str = "",
        record_id: str | None = None,
    ) -> str:
        rid = record_id or f"prov-{uuid.uuid4().hex[:12]}"
        safe_payload = self._redact_value(payload or {})
        row = {
            "record_id": rid,
            "record_type": self._redact_text(record_type),
            "title": self._redact_text(title),
            "summary": self._redact_text(summary),
            "payload_json": json.dumps(safe_payload, sort_keys=True, default=str),
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "project_id": project_id,
            "session_id": session_id,
            "phase": phase,
            "source_tool": self._redact_text(source_tool),
            "created_at": _utc_now(),
        }
        self._nodes.add([row])
        return rid

    def link_records(
        self,
        *,
        from_record_id: str,
        to_record_id: str,
        relation: str,
        rationale: str = "",
        metadata: dict[str, Any] | None = None,
        workspace_id: str,
        actor_id: str = "",
        project_id: str = "",
        session_id: str = "",
        phase: str = "",
        source_tool: str = "",
    ) -> str:
        edge_id = f"edge-{uuid.uuid4().hex[:12]}"
        row = {
            "edge_id": edge_id,
            "from_record_id": from_record_id,
            "to_record_id": to_record_id,
            "relation": self._redact_text(relation),
            "rationale": self._redact_text(rationale),
            "metadata_json": json.dumps(self._redact_value(metadata or {}), sort_keys=True),
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "project_id": project_id,
            "session_id": session_id,
            "phase": phase,
            "source_tool": self._redact_text(source_tool),
            "created_at": _utc_now(),
        }
        self._edges.add([row])
        return edge_id

    def record_security_execution(
        self,
        *,
        incident_id: str | None,
        finding_id: str | None,
        evidence_bundle_id: str,
        recommendation_id: str,
        action_id: str,
        execution_id: str,
        audit_event_id: str,
        policy_decision: str,
        workspace_id: str,
        actor_id: str,
        project_id: str = "",
        session_id: str = "",
        phase: str = "",
        source_tool: str = "security.autopilot_execute",
    ) -> dict[str, str]:
        out: dict[str, str] = {}
        if finding_id:
            out["finding_id"] = self.create_record(
                record_id=finding_id,
                record_type="finding",
                title="Security finding",
                summary="Classifier produced a finding",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        if incident_id:
            out["incident_id"] = self.create_record(
                record_id=incident_id,
                record_type="incident",
                title="Security incident",
                summary="Grouped incident for remediation",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        out["evidence_bundle_id"] = self.create_record(
            record_id=evidence_bundle_id,
            record_type="evidence_bundle",
            title="Evidence bundle",
            summary="Redacted bundle attached to remediation",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        out["recommendation_id"] = self.create_record(
            record_id=recommendation_id,
            record_type="recommendation",
            title="Remediation recommendation",
            summary="Planner recommendation for incident response",
            payload={"policy_decision": policy_decision},
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        out["action_id"] = self.create_record(
            record_id=action_id,
            record_type="approved_action",
            title="Approved action",
            summary="Action selected for execution path",
            payload={"policy_decision": policy_decision},
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        out["execution_id"] = self.create_record(
            record_id=execution_id,
            record_type="execution_record",
            title="Remediation execution",
            summary="Executor result recorded",
            payload={"policy_decision": policy_decision},
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        out["audit_event_id"] = self.create_record(
            record_id=audit_event_id,
            record_type="audit_event",
            title="Audit ledger event",
            summary="Append-only audit record",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        if finding_id and incident_id:
            self.link_records(
                from_record_id=finding_id,
                to_record_id=incident_id,
                relation="grouped_into",
                rationale="Classifier grouped finding into incident",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        if incident_id:
            self.link_records(
                from_record_id=incident_id,
                to_record_id=evidence_bundle_id,
                relation="supported_by",
                rationale="Incident linked to evidence bundle",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        self.link_records(
            from_record_id=evidence_bundle_id,
            to_record_id=recommendation_id,
            relation="supports_recommendation",
            rationale="Evidence informed recommendation",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        self.link_records(
            from_record_id=recommendation_id,
            to_record_id=action_id,
            relation="approved_as",
            rationale="Recommendation approved as action",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        self.link_records(
            from_record_id=action_id,
            to_record_id=execution_id,
            relation="executed_as",
            rationale="Action produced execution record",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        self.link_records(
            from_record_id=execution_id,
            to_record_id=audit_event_id,
            relation="audited_by",
            rationale="Execution written to audit ledger",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        return out

    def record_workbench_session_change(
        self,
        *,
        session_id: str,
        git_diff: str,
        test_summary: dict[str, Any],
        artifacts: list[str],
        handoff_summary: str,
        workspace_id: str,
        actor_id: str,
        project_id: str = "",
        phase: str = "",
        source_tool: str = "workbench.session",
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        session_record_id = self.create_record(
            record_id=session_id,
            record_type="workbench_session",
            title="Workbench session",
            summary="Session context for code/test work",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        result["session_id"] = session_record_id

        git_id = self.create_record(
            record_type="git_diff",
            title="Git diff summary",
            summary=git_diff,
            payload={"diff": git_diff},
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        result["git_diff_id"] = git_id
        self.link_records(
            from_record_id=session_record_id,
            to_record_id=git_id,
            relation="captured_diff",
            rationale="Session captured current diff",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        test_id = self.create_record(
            record_type="test_result",
            title="Test execution summary",
            summary=test_summary.get("summary", "Workbench tests executed"),
            payload=test_summary,
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        result["test_result_id"] = test_id
        self.link_records(
            from_record_id=session_record_id,
            to_record_id=test_id,
            relation="ran_tests",
            rationale="Session executed tests",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        artifact_ids: list[str] = []
        for artifact_path in artifacts:
            artifact_id = self.create_record(
                record_type="artifact",
                title="Generated artifact",
                summary=artifact_path,
                payload={"path": artifact_path},
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )
            artifact_ids.append(artifact_id)
            self.link_records(
                from_record_id=test_id,
                to_record_id=artifact_id,
                relation="produced_artifact",
                rationale="Test/result flow generated artifact",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        handoff_id = self.create_record(
            record_type="handoff_note",
            title="Handoff note",
            summary=handoff_summary,
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )
        result["handoff_note_id"] = handoff_id
        result["artifact_ids"] = artifact_ids

        self.link_records(
            from_record_id=session_record_id,
            to_record_id=handoff_id,
            relation="recorded_handoff",
            rationale="Session produced handoff note",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
            phase=phase,
            source_tool=source_tool,
        )

        for artifact_id in artifact_ids:
            self.link_records(
                from_record_id=artifact_id,
                to_record_id=handoff_id,
                relation="referenced_in_handoff",
                rationale="Artifact referenced in handoff",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        if phase:
            phase_record_id = self.create_record(
                record_id=phase,
                record_type="phase_record",
                title=f"Phase {phase}",
                summary="Phase lineage record",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )
            result["phase_record_id"] = phase_record_id
            self.link_records(
                from_record_id=session_record_id,
                to_record_id=phase_record_id,
                relation="executed_in_phase",
                rationale="Session activity associated with phase",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                session_id=session_id,
                phase=phase,
                source_tool=source_tool,
            )

        return result

    def record_phase_artifacts(
        self,
        *,
        phase: str,
        artifact_paths: list[str],
        evidence_paths: list[str],
        workspace_id: str,
        actor_id: str,
        project_id: str = "",
        source_tool: str = "phase.closeout",
    ) -> dict[str, Any]:
        phase_id = self.create_record(
            record_id=phase,
            record_type="phase_record",
            title=f"Phase {phase}",
            summary="Phase closeout record",
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            phase=phase,
            source_tool=source_tool,
        )
        artifacts: list[str] = []
        evidence: list[str] = []
        for path in artifact_paths:
            aid = self.create_record(
                record_type="artifact",
                title="Phase artifact",
                summary=path,
                payload={"path": path},
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                phase=phase,
                source_tool=source_tool,
            )
            artifacts.append(aid)
            self.link_records(
                from_record_id=phase_id,
                to_record_id=aid,
                relation="generated_artifact",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                phase=phase,
                source_tool=source_tool,
            )

        for path in evidence_paths:
            eid = self.create_record(
                record_type="evidence_bundle",
                title="Phase evidence",
                summary=path,
                payload={"path": path},
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                phase=phase,
                source_tool=source_tool,
            )
            evidence.append(eid)
            self.link_records(
                from_record_id=phase_id,
                to_record_id=eid,
                relation="generated_evidence",
                workspace_id=workspace_id,
                actor_id=actor_id,
                project_id=project_id,
                phase=phase,
                source_tool=source_tool,
            )

        return {"phase_record_id": phase_id, "artifact_ids": artifacts, "evidence_ids": evidence}

    def query_timeline(
        self,
        *,
        workspace_id: str,
        actor_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        record_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        nodes = self._table_rows(self._nodes)
        scoped_nodes = self._scope_filter(
            nodes,
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
        )
        if record_id:
            scoped_nodes = [row for row in scoped_nodes if row.get("record_id") == record_id]
        scoped_nodes.sort(key=lambda row: _safe_str(row.get("created_at")), reverse=True)
        scoped_nodes = scoped_nodes[: max(1, min(limit, 200))]

        timeline = []
        for row in scoped_nodes:
            payload = {}
            raw_payload = _safe_str(row.get("payload_json"))
            if raw_payload:
                try:
                    payload = json.loads(raw_payload)
                except json.JSONDecodeError:
                    payload = {"raw": raw_payload}
            timeline.append(
                {
                    "record_id": row.get("record_id"),
                    "record_type": row.get("record_type"),
                    "title": row.get("title"),
                    "summary": row.get("summary"),
                    "payload": payload,
                    "created_at": row.get("created_at"),
                    "attribution": {
                        "workspace_id": row.get("workspace_id"),
                        "actor_id": row.get("actor_id"),
                        "project_id": row.get("project_id"),
                        "session_id": row.get("session_id"),
                        "phase": row.get("phase"),
                        "source_tool": row.get("source_tool"),
                    },
                }
            )

        return {"timeline": timeline, "count": len(timeline)}

    def explain_record(
        self,
        *,
        record_id: str,
        workspace_id: str,
        actor_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        depth: int = 2,
    ) -> dict[str, Any]:
        scoped_nodes = self._scope_filter(
            self._table_rows(self._nodes),
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
        )
        node_map = {str(row.get("record_id")): row for row in scoped_nodes}
        if record_id not in node_map:
            return {"record_id": record_id, "found": False, "message": "record not found in scope"}

        scoped_edges = self._scope_filter(
            self._table_rows(self._edges),
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
        )

        seen = {record_id}
        frontier = {record_id}
        for _ in range(max(1, min(depth, 4))):
            connected: set[str] = set()
            for edge in scoped_edges:
                from_id = _safe_str(edge.get("from_record_id"))
                to_id = _safe_str(edge.get("to_record_id"))
                if from_id in frontier and to_id in node_map:
                    connected.add(to_id)
                if to_id in frontier and from_id in node_map:
                    connected.add(from_id)
            connected -= seen
            if not connected:
                break
            seen |= connected
            frontier = connected

        related_nodes = [node_map[rid] for rid in seen if rid in node_map]
        related_edges = [
            edge
            for edge in scoped_edges
            if _safe_str(edge.get("from_record_id")) in seen
            and _safe_str(edge.get("to_record_id")) in seen
        ]
        evidence = [row for row in related_nodes if row.get("record_type") == "evidence_bundle"]
        changed = [
            row
            for row in related_nodes
            if row.get("record_type") in {"git_diff", "test_result", "artifact"}
        ]

        return {
            "record_id": record_id,
            "found": True,
            "what_happened": [
                {
                    "record_id": row.get("record_id"),
                    "record_type": row.get("record_type"),
                    "title": row.get("title"),
                    "summary": row.get("summary"),
                    "source_tool": row.get("source_tool"),
                    "session_id": row.get("session_id"),
                }
                for row in sorted(related_nodes, key=lambda item: _safe_str(item.get("created_at")))
            ],
            "why": [
                {
                    "from": edge.get("from_record_id"),
                    "to": edge.get("to_record_id"),
                    "relation": edge.get("relation"),
                    "rationale": edge.get("rationale"),
                }
                for edge in related_edges
            ],
            "evidence_supported": [
                {
                    "record_id": row.get("record_id"),
                    "title": row.get("title"),
                    "summary": row.get("summary"),
                }
                for row in evidence
            ],
            "what_changed": [
                {
                    "record_id": row.get("record_id"),
                    "record_type": row.get("record_type"),
                    "summary": row.get("summary"),
                }
                for row in changed
            ],
        }

    def query_what_changed(
        self,
        *,
        workspace_id: str,
        actor_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        scoped_nodes = self._scope_filter(
            self._table_rows(self._nodes),
            workspace_id=workspace_id,
            actor_id=actor_id,
            project_id=project_id,
            session_id=session_id,
        )
        changed_types = {"git_diff", "test_result", "artifact", "handoff_note", "execution_record"}
        changed = [
            row for row in scoped_nodes if _safe_str(row.get("record_type")) in changed_types
        ]
        changed.sort(key=lambda row: _safe_str(row.get("created_at")), reverse=True)
        changed = changed[: max(1, min(limit, 200))]

        return {
            "count": len(changed),
            "changes": [
                {
                    "record_id": row.get("record_id"),
                    "record_type": row.get("record_type"),
                    "summary": row.get("summary"),
                    "source_tool": row.get("source_tool"),
                    "session_id": row.get("session_id"),
                    "phase": row.get("phase"),
                    "created_at": row.get("created_at"),
                }
                for row in changed
            ],
        }


_GRAPH_INSTANCE: ProvenanceGraph | None = None


def get_provenance_graph() -> ProvenanceGraph:
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        _GRAPH_INSTANCE = ProvenanceGraph()
    return _GRAPH_INSTANCE
