# Handoff — bazzite-laptop

Auto-generated cross-tool handoff. Updated by Claude.ai (Perplexity/Bazzite-secure space)

## Current State

- **Last Tool:** claude.ai (Bazzite-secure space)
- **Last Updated:** 2026-04-08T10:55:00Z
- **Project:** bazzite-laptop
- **Branch:** master (clean, up to date)
- **Phase:** post-P50

## Confirmed Baseline Numbers

| Metric | Value |
|---|---|
| MCP tools | 82 (+1 health endpoint) |
| Systemd timers | 22 |
| Unit tests | 2317 (0 failures) |
| LanceDB tables | 26 |
| Newelle skill bundles | 9 |
| ruff errors | 0 |
| Cloud LLM providers | 6 |
| Threat intel APIs | 16 |

## Documentation State (P44-DOC-01 + P44-DOC-02 Complete)

All documentation updated in latest commit:
- `README.md` — root README created
- `docs/phase-roadmap-p44.md` — created
- `docs/AGENT.md` — reconciled to post-P50 state
- `docs/USER-GUIDE.md` — expanded
- `docs/newelle-system-prompt.md` — updated
- `docs/morning-briefing-prompt.md` — updated
- `docs/CHANGELOG.md` — updated
- `docs/verified-deps.md` — updated (last verified 2026-04-08)
- `docs/REPO-STRUCTURE.md` — updated
- `HANDOFF.md` (this file) — reflects post-P50 state

## Latest Rescue Branch

- **Branch:** `rescue/p45-cleanup-and-docs`
- **Commit:** `1790886`
- **Message:** `docs: finalize P45 path cleanup and repo structure`
- **Status:** Pushed to origin; PR was offered by GitHub — merge via web UI

## Path Classification Outcome (P45)

| Directory | Decision |
|---|---|
| `desktop/` | KEEP — permanent supported repo structure |
| `agents/` | REMOVED — legacy Claude Flow YAML artifacts |
| `plugins/` | REMOVED — legacy NodeJS/Claude Flow cruft |

- `scripts/check-repo-structure.py` updated to reflect above
- Repo structure validation passed before commit

## Git Safety State

- `master` is clean and up to date
- Two stashes exist:
  - `stash@{0}` = `post-P45 mixed in-progress changes` (substantial — ai/, tests/, configs/mcp-bridge-allowlist.yaml, pyproject.toml, scripts/security-briefing.py, docs/zo-tools/*)
  - `stash@{1}` = `leftover untracked files before phase close`
- **DO NOT** apply `stash@{0}` onto `master` blindly
- Safe recovery: `git stash branch rescue/post-p45-mixed stash@{0}`

## Open Tasks

1. Open/merge PR for `rescue/p45-cleanup-and-docs` via GitHub web UI
2. Start P46 Dependabot triage from clean `master`
3. Leave stashes untouched until intentionally sorted
4. Later: deploy verification / health checks
   - `curl -s http://127.0.0.1:8766/health`
   - `curl -s http://127.0.0.1:8767/v1/models`

## Dependabot Branches Visible on Origin

- GitHub Actions updates
- `certifi`, `cryptography`, `filelock` (multiple versions)
- `litellm`, `pillow`, `pip`, `pip-audit`
- `protobuf`, `pygobject`, `pypresence`, `requests`

Note: `pip-audit` is system-only, not installed in `.venv`. `pygobject` is system-provided, not in `.venv`.

## Critical Guardrails

1. NEVER modify `ai/router.py` and `ai/mcp_bridge/` in the same prompt
2. NEVER suggest PRIME offload variables (crash Proton games)
3. NEVER lower `vm.swappiness` below 180 (ZRAM)
4. NEVER install Python packages globally (uv + .venv only)
5. NEVER store API keys in code/scripts/git
6. NEVER use `shell=True` in subprocess
7. NEVER import `ai.router` in `ai/mcp_bridge/`
8. NEVER modify `/usr` (immutable OS)
9. `restorecon` after every systemd unit install
10. Atomic writes for `~/security/.status` (read-modify-write + tmp/mv)
11. Runtime semantic cache path is external: `~/security/llm-cache/`

## CC Prompt Numbering

- Continues from 100 (P43 ended at cc-prompt 100)

## Recent Sessions

### 2026-04-08T10:55:00Z — claude.ai (Bazzite-secure)
Memory update: P44-DOC-01 and P44-DOC-02 complete. P45 cleanup committed on rescue/p45-cleanup-and-docs (commit 1790886). Post-P50 baseline confirmed: 2317 tests, 26 LanceDB tables, 82 MCP tools, 22 timers. agents/ and plugins/ deleted. desktop/ promoted to permanent structure. Two stashes exist — do not apply blindly. Next: merge rescue PR, start P46 Dependabot triage.

### 2026-04-06T23:38:49Z — claude-code
P43 (cc-prompts 93-100) fully executed: ruff errors reduced from 30 to 0 via per-file-ignores and real code fixes in composites.py/test_perf_profiler.py, all 1872 tests still pass. Newelle docs synced to 82-tool reality — system prompt gained intel.* section, 4 new skill bundles created (intel/collab/memory/workflow), bazzite-system.md updated with 15 new tools, morning briefing expanded from 7 to 12 tools. Smoke test script (scripts/smoke-test-tools.py) confirmed 30/30 P42-wired tools dispatch correctly; architecture diagram updated to 82 tools / 22 timers; committed as e022b3c.

### 2026-04-06T23:04:05Z — claude-code
P42 stabilization pass executed all 7 cc-prompts (86-92): fixed 8 test failures (SELinux DB isolation, live Cohere API mock, lancedb sys.modules contamination, Sentry eager format string), wired 30 orphaned MCP tools into _execute_python_tool dispatch, and reconciled AGENT.md/CHANGELOG.md/USER-GUIDE.md to actual state (82 tools, 22 timers, 1872 tests). pyproject.toml was updated to scope E402 suppression to router.py, reducing ruff baseline from 48 to 30 errors. Remaining: 17 Dependabot PRs need manual merge via GitHub web UI (gh CLI unavailable) and services were not running so runtime health checks were skipped.
