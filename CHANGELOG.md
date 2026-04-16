# Changelog — Bazzite AI Layer

All significant changes. Format: date · deliverables · deltas · commit.

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
