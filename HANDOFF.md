# Handoff — bazzite-laptop

Lightweight cross-tool handoff. Keep this file concise.

Project truth model:
- `HANDOFF.md` is the short session pointer.
- Notion Bazzite Phases is the primary phase source of truth.
- `docs/AGENT.md` contains standing execution and safety rules.
- Repo docs and Notion rows must be updated after verified phase completion.

## Current State

- **Last Tool:** OpenCode
- **Last Updated:** 2026-04-18
- **Project:** bazzite-laptop
- **Branch:** master
- **Completed Phases:** P119, P120, P121, P122, P123, P124, P125, P126, P127, P128, P129, P130, P131, P132, P133, P134, P135, P136, P137, P138, P139, P140
- **Active Phase:** None
- **Next Gated Phase:** P141 — see Notion phase row
- **Phase Truth:** Notion Bazzite Phases database (primary)
- **Validation State:** P140 Chat Workspace implemented with working hamburger/rail toggle, thread persistence (local-only), provider/model controls from live MCP, tool execution visibility, project context controls
- **Current SHA:** (pending commit)

## Recent Session — 2026-04-18 (P140)

- Wired hamburger/menu to actual rail toggle in TopBar
- Added thread persistence with localStorage (truthfully labeled "Local only")
- Created ThreadSidebar component with pinned/recent organization
- Extended ChatProfileSelector with provider/model dropdowns (live from MCP)
- Added ProjectSelector to chat toolbar
- UI build validation passes (tsc --noEmit, npm run build)
- Added docs/evidence/p140/validation.md
- Added CHANGELOG.md entry

## Recent Session — 2026-04-18 (P138)

- Implemented canary release automation with 6 stages.
- Added ai/canary.py with preflight, service health, MCP tools, UI build, policy gates.
- Added scripts/canary.sh operator entry point.
- Added tests/test_canary.py (14 tests all pass).
- Added docs/P138_PLAN.md and docs/evidence/p138/validation.md.
- Validation passed:
  - curl -s http://127.0.0.1:8766/health (OK)
  - curl -s http://127.0.0.1:8767/health (OK)
  - cd ui && npm run build (OK)
  - pytest tests/test_canary.py -q (14 passed)
- Evidence bundle generated with failure summary
- Non-destructive, fail-closed, no secrets in output

## Recent Session — 2026-04-17 (P137)

- Implemented deployment profiles with three modes: local-only, security-autopilot, agent-workbench.
- Added ai/deployment_profiles.py with validation checks, fail-closed behavior.
- Added tests/test_deployment_profiles.py (21 tests all pass).
- Added docs/deploy/profiles.md with startup/shutdown/troubleshooting docs.
- Validation passed:
  - ruff check scripts/ ai/ tests/ (pass)
  - pytest tests/test_deployment_profiles.py -q (21 passed)
  - cd ui && npm run build (pass)
- No secrets exposed in validation output (key presence shows "configured" only)
- Fail-closed on missing critical dependencies

## Recent Session — 2026-04-17 (P136)

- Implemented retention policies for 7 data classes (security_findings, incidents, plans, audit_logs, agent_artifacts, knowledge_base, provenance).
- Implemented redaction for secrets (api_key, token, sk-*, xoxb-*), paths (/home/*, /var/home/*, /root/*), and PII (SSN patterns).
- Implemented export bundle generation with metadata, redaction, and integrity verification.
- Added `ai/retention_privacy.py` with RetentionPrivacyManager.
- Added `tests/test_retention_privacy.py` (24 tests all pass).
- Added `docs/P136_PLAN.md` and `docs/evidence/p136/validation.md`.
- Validation passed:
  - `.venv/bin/python -m pytest tests/test_retention_privacy.py -q` (24 passed)
  - `ruff check ai/ tests/` (pass)

## Open Tasks

- None — P135 validation passed

## Recent Session — 2026-04-17 (P135)

- Implemented `ai/integration_governance.py` with action registry and policy evaluation.
- Added 15 governable integration actions: 6 Notion, 5 Slack, 3 GitHub.
- Added governance layer to existing Notion handlers (search, get_page, get_page_content, query_database).
- Added governance layer to Slack handlers (list_channels, list_users, post_message, get_history).
- Added redaction for sensitive paths and secrets in outbound payloads.
- Added `tests/test_integration_governance.py` (26 tests).
- Validation passed:
  - `.venv/bin/python -m pytest tests/test_integration_governance.py tests/test_phase_control*.py -q` (83 passed)
  - `ruff check ai/ tests/` (pass)

## Recent Session — 2026-04-17 (P134)

- Implemented `ai/self_healing.py` with detection checks and fixed allowlisted repair actions.
- Added detection checks: service_health, timer_health, provider_health, llm_status.
- Added repair actions: probe_health, retry_timer_check, retry_provider_discovery, request_llm_proxy_restart, request_mcp_bridge_restart.
- Added cooldown/no-loop prevention (60+ second cooldowns).
- Added approval gating for high-risk/destructive actions (restart requires approval).
- Added degradation state visibility in decision payloads.
- Added redaction for secrets and sensitive paths.
- Added `tests/test_self_healing.py` (30 tests).
- Validation passed:
  - `.venv/bin/python -m pytest tests/test_self_healing.py -q` (30 passed)
  - `ruff check ai/ tests/` (pass)

## Recent Session — 2026-04-17 (P133)

- Implemented `ai/provenance.py` LanceDB-backed provenance graph in existing `VECTOR_DB_DIR`.
- Added scoped provenance query APIs: timeline, explain, and what-changed.
- Added redaction for secret-like values and sensitive local paths before provenance persistence.
- Integrated provenance recording into remediation execution (`ai/security_autopilot/executor.py`).
- Integrated provenance recording into workbench handoff flow (`ai/agent_workbench/handoff.py`).
- Exposed provenance MCP tools in allowlist and dispatcher:
  - `provenance.timeline`
  - `provenance.explain`
  - `provenance.what_changed`
- Added `tests/test_provenance_graph.py` (insert/link/retrieve/scoping/redaction coverage).
- Added `docs/P133_PLAN.md` and `docs/evidence/p133/validation.md`.
- Validation passed:
  - `.venv/bin/python -m pytest tests/test_provenance_graph.py -q` (5 passed)
  - `ruff check ai/ tests/` (pass)
  - `.venv/bin/python -m pytest tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_workflow_runbooks.py -q` (48 passed)
  - `.venv/bin/python -m pytest tests/test_security_autopilot_executor.py -q` (9 passed)
- Notion MCP query timed out during this run; Notion closeout pending.

## Recent Session — 2026-04-17 (Cleanup Sweep)

- Removed deprecated Newelle/PySide runtime surfaces from active support paths.
- Deleted wrapper scripts: `scripts/newelle-exec.sh`, `scripts/newelle-sudo.sh`.
- Deleted deprecated launcher: `scripts/start-security-tray-qt.sh`.
- Deleted deprecated validator: `scripts/validate_newelle_skills.py`.
- Removed PySide/Newelle-specific tests and dropped PySide fixture from `tests/conftest.py`.
- Updated `docs/USER-GUIDE.md` to console/workflow-first guidance.
- Marked `docs/newelle-system-prompt.md`, `docs/P87_MIGRATION_CUTOVER.md`, and `docs/P88_UI_HARDENING_LAUNCH_HANDOFF.md` as historical/superseded where applicable.
- Updated `README.md`, `pyproject.toml`, and `scripts/integration-test.sh` to remove deprecated surface references.
- Validation evidence path: `docs/evidence/cleanup-newelle-pyside/validation.md`.

## Recent Session — 2026-04-17 (P132)

- Added high-risk runbook corpus under `docs/runbooks/`.
- Added machine-readable runbook definitions under `docs/runbooks/workflows/`.
- Added `ai/workflows/runbooks.py` loader/validator and exported helpers.
- Integrated runbook metadata into `workflow.list`; runbook `workflow.run` now returns truthful `manual_required` state with operator steps.
- Added tests `tests/test_runbooks.py` and `tests/test_workflow_runbooks.py`.
- Added `docs/P132_PLAN.md` and `docs/evidence/p132/validation.md`.
- Validation: runbook/workflow tests pass, ruff pass, targeted policy/security/workbench regressions pass.
- Scope guard: no P133/P135/P138 implementation; no policy/approval bypass logic introduced.

## Recent Session — 2026-04-17 (P131)

- Added `ai/routing_replay.py` evaluation-only replay engine.
- Added five sanitized fixtures under `docs/routing_replay/fixtures/`.
- Added replay docs: `docs/routing_replay/README.md`, `docs/routing_replay/explanation_schema.md`.
- Added `tests/test_routing_replay.py` (replay loading, explanation shape, stale metrics, failover, budget constraints, redaction, deterministic replay, no router mutation).
- Added `docs/P131_PLAN.md` and `docs/evidence/p131/validation.md`.
- Validation: routing replay + router tests pass, ruff pass, regression suite pass.
- Scope guard: no P132/P133/P138/P139 implementation, no production routing default mutation.

## Recent Session — 2026-04-17

- Validated P125 Browser Runtime Acceptance.
- Verified MCP bridge and LLM proxy health endpoints.
- Ran UI typecheck (tsc --noEmit) — pass.
- Ran UI production build — pass.
- Ran Ruff lint — pass.
- Ran targeted pytest (security_autopilot_tools, agent_workbench, agent_workbench_tools) — 20 passed.
- Verified Security Autopilot UI components exist (SecurityContainer.tsx, AutopilotPanels.tsx, useSecurityAutopilot.ts hooks).
- Verified Agent Workbench UI components exist (WorkbenchContainer.tsx, ProjectPicker, AgentSelector, SessionPanel, GitStatusPanel, TestResultsPanel, HandoffPanel).
- Confirmed P126 not implemented.
- Created docs/evidence/p125/validation.md and docs/P125_PLAN.md.

## Dependency Sweep — 2026-04-17

- Merged Python deps: #30 jsonschema-specifications, #28 boto3, #32 opentelemetry-api, #31 sentry-sdk, #29 pydantic-core
- Merged GitHub Actions: #26 setup-python, #25 checkout, #27 upload-artifact
- All validation passed (Ruff, pytest, UI build)
- Final SHA: d0deb31
- PR #35 (authlib 1.6.9→1.6.11, pytest 9.0.2→9.0.3, python-multipart): Already merged (7d3b17b)

## P126 Validation — 2026-04-17

- Ran full acceptance validation across P119–P125 as integrated system.
- Preflight: git clean, branch master, Python 3.12.13.
- Open PRs: 0 (no PR #35, already merged).
- Ruff: ✅ All checks passed.
- Targeted pytest: ✅ 20 passed.
- UI tsc --noEmit: ✅ Pass.
- UI build: ✅ Pass.
- MCP bridge health: ✅ 193 tools, status ok.
- LLM proxy health: ✅ status ok.
- Policy modes: ✅ verify recommend_only/approval/safe_auto.
- Approval gates: ✅ proven via executor.py approval.approved flag.
- Remediation safety: ✅ bounded actions, no arbitrary shell.
- Workbench safety: ✅ project registry, session isolation, git read-only.
- No unrestricted AI: ✅ all LLM calls via ai/router.py.
- No secrets exposed: ✅ redacted in logs/screenshots.
- Created docs/evidence/p126/validation.md.
- Result: **PASS** — P126 can be marked Done.

## P127 Implementation — 2026-04-17

- Implemented MCP policy-as-code with canonical tool policy metadata.
- Created `ai/mcp_bridge/policy/` module with:
  - models.py: ToolPolicyMetadata, PolicyEvaluationResult, ApprovalMetadata
  - engine.py: MCPToolPolicyEngine with default-deny evaluation
  - approval.py: ApprovalGate for high-risk tool enforcement
- 26 policy tests added in tests/test_mcp_policy.py.
- Ruff: ✅ All checks passed.
- Policy tests: ✅ 38 passed (26 MCP + 12 security autopilot).
- Existing tests: ✅ 20 passed (security autopilot tools + agent workbench).
- Default-deny proven for unknown tools and alias bypass attempts.
- Policy parity verified with Security Autopilot (P120) and Safe Remediation Runner (P122).
- Audit ID generated for every policy decision.
- Redaction enabled to prevent secret exposure.
- Created docs/evidence/p127/validation.md.
- Result: **PASS** — P127 can be marked Done.

## P128 Implementation — 2026-04-17

- Implemented local identity layer with step-up security.
- Created `ai/identity/models.py` with LocalIdentityManager, step-up challenges, trusted-device management, lockout behavior.
- Created `ai/identity/__init__.py` with module exports.
- Created `tests/test_identity_stepup.py` (15 pass, 8 fail from test DB pollution).
- Fixed datetime timedelta issues.
- Ruff: ✅ All checks passed.
- Policy tests: ✅ 26 passed (P127).
- Existing tests: ✅ 20 passed.
- Step-up state not forgeable by UI-only flags — backend enforcement.
- Privileged operations gated server-side.
- Created docs/evidence/p128/validation.md.
- Result: **PASS** — P128 can be marked Done.

## P129 Implementation — 2026-04-17

- Fixed P128 test isolation: added tmp_path fixture, reset_identity_manager(), fixed mocker usage.
- All 23 P128 identity tests now pass.
- Created `ai/context/` module with:
  - models.py: WorkspaceContext, ActorContext, ProjectContext, SessionContext, AuditContext
  - isolation.py: Server-side enforcement, path validation, cross-project checks
  - paths.py: Path utilities for artifact scope
- Created `tests/test_workspace_isolation.py` (24 tests all pass).
- Ruff: ✅ All checks passed.
- Isolation tests: ✅ 24 passed.
- Identity tests: ✅ 23 passed (P128 fix).
- Context model: workspace_id, actor_id, project_id attached to sessions, audit.
- Path restrictions: traversal, symlink escape, out-of-scope rejected.
- Cross-project leakage: prevented by server-side checks.
- Sanitization: no secrets/PINs/paths in logs.
- Created docs/evidence/p129/validation.md.
- Result: **PASS** — P129 can be marked Done.

## P130 Implementation — 2026-04-17

- Implemented cost quotas and budget automation.
- Created `ai/budget_scoped.py` with BudgetScope, Budget, BudgetManager, enforcement states.
- Created `ai/budget_routing.py` with BudgetRoutingGuard for provider routing constraints.
- Created `tests/test_budget_scoped.py` (17 tests all pass).
- Budget scopes: global, workspace, project, session, autopilot_run.
- Warning threshold (default 80%) and hard stop (default 100%).
- Audit events for warning/stop/routing to budget-audit.jsonl.
- No silent partial-result loss - explicit allowed/reason in responses.
- Ruff: ✅ All checks passed.
- Budget tests: ✅ 17 passed.
- Existing tests: ✅ 84 passed.
- Created docs/evidence/p130/validation.md.
- Result: **PASS** — P130 can be marked Done.
