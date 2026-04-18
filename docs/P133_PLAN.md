# P133 — Memory, Artifact, and Provenance Graph

**Status:** Done  
**Risk Tier:** Medium  
**Execution Mode:** bounded  
**Dependencies:** P75, P76, P126, P129

## Objective

Connect incidents/findings, evidence bundles, recommendations, approved actions,
execution records, workbench sessions, git diffs, tests, artifacts, memory, and
phase records into a scoped provenance graph.

## Scope Delivered

1. Added `ai/provenance.py` LanceDB-backed provenance graph using existing
   `VECTOR_DB_DIR` storage.
2. Added provenance entities and links for:
   - security chain: finding -> incident -> evidence -> recommendation -> action -> execution -> audit
   - workbench chain: session -> git diff -> test result -> artifact -> handoff note -> phase
   - phase closeout chain: phase -> artifacts/evidence
3. Added scoped query APIs with P129-style filtering:
   - `query_timeline`
   - `explain_record`
   - `query_what_changed`
4. Added redaction-safe storage for secrets and sensitive local paths before
   persistence.
5. Wired provenance writes into existing flows:
   - `ai/security_autopilot/executor.py` (execution/audit chain)
   - `ai/agent_workbench/handoff.py` (handoff/session/artifact chain)
6. Exposed provenance query tools through MCP bridge:
   - `provenance.timeline`
   - `provenance.explain`
   - `provenance.what_changed`

## Tests

- Added `tests/test_provenance_graph.py` covering:
  - insert + link behavior
  - scoped retrieval isolation
  - redaction behavior
  - timeline/explain/what-changed query behavior
  - phase artifact linking

## Out of Scope (Kept Out)

- P135 integration governance execution.
- P136 retention/export controls.
- Any new parallel database backend.

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_provenance_graph.py -q
ruff check ai/ tests/
.venv/bin/python -m pytest tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_workflow_runbooks.py -q
```

## Evidence

- `docs/evidence/p133/validation.md`
