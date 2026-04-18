# P133 Validation Evidence — Memory, Artifact, and Provenance Graph

Date: 2026-04-17
Status: PASS

## Git SHA

- Before: `cb50d35`
- After: `ae06d55`

## Provenance Entity/Link Schema

Storage backend: existing LanceDB path (`VECTOR_DB_DIR`), no parallel database.

Tables:

1. `provenance_nodes`
   - keys: `record_id`, `record_type`
   - attribution: `workspace_id`, `actor_id`, `project_id`, `session_id`, `phase`, `source_tool`
   - content: `title`, `summary`, `payload_json`, `created_at`
2. `provenance_edges`
   - keys: `edge_id`, `from_record_id`, `to_record_id`, `relation`
   - attribution: `workspace_id`, `actor_id`, `project_id`, `session_id`, `phase`, `source_tool`
   - content: `rationale`, `metadata_json`, `created_at`

Implemented link patterns:

- Security chain:
  `finding -> incident -> evidence_bundle -> recommendation -> approved_action -> execution_record -> audit_event`
- Workbench chain:
  `workbench_session -> git_diff -> test_result -> artifact -> handoff_note -> phase_record`
- Phase chain:
  `phase_record -> artifact` and `phase_record -> evidence_bundle`

## Scoped Query Proof (P129)

Scoped query APIs require `workspace_id` and support additional filters:

- `query_timeline(workspace_id, actor_id?, project_id?, session_id?)`
- `explain_record(record_id, workspace_id, actor_id?, project_id?, session_id?)`
- `query_what_changed(workspace_id, actor_id?, project_id?, session_id?)`

Scope behavior verified in tests:

- `tests/test_provenance_graph.py::test_scope_isolation_blocks_cross_workspace_reads`
- Only records with matching workspace are returned.

## Example Redacted Query Output

Representative timeline output (sanitized):

```json
{
  "record_type": "artifact",
  "summary": "token=[REDACTED] in [PATH_REDACTED]",
  "payload": {
    "secret": "api_key=[REDACTED]",
    "path": "[PATH_REDACTED]"
  },
  "attribution": {
    "workspace_id": "ws-redact",
    "actor_id": "actor-redact"
  }
}
```

## Redaction and Sensitive Data Statement

- Provenance storage redacts secret-like key/value markers (`token=`, `api_key=`,
  `secret=`, `password=`).
- Sensitive local paths are normalized to `[PATH_REDACTED]` before persistence.
- No raw secrets or sensitive local paths are intentionally written by the
  provenance module.

## Validation Commands and Results

```bash
$ .venv/bin/python -m pytest tests/test_provenance_graph.py -q
5 passed

$ ruff check ai/ tests/
All checks passed!

$ .venv/bin/python -m pytest tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_workflow_runbooks.py -q
48 passed

$ .venv/bin/python -m pytest tests/test_security_autopilot_executor.py -q
9 passed
```

## Files Added/Updated for P133

- `ai/provenance.py`
- `ai/security_autopilot/executor.py`
- `ai/agent_workbench/handoff.py`
- `ai/mcp_bridge/tools.py`
- `configs/mcp-bridge-allowlist.yaml`
- `tests/test_provenance_graph.py`
- `docs/P133_PLAN.md`

## Known Limitations

1. Provenance writes are integrated for remediation execution and handoff paths;
   not every legacy subsystem emits provenance yet.
2. No retention/export lifecycle controls are included in P133.
3. Notion updates were not executed from this run due Notion MCP timeouts.

## Next-Phase Notes (P136-related)

- Retention policies and export controls remain intentionally out of scope for
  P133 and should be handled in P136.
