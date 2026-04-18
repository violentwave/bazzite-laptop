# Changelog — Bazzite AI Layer

All significant changes. Format: date · deliverables · deltas · commit.

---

## Phase 133 — Memory, Artifact, and Provenance Graph
**Date:** 2026-04-17 · **Commit:** ae06d55

**Deliverables:**
- Added `ai/provenance.py` with LanceDB-backed provenance nodes/edges and scoped retrieval
- Linked security lineage: finding/incident/evidence/recommendation/action/execution/audit
- Linked workbench lineage: session/git diff/tests/artifacts/handoff/phase
- Added redaction-safe provenance storage for secrets and sensitive local paths
- Added MCP query APIs: `provenance.timeline`, `provenance.explain`, `provenance.what_changed`
- Added tests in `tests/test_provenance_graph.py`
- Added phase plan/evidence docs (`docs/P133_PLAN.md`, `docs/evidence/p133/validation.md`)

**Validation:**
- `.venv/bin/python -m pytest tests/test_provenance_graph.py -q` — 5 passed
- `ruff check ai/ tests/` — pass
- `.venv/bin/python -m pytest tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_workflow_runbooks.py -q` — 48 passed
- `.venv/bin/python -m pytest tests/test_security_autopilot_executor.py -q` — 9 passed

**Artifacts:**
- `ai/provenance.py`
- `ai/security_autopilot/executor.py`
- `ai/agent_workbench/handoff.py`
- `ai/mcp_bridge/tools.py`
- `configs/mcp-bridge-allowlist.yaml`
- `tests/test_provenance_graph.py`
- `docs/P133_PLAN.md`
- `docs/evidence/p133/validation.md`

**Result:** PASS — Provenance graph implemented with scoped attribution and redaction-safe storage across security, workbench, artifact, memory, and phase record paths.

---

## Cleanup Sweep - Deprecated Newelle/PySide Runtime Surfaces
**Date:** 2026-04-17 · **Commit:** cb50d35

**Deliverables:**
- Removed deprecated runtime wrapper scripts: `scripts/newelle-exec.sh`, `scripts/newelle-sudo.sh`
- Removed deprecated PySide launcher script: `scripts/start-security-tray-qt.sh`
- Removed deprecated Newelle skill validator script: `scripts/validate_newelle_skills.py`
- Removed Newelle/PySide-focused tests and PySide test fixture wiring
- Updated docs to console/workflow-first guidance and marked legacy prompt/migration docs as historical
- Removed PySide-specific dependency/lint exclusions from `pyproject.toml`

**Validation:**
- `ruff check ai/ tests/ scripts/` - pass
- `.venv/bin/python -m pytest tests/ -x -q --tb=short` - pass

**Artifacts:**
- `docs/evidence/cleanup-newelle-pyside/validation.md`

**Result:** PASS - Deprecated fallback/tray runtime surfaces removed from active operation without changing MCP, LLM proxy, workflow, or runbook contracts.

---

## Phase 132 — Human-in-the-loop Orchestration Runbooks
**Date:** 2026-04-17 · **Commit:** 9e7e963

**Deliverables:**
- Added high-risk operator runbook corpus under `docs/runbooks/`
- Added machine-readable runbook workflow definitions under `docs/runbooks/workflows/`
- Added runbook loader/validator in `ai/workflows/runbooks.py`
- Integrated runbook surfacing into existing workflow handlers:
  - `workflow.list` now returns runbook metadata
  - `workflow.run` returns `manual_required` for runbook IDs with explicit operator steps
- Added tests for runbook parsing/safety and workflow integration
- Added phase plan and evidence docs (`docs/P132_PLAN.md`, `docs/evidence/p132/validation.md`)

**Validation:**
- `.venv/bin/python -m pytest tests/test_runbooks.py tests/test_workflow*.py -q` — 35 passed
- `ruff check ai/ tests/` — pass
- `.venv/bin/python -m pytest tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py -q` — 42 passed

**Artifacts:**
- `docs/runbooks/*.md`
- `docs/runbooks/workflows/*.yaml`
- `ai/workflows/runbooks.py`
- `ai/mcp_bridge/handlers/workflow_tools.py`
- `tests/test_runbooks.py`
- `tests/test_workflow_runbooks.py`
- `docs/P132_PLAN.md`
- `docs/evidence/p132/validation.md`

**Result:** PASS — Human-in-the-loop runbooks added with explicit approval and
escalation semantics aligned to P122/P127/P128 and P131 decision support.

---

## Phase 131 — Routing Evaluation and Replay Lab
**Date:** 2026-04-17 · **Commit:** 7e32900

**Deliverables:**
- Added evaluation-only routing replay module in `ai/routing_replay.py`
- Added five sanitized replay fixtures under `docs/routing_replay/fixtures/`
- Added explanation schema doc at `docs/routing_replay/explanation_schema.md`
- Added replay lab usage docs at `docs/routing_replay/README.md`
- Added replay test suite `tests/test_routing_replay.py`
- Added phase plan and validation evidence (`docs/P131_PLAN.md`, `docs/evidence/p131/validation.md`)
- Preserved production routing defaults and avoided runtime mutation

**Validation:**
- `.venv/bin/python -m pytest tests/test_routing_replay.py tests/test_router.py -q` — 35 passed
- `ruff check ai/ tests/` — pass
- `.venv/bin/python -m pytest tests/test_budget_scoped.py tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py -q` — 59 passed

**Artifacts:**
- `ai/routing_replay.py`
- `docs/routing_replay/README.md`
- `docs/routing_replay/explanation_schema.md`
- `docs/routing_replay/fixtures/*.json`
- `tests/test_routing_replay.py`
- `docs/P131_PLAN.md`
- `docs/evidence/p131/validation.md`

**Result:** PASS — Routing replay lab implemented with deterministic fixtures,
budget-aware comparisons, failover/staleness coverage, and explanation payloads.

---

## Phase 130 — Cost Quotas and Budget Automation
**Date:** 2026-04-17 · **Commit:** be08087

**Deliverables:**
- Implemented scoped budget model with token/cost limits, warning/stop thresholds
- Created ai/budget_scoped.py with BudgetScope, Budget, BudgetManager
- Created ai/budget_routing.py with BudgetRoutingGuard for provider constraints
- Budget scopes: global, workspace, project, session, autopilot_run
- Warning threshold (default 80%) and hard stop (default 100%)
- Audit events for warning/stop/routing to budget-audit.jsonl
- Provider routing respects budget constraints
- No silent partial-result loss - explicit allowed/reason in responses

**Validation:**
- `ruff check ai/budget_scoped.py ai/budget_routing.py tests/test_budget_scoped.py` — pass
- `.venv/bin/python -m pytest tests/test_budget_scoped.py -q` — 17 passed
- `.venv/bin/python -m pytest tests/test_budget.py tests/test_identity_stepup.py tests/test_workspace_isolation.py tests/test_mcp_policy.py -q` — 84 passed

**Artifacts:**
- `ai/budget_scoped.py`
- `ai/budget_routing.py`
- `tests/test_budget_scoped.py`
- `docs/evidence/p130/validation.md`

**Result:** PASS — Cost quotas and budget automation implemented.

---

## Phase 129 — Workspace and Actor Context Isolation
**Date:** 2026-04-17 · **Commit:** (pending)

**Deliverables:**
- Fixed P128 test isolation (tmp_path fixture, reset_identity_manager, mocker fix)
- All 23 P128 identity tests now pass
- Created ai/context/ module with context models (workspace, actor, project, session, audit)
- Server-side isolation enforcement (not UI-dependent)
- Path validation: traversal, symlink escape, out-of-scope rejected
- Cross-project access prevention tested
- Audit context with correlation IDs for all operations
- Sanitization: no secrets/PINs/paths in logs

**Validation:**
- `ruff check ai/context/ tests/test_workspace_isolation.py` — pass
- `.venv/bin/python -m pytest tests/test_identity_stepup.py -q` — 23 passed
- `.venv/bin/python -m pytest tests/test_workspace_isolation.py -q` — 24 passed

**Artifacts:**
- `ai/context/__init__.py`
- `ai/context/models.py`
- `ai/context/isolation.py`
- `ai/context/paths.py`
- `tests/test_workspace_isolation.py`
- `docs/evidence/p129/validation.md`

**Result:** PASS — Workspace/actor context isolation implemented with server-side enforcement, path restrictions, cross-project leakage prevention.

---

## Phase 128 — Local Identity and Step-Up Security
**Date:** 2026-04-17 · **Commit:** f524b84

**Deliverables:**
- Implemented local-only identity layer with step-up security
- Created LocalIdentityManager with PIN verification, failed attempt tracking, lockout
- Implemented StepUpChallenge with expiry for privileged operation elevation
- Added TrustedDevice management with creation, expiry, revocation
- Backend enforcement via `check_privileged_operation` decorator — step-up not forgeable by UI
- Server-side gating for settings mutations, secret reveal, high-risk tools
- Integration with P127 MCP policy engine
- Fixed test isolation (tmp_path fixture, reset_identity_manager, mocker) - all 23 tests pass

**Validation:**
- `ruff check ai/identity/ tests/test_identity_stepup.py` — pass
- `.venv/bin/python -m pytest tests/test_identity_stepup.py -q` — 23 passed
- `.venv/bin/python -m pytest tests/test_mcp_policy.py -q` — 26 passed

**Artifacts:**
- `ai/identity/__init__.py`
- `ai/identity/models.py`
- `tests/test_identity_stepup.py`
- `docs/evidence/p128/validation.md`

**Result:** PASS — Local identity layer with step-up security, test isolation fixed.

---

## Phase 127 — MCP Policy-as-Code and Approval Gates
**Date:** 2026-04-17 · **Commit:** aea4d5c

**Deliverables:**
- Implemented canonical MCP tool policy metadata (ToolPolicyMetadata, RiskTier, PolicyDecision)
- Created policy evaluation engine with default-deny semantics
- Implemented approval gate enforcement for high-risk tools
- Added bypass resistance (alias/namespace/parameter tricks rejected)
- Integrated with Security Autopilot (P120) and Safe Remediation Runner (P122) semantics
- Audit ID generation for every policy decision
- Redaction to prevent secret exposure

**Validation:**
- `ruff check ai/mcp_bridge/policy/ tests/test_mcp_policy.py` — pass
- `.venv/bin/python -m pytest tests/test_mcp_policy.py tests/test_security_autopilot_policy.py -q` — 38 passed
- `.venv/bin/python -m pytest tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_agent_workbench_tools.py -q` — 20 passed

**Artifacts:**
- `ai/mcp_bridge/policy/__init__.py`
- `ai/mcp_bridge/policy/models.py`
- `ai/mcp_bridge/policy/engine.py`
- `ai/mcp_bridge/policy/approval.py`
- `tests/test_mcp_policy.py`
- `docs/evidence/p127/validation.md`

**Result:** PASS — Policy-as-code layer implemented with approval gates and auditability.

---

## Phase 126 — Full Autopilot Acceptance Gate
**Date:** 2026-04-17 · **Commit:** 7d3b17b

**Deliverables:**
- Validated P119–P125 as one integrated system.
- Created acceptance validation evidence at `docs/evidence/p126/validation.md`.
- Verified policy modes (recommend_only/approval/safe_auto), approval gates, remediation safety, workbench safety.
- Confirmed no unrestricted AI execution, no arbitrary shell, no secrets exposed.
- Updated HANDOFF.md with P126 completion.

**Validation:**
- `ruff check ai/ tests/ scripts/` — pass
- `.venv/bin/python -m pytest tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_agent_workbench_tools.py -q` — 20 passed
- `cd ui && npx tsc --noEmit` — pass
- `cd ui && npm run build` — pass
- `curl -s http://127.0.0.1:8766/health` — `{"status":"ok","tools":193,"service":"bazzite-mcp-bridge"}`
- `curl -s http://127.0.0.1:8767/health` — `{"status":"ok","service":"bazzite-llm-proxy"}`

**Result:** PASS — Approval gates verified, safety proofs confirmed.

---

## Phase 125 — Browser Runtime Acceptance
**Date:** 2026-04-17 · **Commit:** 28bf021

**Deliverables:**
- Validated Security Autopilot UI (P121) runtime acceptance via browser inspection.
- Validated Agent Workbench UI (P124) runtime acceptance via browser inspection.
- Verified MCP bridge and LLM proxy health endpoints.
- Created runtime validation evidence at `docs/evidence/p125/validation.md`.
- Created phase plan at `docs/P125_PLAN.md`.

**Validation:**
- MCP bridge running at http://127.0.0.1:8766
- LLM proxy health: `{"status":"ok","service":"bazzite-llm-proxy"}`
- `cd ui && npx tsc --noEmit` — pass
- `cd ui && npm run build` — pass
- `ruff check ai/ tests/` — pass
- `.venv/bin/python -m pytest tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_agent_workbench_tools.py -q` — 20 passed

**Scope Confirmation:** P126 (Full Autopilot Acceptance Gate) NOT implemented.

---

## Phase 124 — Codex/OpenCode UI Integration
**Date:** 2026-04-17 · **Commit:** pending

**Deliverables:**
- Added Agent Workbench navigation to the Unified Control Console shell and command palette.
- Added `ui/src/types/agent-workbench.ts` and `ui/src/hooks/useAgentWorkbench.ts` for real MCP-backed workbench state (projects, sessions, git, tests, handoff).
- Added integrated Workbench panel surfaces in `ui/src/components/workbench/*` for project picker, agent selector, session lifecycle, git status, test execution, and handoff artifacts.
- Added `tests/test_agent_workbench_tools.py` for MCP tool contract coverage used by the UI.
- Added phase docs and runtime evidence at `docs/P124_PLAN.md` and `docs/evidence/p124/*`.

**Validation:**
- `cd ui && npx tsc --noEmit`
- `cd ui && npm run build`
- `.venv/bin/python -m pytest tests/test_agent_workbench_tools.py -q`
- `ruff check ai/ tests/`
- `.venv/bin/python -m pytest tests/test_agent_workbench.py -q`
- `python3 -c "import yaml; yaml.safe_load(open('configs/mcp-bridge-allowlist.yaml')); print('allowlist parse ok')"`

---

## Phase 123 — Agent Workbench Core
**Date:** 2026-04-17 · **Commit:** 14b0f78

**Deliverables:**
- Added new `ai/agent_workbench/` package for project registry, session lifecycle, sandbox profiles, read-only git summaries, safe test command execution, and structured handoff notes.
- Added 11 MCP `workbench.*` tool handlers in `ai/mcp_bridge/tools.py`.
- Added MCP server workbench tool annotations/argument registration in `ai/mcp_bridge/server.py`.
- Added allowlist contracts for all `workbench.*` tools in `configs/mcp-bridge-allowlist.yaml`.
- Added `tests/test_agent_workbench.py` coverage for path safety, registry/session persistence, command restrictions, and MCP envelopes.
- Synced tool drift docs in `docs/newelle-system-prompt.md` and added phase artifacts `docs/P123_PLAN.md` and `docs/evidence/p123/validation.md`.

**Validation:**
- `.venv/bin/python -m pytest tests/test_agent_workbench.py -q`
- `ruff check ai/agent_workbench tests/test_agent_workbench.py`
- `.venv/bin/python -c "from pathlib import Path; import yaml; yaml.safe_load(Path('configs/mcp-bridge-allowlist.yaml').read_text()); print('allowlist yaml parse ok')"`
- `.venv/bin/python -m pytest tests/ -q --tb=short`

---

## Phase 122 — Safe Remediation Runner
**Date:** 2026-04-16 · **Commit:** pending

**Deliverables:**
- Added `ai/security_autopilot/executor.py` with a fixed allowlisted action registry and strict safety validation (no arbitrary shell/model-generated command execution).
- Added structured execution models (`ExecutionApproval`, `RemediationExecutionRequest`, `RemediationExecutionResult`, `RollbackMetadata`) and deterministic reject/execute/prepare outcomes.
- Enforced P120 policy evaluation for every action and explicit approval gates for high-risk/destructive categories.
- Added audit + redacted evidence emission for every attempted action (including rejected attempts).
- Added rollback metadata for prepare-only high-risk request actions.
- Updated package exports in `ai/security_autopilot/__init__.py`.
- Added executor coverage in `tests/test_security_autopilot_executor.py`.
- Added phase documentation/evidence artifacts: `docs/P122_PLAN.md` and `docs/evidence/p122/*`.

**Validation:**
- `.venv/bin/python -m pytest tests/test_security_autopilot_executor.py -q`
- `ruff check ai/security_autopilot tests/test_security_autopilot_executor.py`
- `.venv/bin/python -m pytest tests/ -q --tb=short`

---

## Phase 121 — Security Autopilot UI
**Date:** 2026-04-16 · **Commit:** pending

**Deliverables:**
- Added `ai/security_autopilot/ui_service.py` for read-only autopilot aggregation (overview, findings, incidents, evidence, audit, policy, remediation queue).
- Added seven `security.autopilot_*` MCP handlers in `ai/mcp_bridge/tools.py` and allowlist entries in `configs/mcp-bridge-allowlist.yaml`.
- Added UI autopilot contracts and data hook: `ui/src/types/security-autopilot.ts` and `ui/src/hooks/useSecurityAutopilot.ts`.
- Added new panel surfaces in `ui/src/components/security/AutopilotPanels.tsx` and integrated seven-tab autopilot navigation in `ui/src/components/security/SecurityContainer.tsx`.
- Added `tests/test_security_autopilot_tools.py` and `docs/P121_PLAN.md` + `docs/evidence/p121/validation.md`.

**Validation:**
- `cd ui && npx tsc --noEmit`
- `cd ui && npm run build`
- `.venv/bin/python -m pytest tests/test_security_autopilot_tools.py -q`
- `ruff check ai/ tests/`
- `.venv/bin/python -m pytest tests/ -q --tb=short`

---

## Phase 120 — Security Policy Engine
**Date:** 2026-04-16 · **Commit:** pending

**Deliverables:**
- Added `ai/security_autopilot/policy.py` with mode-based policy evaluation for `monitor_only`, `recommend_only`, `safe_auto`, `approval_required`, and `lockdown`.
- Added strict decision outcomes (`auto_allowed`, `approval_required`, `blocked`) and full action category model.
- Added `configs/security-autopilot-policy.yaml` with safe defaults, destructive-action controls, global blocked categories, and redaction patterns.
- Added structured request/result policy models and validation for malformed mode/category/action inputs.
- Added target path validation for write/delete categories against allowlisted roots.
- Added policy redaction helper and P119 remediation action evaluation path without execution.
- Added `tests/test_security_autopilot_policy.py` and `docs/P120_PLAN.md`.

**Validation:**
- `.venv/bin/python -m pytest tests/test_security_autopilot_policy.py -q`
- `ruff check ai/security_autopilot tests/test_security_autopilot_policy.py`
- `.venv/bin/python -m pytest tests/ -q --tb=short`

---

## Phase 119 — Security Autopilot Core
**Date:** 2026-04-16 · **Commit:** d502c21

**Deliverables:**
- Added `ai/security_autopilot/` core package with safe typed models for findings/incidents/decisions/plans/audit/evidence.
- Added safe sensor adapters over existing Bazzite security/system/log/agent signals (`security.*`, `system.*`, `logs.anomalies`, `agents.*`).
- Added finding classifier and incident grouping logic.
- Added plan-only remediation planner (no destructive execution allowed).
- Added redacted evidence handling and append-only hash-chained JSONL audit ledger.
- Added `tests/test_security_autopilot.py` and `docs/P119_PLAN.md`.

**Validation:**
- `.venv/bin/python -m pytest tests/test_security_autopilot.py -q`
- `ruff check ai/security_autopilot tests/test_security_autopilot.py`
- `.venv/bin/python -m pytest tests/ -q --tb=short`

---

## Phase 112 — UI Dev Runtime / Turbopack Launch Crash Remediation
**Date:** 2026-04-15 · **Commit:** pending

**Deliverables:**
- Fixed Turbopack dev server crash by neutralizing root-level tailwindcss dependencies.
- Added deterministic preflight check to `scripts/start-console-ui.sh` to prevent root-level frontend package pollution.
- Re-rooted Turbopack via `ui/next.config.ts` (`root: __dirname`).
- Fixed React component crash in `SecurityOverview.tsx` (TypeError reading 'length' of undefined `recent_alerts`).

**Validation:**
- `npx tsc --noEmit` and `npm run build` in `ui/` passed.
- `ruff check ai/ tests/ scripts/` passed.
- UI browser compilation with `next dev --turbo` succeeds without crash.

---

## Phase 111 — Final Production Acceptance Gate
**Date:** 2026-04-15 · **Commit:** pending

**Deliverables:**
- `docs/P111_PLAN.md` — Acceptance gate matrix and validation plan
- `docs/P111_FINAL_ACCEPTANCE_REPORT.md` — Comprehensive system acceptance validation
- Confirmed full system stability across 169 MCP tools, P101-P105 backend features, and P106-P110 UI features
- Verified degraded state correctness, safety boundaries, and no exposed secrets
- Consolidated phase documentation across `HANDOFF.md`, `PHASE_INDEX.md`, and `PHASE_ARTIFACT_REGISTER.md`

**Validation:**
- `ruff check ai/ tests/ scripts/` passed
- `python -m pytest tests/` test suites passed
- `npx tsc --noEmit` and `npm run build` in `ui/` passed
- UI browser evidence visually verified against localhost endpoints

---

## Phase 87 — Newelle/PySide Migration + Compatibility Cutover
**Date:** 2026-04-13 · **Commit:** 877efdd

**Deliverables:**
- `docs/P87_MIGRATION_CUTOVER.md` — primary-UX threshold, parallel-run model, compatibility boundaries, rollback triggers/path, deprecation matrix
- Updated `docs/USER-GUIDE.md` to make Unified Control Console the primary documented UX
- Updated `docs/AGENT.md` Newelle integration section to fallback role
- Updated `docs/newelle-system-prompt.md` with P87 compatibility preface
- Updated phase tracking docs (`HANDOFF.md`, `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`) for P86/P87 truth alignment

**Notes:**
- P80 (Auth/2FA/Recovery/Gmail) remains explicitly deferred
- Newelle and PySide remain supported fallback/secondary surfaces; no runtime removal in P87

---

## Phase 88 — UI Hardening, Validation, Docs, Launch Handoff
**Date:** 2026-04-14 · **Commit:** pending

**Deliverables:**
- Added `docs/P88_UI_HARDENING_LAUNCH_HANDOFF.md` with end-to-end validation checklist, evidence summary, hardening findings, launch checklist, deferred-risk log, and tranche launch stance
- Reconciled phase-status drift by marking P77/P78 docs complete
- Updated `docs/newelle-system-prompt.md` tool routing catalog to include `security.ops_*`, `settings.*`, `providers.*`, `shell.*`, and `project.*` tools required by drift validation
- Updated launch-truth guidance in `docs/USER-GUIDE.md` with explicit P88 ready/partial/deferred state
- Updated phase tracking docs (`HANDOFF.md`, `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`) for P88 closeout and P86/P87/P88 consistency

**Validation:**
- `npx tsc --noEmit` (ui) passed
- `.venv/bin/python -m pytest tests/ -q --tb=short` passed (2131 passed, 183 skipped)
- `ruff check docs/ || true` still reports pre-existing `docs/zo-tools/*` lint debt (out of P88 scope)

**Notes:**
- P80 remains deferred and is not marked complete
- Unified Control Console is launch-ready locally for the current tranche; Newelle/PySide remain fallback/secondary per P87

---

## Phase 21 — Code Knowledge Base Expansion
**Date:** 2026-04-03 · **Commit:** 7eb5906

**Deliverables:**
- `ai/rag/pattern_store.py` — LanceDB `code_patterns` table (schema, upsert, dedup by SHA256 content ID)
- `ai/rag/pattern_query.py` — `search_patterns()` with `VALID_LANGUAGES`/`VALID_DOMAINS` allowlists, vector field stripped from output
- `scripts/ingest-patterns.py` — CLI ingest for `docs/patterns/*.md`, YAML frontmatter parsing, `--dry-run` and `--force` flags
- `docs/patterns/` — 26 curated code patterns (python, bash, rust, yaml) across security, systems, testing domains
- `knowledge.pattern_search` MCP tool (tool #50) registered in bridge and allowlist

**Deltas:** Tools 49 → 50 · Tests 1672 → 1679

---

## Phase 20 — Headless Security Briefing + Timer Sentinel
**Date:** 2026-04-03 · **Commit:** 903ab26

**Deliverables:**
- `scripts/security-briefing.py` — headless daily briefing (no LLM), assembles ClamAV/health/provider/timer/KEV/update sections, atomic write via tempfile+os.replace
- `ai/agents/timer_sentinel.py` — validates all 16 systemd timers against expected fire windows; returns per-timer status and overall healthy/warning/critical
- `systemd/security-briefing.service` + `security-briefing.timer` — daily 08:45, `Persistent=true`
- `agents.timer_health` MCP tool (tool #49) registered in bridge

**Deltas:** Tools 48 → 49 · Timers 15 → 16 · Tests 1621 → 1672

---

## Phase 19 — Input Validation & MCP Safety Layer
**Date:** 2026-04-03 · **Commit:** c97aba0

**Deliverables:**
- `ai/security/inputvalidator.py` — `InputValidator` with SQL injection, command injection, forbidden pattern, path traversal, and secret redaction detection; loaded as singleton in MCP bridge
- `configs/safety-rules.json` — max_input_length (10000), forbidden_patterns, path_allowed_roots, high_risk_tools
- `ai/mcp_bridge/tools.py` — pre-dispatch `_VALIDATOR.validate_tool_args()` call; secrets redacted in log warnings
- `tests/test_inputvalidator.py` — 51 tests covering injection, path traversal, redaction, boundary conditions

**Deltas:** Tests 1570 → 1621

---
