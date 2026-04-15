# P97 — Live UI Reality Reconciliation + Figma Parity

**Status:** In Progress  
**Dependencies:** P95, P96  
**Risk Tier:** High  
**Backend:** opencode

## Objective

Reconcile the live localhost console against real behavior, code truth, and the P96 Figma/Notion documentation bundle. Correct false-positive completion assumptions from P89-P95 where runtime behavior does not match documented claims.

## Scope

Audit and reconcile all six core panels:

1. Chat
2. Settings
3. Providers
4. Security
5. Projects & Phases
6. Terminal / Shell Gateway

## Pre-flight Baseline

- `git status`: dirty worktree from prior phases (expected)
- `git log --oneline -10`: includes P91/P92/P95-related commits
- `ruff check ai/ ui/src/ tests/ docs/`: fails due pre-existing issues in `docs/zo-tools/*` (out of P97 scope)
- `python -m pytest tests/ -q --tb=short`: `2186 passed, 183 skipped`
- `cd ui && npx tsc --noEmit`: passes
- Services: MCP bridge and LLM proxy both active on localhost

## Source-of-Truth Inputs Used

- `HANDOFF.md`
- `docs/AGENT.md`
- `docs/PHASE_DOCUMENTATION_POLICY.md`
- `docs/PHASE_INDEX.md`
- `docs/PHASE_ARTIFACT_REGISTER.md`
- P96 Notion page and child bundle (14 child pages)
- P89-P95 phase claims and artifacts

## Confirmed Mismatches (Claimed vs Actual)

- Settings still used browser-native `window.prompt`/`window.confirm` despite P95 debt classification.
- Settings "View Audit Log" button existed but was not wired.
- Project workflow hook still had stale-closure-style overwrite risk in error handling path.
- Security quick actions were labeled "Coming Soon" and not connected to backend tools.
- Chat health check helpers existed but were not used before send.
- Shell active session was not persisted across refresh/reload.
- MCP argument validation assumed all args are strings, causing typed integer args (e.g. `shell.get_audit_log`, `settings.audit_log`) to fail unexpectedly.

## Planned Deliverables

- Repo-level fixes for each confirmed mismatch.
- `docs/P97_RECONCILIATION.md` evidence matrix (issue → cause → fix → validation).
- Update phase index/register and HANDOFF with reality-based closeout.

## Validation Commands

- `source .venv/bin/activate && ruff check ai/mcp_bridge/tools.py tests/test_mcp_tools_validation.py`
- `source .venv/bin/activate && python -m pytest tests/test_mcp_tools_validation.py tests/test_mcp_bridge_tools.py tests/test_tools.py tests/test_mcp_bridge_advanced.py -q --tb=short`
- `cd ui && npx tsc --noEmit`
