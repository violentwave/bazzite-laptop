# Changelog — Bazzite AI Layer

All significant changes. Format: date · deliverables · deltas · commit.

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
