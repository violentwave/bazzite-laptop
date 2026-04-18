# Changelog — Bazzite AI Layer

All significant changes. Format: date · deliverables · deltas · commit.

---

## Phase 143 — Adaptive Minimalist UI Redesign Spec
**Date:** 2026-04-18 · **Commit:** pending

**Deliverables:**
- Analyzed the extracted redesign bundle at `/home/lch/projects/bazzite-redesign/redesign_ui/`.
- Produced comprehensive redesign specification docs: `docs/P143_UI_REDESIGN_SPEC.md`, `docs/P143_WIDGET_CATALOG.md`, and `docs/P143_UI_IMPLEMENTATION_MAP.md`.
- Defined modular widget-based Home Dashboard architecture with Guided/Standard/Expert presets.
- Defined the Chat Workspace and thread-rail implementation targets without changing production UI in this phase.
- Mapped follow-on implementation into P144, P145, and P146.

---

## Phase 142 — Console Asset Loading and Runtime Stability Fix
**Date:** 2026-04-18 · **Commit:** pending

**Deliverables:**
- Identified root cause for white/unstyled console regressions as `_next/static` dev chunk failures (HTTP 500) under stale Turbopack cache/chunk state.
- Added a stable dev launcher that clears stale chunk cache paths before `next dev` startup:
  - `ui/scripts/dev-stable.mjs`
- Wired `scripts/start-console-ui.sh` to prefer the stable dev launcher path.
- Reduced cache mismatch risk by disabling Turbopack persisted dev cache restore:
  - `ui/next.config.ts` (`experimental.turbopackFileSystemCacheForDev: false`)
- Added local dev-origin compatibility to stop blocked HMR resource loading on `127.0.0.1`:
  - `ui/next.config.ts` (`allowedDevOrigins: ['127.0.0.1', 'localhost']`)
- Added MCP RPC timeout guards to prevent Home/Workbench project loading from hanging indefinitely:
  - `ui/src/lib/mcp-client.ts` (`AbortSignal.timeout(10000)` on initialize and RPC requests)
- Cleaned runtime truth so chat status is derived from one canonical active-thread session state and no longer shows contradictory pending/no-project states in happy-path evidence.
- Reduced thread rail duplication by making `By Project` show remaining active threads not already highlighted in Pinned/Recent.
- Captured final canonical happy-path evidence set for Home -> project -> Chat (bound runtime) and thread workflows.

**Validation:**
- `cd ui && npx tsc --noEmit` — pass
- `cd ui && npm run build` — pass
- `cd ui && node --test src/lib/workspace-session-binding.test.mjs src/lib/thread-store.test.mjs src/lib/console-simplify.test.mjs` — pass (26/26)
- `curl -s http://127.0.0.1:3000` — returns HTML with stylesheet and chunk links
- `curl -s http://127.0.0.1:8766/health` — `{"status":"ok",...}`
- `curl -s http://127.0.0.1:8767/health` — `{"status":"ok",...}`
- Static asset probe after fix: all referenced `_next/static/*` assets on `/` return 200 (`ASSET_ERROR_COUNT 0`)
- Browser runtime check: no repeated `/_next/webpack-hmr` cross-origin websocket failures when validating via `127.0.0.1`

**Artifacts:**
- `docs/evidence/p142/validation.md`
- `docs/evidence/p142/screenshots/p142-home-dashboard-happy-path.png`
- `docs/evidence/p142/screenshots/p142-active-project-success.png`
- `docs/evidence/p142/screenshots/p142-chat-workspace-bound-happy-path.png`
- `docs/evidence/p142/screenshots/p142-thread-organization-final.png`
- `docs/evidence/p142/screenshots/p142-bulk-select-final.png`
- `docs/evidence/p142/screenshots/p142-merge-modal-final.png`
- `docs/evidence/p142/screenshots/p142-archived-restore-final.png`

**Result:** Stabilized in repo scope; Notion row reconciliation still pending external write-path availability.

## Phase 141 — Workspace Evidence Refresh and Post-closeout Polish
**Date:** 2026-04-18 · **Commit:** 58a2934

**Deliverables:**
- Refreshed final-state evidence with canonical P141 screenshot set under `docs/evidence/p141/screenshots/`
- Added explicit archive destination/restore guidance in thread sidebar UX
- Reduced runtime/degraded presentation noise while preserving truthful state rendering
- Clarified project registration constraints in Home modal (absolute path + blocked locations)
- Reconciled docs for post-closeout acceptance evidence

**Validation:**
- `cd ui && npx tsc --noEmit` — pass
- `cd ui && npm run build` — pass

**Canonical evidence set:**
- `docs/evidence/p141/screenshots/p141-home-dashboard-final.png`
- `docs/evidence/p141/screenshots/p141-active-project-flow-final.png`
- `docs/evidence/p141/screenshots/p141-chat-workspace-final.png`
- `docs/evidence/p141/screenshots/p141-thread-organization-final.png`
- `docs/evidence/p141/screenshots/p141-bulk-select-final.png`
- `docs/evidence/p141/screenshots/p141-merge-modal-final.png`
- `docs/evidence/p141/screenshots/p141-archived-restore-flow-final.png`
- `docs/evidence/p141/screenshots/p141-runtime-state-final.png`

**Result:** PASS — post-closeout polish complete and final screenshot evidence refreshed.

---

## Phase 140 — Chat Workspace and Home Screen Operator Integration
**Date:** 2026-04-18 · **Commit:** f3c1795

**Deliverables:**
- Wired hamburger/menu to actual rail toggle behavior in TopBar
- Added persistent thread organization: recent, pinned, project-grouped
- Added local-only storage indicator (truthful labeling)
- Added thread-side project assignment flow (move to project/folder from ThreadSidebar)
- Added canonical runtime session binding for provider/model/mode/project and invalid-selection fail paths
- Added truthful runtime introspection and operator action surface (`/runtime`, `/tools`, `/project`, etc.)
- Added explicit tool trace statuses including blocked/degraded handling
- Added distinct `Home Dashboard` panel with live project entrypoint, recent threads, security/runtime widgets, and quick actions
- Applied Simplification Tranches A, B, C, and Refinement Pass 1 and 2:
  - Condensed Home dashboard into summary-first cards, removing form clutter
  - Condensed Chat Workspace header into a clean runtime strip with toggleable diagnostics
  - Upgraded Thread Sidebar with bulk-select mode, contextual kebab menus, and clean project grouping
  - Implemented true chronological thread merging with auditability (`sourceThreadIds`) and explicit cross-project conflict resolution
  - Fixed runtime consistency bugs and tool discovery paths (`listTools`)
  - Cleaned up empty-state chat, hiding advanced UI and providing minimal guidance/controls
  - Ensured runtime tuple, bind badge, and diagnostics view derive from one consistent binding state
  - Refined degraded-state messages to be concise and kept details in expandable diagnostics
  - Integrated provider/model selection into empty-state WelcomeScreen
  - Polished Thread Rail: Improved thread item layout (title, project/folder, timestamp, markers), ensured only one thread action menu can be open at a time (z-index/focus), improved keyboard accessibility for modals (Escape key closes).
- Added pass 4E + Simplification tranches acceptance screenshot bundle for Home/Chat operator flows

**Validation:**
- `cd ui && node --test src/lib/workspace-session-binding.test.mjs src/lib/thread-store.test.mjs src/lib/operator-runtime.test.mjs src/lib/home-dashboard.test.mjs src/lib/console-simplify.test.mjs` — 24 passed
- `cd ui && npx tsc --noEmit` — pass
- `cd ui && npm run build` — pass

**Files Modified:**
- `ui/src/hooks/useChat.ts` — runtime binding, operator intents/actions, degraded-state truth messaging, bulk selection, merge execution, empty-state cleanup
- `ui/src/lib/llm-client.ts` — runtime binding headers through LLM request path
- `ui/src/lib/workspace-session-binding.*` — runtime validation helpers + tests
- `ui/src/lib/thread-store.*` — thread organization, merging helpers + tests
- `ui/src/lib/operator-runtime.*` — operator grounding helpers + tests
- `ui/src/components/chat/ThreadSidebar.tsx` — thread rename/move/archive, bulk selection, merge modals
- `ui/src/components/chat/ChatContainer.tsx` — runtime badges, location indicator, diagnostics, operator action surface, empty-state simplification, WelcomeScreen integration
- `ui/src/components/home/HomeContainer.tsx` — Home dashboard implementation, project creation validation
- `ui/src/lib/home-dashboard.*` — Home widget helpers + tests
- `ui/src/lib/console-simplify.*` — Simplification helpers + tests
- `ui/src/components/shell/{ShellContext,IconRail,CommandPalette,TopBar}.tsx` — Home panel routing and navigation context
- `ui/src/app/page.tsx` — Home panel render path
- `docs/evidence/p140/screenshots/*` — acceptance evidence screenshots
- `docs/USER-GUIDE.md` — updated with Home vs Chat responsibilities and bulk actions

**Constraints Verified:**
- Local-first truth: Thread storage labeled "Local only", merged threads retain original ordering
- No hardcoded catalogs: Providers/models from live MCP calls
- No fake execution: Tool results show real status/duration/error
- No fake widget metrics: Home widgets sourced from live hooks/runtime state
- No dead buttons: Home/Chat controls route to live surfaces or actionable tool paths
- No silent destruction: Original threads during merge are archived or kept based on explicit choice
- No fake green states: empty state is truthful and minimal
- No hidden failures: diagnostics are available when needed
- No contradictory runtime/bind/project states: UI consistency in empty/active states

**Result:** PASS (closed) — P140 checklist satisfied, evidence captured, and Notion row reconciled to Done.

---

## Phase 137 — Deployment Profiles and Environment Packaging
**Date:** 2026-04-17 · **Commit:** 5f2431c

**Deliverables:**
- Added `ai/deployment_profiles.py` with three deployment profiles
- Added local-only: core services (LLM proxy, MCP bridge) validation
- Added security-autopilot: + API key presence checks
- Added agent-workbench: + workbench config validation
- Added fail-closed on missing critical dependencies
- Added key presence checks without exposing secrets
- Added `docs/deploy/profiles.md` with startup/shutdown/troubleshooting
- Added `tests/test_deployment_profiles.py` with 21 tests

**Validation:**
- `ruff check scripts/ ai/ tests/` — pass
- `.venv/bin/python -m pytest tests/test_deployment_profiles.py -q` — 21 passed
- `cd ui && npm run build` — pass

**Artifacts:**
- `ai/deployment_profiles.py`
- `tests/test_deployment_profiles.py`
- `docs/deploy/profiles.md`
- `docs/P137_PLAN.md`
- `docs/evidence/p137/validation.md`

**Safety Proofs:**
- No secrets in validation output
- Fail-closed on missing services/ports
- No auto-start without operator approval
- Critical checks required: service, mcp, llm, repo, venv

**Result:** PASS — Deployment profiles implemented with three modes.

---

## Phase 136 — Retention, Privacy, and Export Controls
**Date:** 2026-04-17 · **Commit:** 5f2431c

**Deliverables:**
- Added `ai/retention_privacy.py` with retention policies for 7 data classes
- Added redaction for secrets: api_key, token, sk-*, xoxb-*
- Added redaction for paths: /home/*, /var/home/*, /root/*
- Added redaction for PII: SSN patterns
- Added export bundle generation with metadata and integrity
- Added context isolation respecting P129 boundaries
- Added `tests/test_retention_privacy.py` with 24 tests

**Validation:**
- `.venv/bin/python -m pytest tests/test_retention_privacy.py -q` — 24 passed
- `ruff check ai/ tests/` — pass

**Artifacts:**
- `ai/retention_privacy.py`
- `tests/test_retention_privacy.py`
- `docs/P136_PLAN.md`
- `docs/evidence/p136/validation.md`

**Data Classes:**
- security_findings (90 days), incidents (365 days), plans (180 days)
- audit_logs (730 days), agent_artifacts (90 days)
- knowledge_base (365 days), provenance (365 days)

**Safety Proofs:**
- No raw secrets in export
- No raw paths in export
- Evidence not auto-deletable
- Warnings for redactions

**Result:** PASS — Retention, privacy, and export controls implemented.

---

## Phase 134 — Self-healing Control Plane
**Date:** 2026-04-17 · **Commit:** 81daf2c

**Deliverables:**
- Added `ai/self_healing.py` with detection checks for service health, timers, providers, LLM status
- Added fixed allowlisted repair actions: probe_health, retry_timer_check, retry_provider_discovery
- Added approval-gated repair actions: request_llm_proxy_restart, request_mcp_bridge_restart
- Added cooldown/no-loop prevention (60+ second cooldowns)
- Added policy gating for all actions
- Added degraded state visibility in decision payloads
- Added redaction for secrets and sensitive paths
- Added `tests/test_self_healing.py` with 30 tests

**Validation:**
- `.venv/bin/python -m pytest tests/test_self_healing.py -q` — 30 passed
- `ruff check ai/ tests/` — pass

**Artifacts:**
- `ai/self_healing.py`
- `tests/test_self_healing.py`
- `docs/P134_PLAN.md`
- `docs/evidence/p134/validation.md`

**Safety Proofs:**
- No arbitrary shell — all actions fixed-name to existing MCP tools
- No uncontrolled loops — cooldown prevents rapid retry
- Destructive requires approval — restart blocked without explicit approval
- Degraded state visible — explain_decision includes degraded_state_visible
- Audit/evidence — state persists to disk with cooldowns

**Result:** PASS — Self-healing control plane implemented with detection, fixed actions, policy gating, approval requirements, and loop prevention.

---

## Phase 135 — Integration Governance for Notion, Slack, GitHub Actions
**Date:** 2026-04-17 · **Commit:** eedd8db

**Deliverables:**
- Added `ai/integration_governance.py` with action registry and policy evaluation
- Added 15 governable actions: 6 Notion, 5 Slack, 3 GitHub
- Added governance layer to Notion handlers: search, get_page, get_page_content, query_database
- Added governance layer to Slack handlers: list_channels, list_users, post_message, get_history
- Added redaction for sensitive paths and secrets in outbound payloads
- Added `tests/test_integration_governance.py` with 26 tests

**Validation:**
- `.venv/bin/python -m pytest tests/test_integration_governance.py -q` — 26 passed
- `ruff check ai/ tests/` — pass

**Artifacts:**
- `ai/integration_governance.py`
- `tests/test_integration_governance.py`
- `docs/P135_PLAN.md`
- `docs/evidence/p135/validation.md`

**Safety Proofs:**
- Default-deny for unknown actions
- Scope and attribution requirements enforced
- Redaction applied before outbound content
- Audit linkage to compliance events

**Result:** PASS — Integration governance implemented with default-deny policy, scope requirements, and audit linkage.

---

## Phase 133 — Memory, Artifact, and Provenance Graph
**Date:** 2026-04-17 · **Commit:** f4a578b

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
**Date:** 2026-04-17 · **Commit:** f266c4b

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
**Date:** 2026-04-17 · **Commit:** 661d3a8

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
