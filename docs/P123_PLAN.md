# P123 — Agent Workbench Core

**Status:** Done  
**Date:** 2026-04-17  
**Dependencies:** P122  
**Risk Tier:** high  
**Execution Mode:** bounded  
**Approval Required:** false  
**Backend:** opencode

## Objective

Implement the Agent Workbench core backend and MCP bridge surface for safe
project registration, bounded session lifecycle management, read-only git
status, registered test command execution, and structured handoff notes.

## Scope Delivered

- Added new package `ai/agent_workbench/`:
  - `models.py` with typed records for projects, sessions, sandbox profiles,
    git summary, test commands, and handoff notes.
  - `paths.py` with atomic writes, allowlist root parsing,
    absolute-path normalization, and project marker validation.
  - `registry.py` with persistent project registry load/save/list/register/open
    operations.
  - `sessions.py` with bounded session creation/list/get/stop and backend
    allowlist enforcement (`codex`, `opencode`, `claude-code`, `gemini-cli`).
  - `sandbox.py` with conservative and analysis profiles (shell/network disabled
    by default).
  - `git.py` with read-only git status extraction and bounded changed file list.
  - `testing.py` with registered safe test command defaults and blocked token
    checks.
  - `handoff.py` with append-only structured handoff note helper.
  - `__init__.py` package exports and singleton accessors.
- Added MCP handlers in `ai/mcp_bridge/tools.py` for:
  - `workbench.project_register`
  - `workbench.project_list`
  - `workbench.project_open`
  - `workbench.project_status`
  - `workbench.session_create`
  - `workbench.session_list`
  - `workbench.session_get`
  - `workbench.session_stop`
  - `workbench.git_status`
  - `workbench.test_commands`
  - `workbench.handoff_note`
- Added workbench tool annotations and argument pass-through registration in
  `ai/mcp_bridge/server.py`.
- Added allowlist contracts for all `workbench.*` tools in
  `configs/mcp-bridge-allowlist.yaml`.
- Added drift prompt sync entries for all `workbench.*` tools in
  `docs/newelle-system-prompt.md`.
- Added `tests/test_agent_workbench.py` coverage for safety and MCP envelopes.

## Safety Boundaries Maintained

- No unrestricted filesystem access.
- No arbitrary shell execution path.
- No `shell=True` subprocess usage.
- No sudo automation.
- Paths must be absolute, existing directories under allowlisted roots.
- Session working directories are constrained under project root.
- Test execution only allows registered commands with allowlisted executables.
- Handoff notes are structured and append-only.

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_agent_workbench.py -q
ruff check ai/agent_workbench tests/test_agent_workbench.py
.venv/bin/python -c "from pathlib import Path; import yaml; yaml.safe_load(Path('configs/mcp-bridge-allowlist.yaml').read_text()); print('allowlist yaml parse ok')"
.venv/bin/python -m pytest tests/ -q --tb=short
```

## Validation Outcome

- `tests/test_agent_workbench.py`: 13 passed
- `ruff check ai/agent_workbench tests/test_agent_workbench.py`: passed
- allowlist YAML parse: passed
- full suite: 2443 passed, 183 skipped

## Definition of Done

- Project registry and session lifecycle implemented with bounded path policy.
- MCP `workbench.*` tools are registered, allowlisted, and drift-doc synced.
- Read-only git summary and safe test command handling implemented.
- Handoff helper and validation evidence are documented.
- Required targeted and full validation commands pass.

## Next Phase

- P124 — Codex/OpenCode UI Integration
