# P124 — Codex/OpenCode UI Integration

**Status:** Done  
**Date:** 2026-04-17  
**Dependencies:** P123 (`04b76b6`)  
**Risk Tier:** high  
**Execution Mode:** bounded  
**Approval Required:** false  
**Backend:** opencode

## Objective

Integrate the Agent Workbench panel into the Unified Control Console so operators can use real `workbench.*` MCP tools for project selection, bounded session lifecycle, read-only git/test surfaces, and structured handoff capture.

## Scope Delivered

- Added Workbench navigation and routing in the existing shell surfaces:
  - `ui/src/components/shell/IconRail.tsx`
  - `ui/src/components/shell/CommandPalette.tsx`
  - `ui/src/app/page.tsx`
- Added typed Agent Workbench contracts:
  - `ui/src/types/agent-workbench.ts`
- Added Workbench data hook with MCP-backed flows and truthful error/degraded handling:
  - `ui/src/hooks/useAgentWorkbench.ts`
- Added Workbench panel and sub-surfaces (inside existing console shell):
  - `ui/src/components/workbench/WorkbenchContainer.tsx`
  - `ui/src/components/workbench/ProjectPicker.tsx`
  - `ui/src/components/workbench/AgentSelector.tsx`
  - `ui/src/components/workbench/SessionPanel.tsx`
  - `ui/src/components/workbench/GitStatusPanel.tsx`
  - `ui/src/components/workbench/TestResultsPanel.tsx`
  - `ui/src/components/workbench/HandoffPanel.tsx`
- Added MCP contract tests for P124 UI/backend expectations:
  - `tests/test_agent_workbench_tools.py`

## Operator Flows Implemented

- Select registered project from real `workbench.project_list` data.
- Select bounded backend profile and sandbox/lease constraints.
- Create/attach/stop sessions through `workbench.session_*` tools.
- View read-only git metadata from `workbench.git_status`.
- View and run only registered test commands via `workbench.test_commands`.
- Save structured handoff notes via `workbench.handoff_note`.
- Render truthful degraded state strips when MCP/workbench calls fail.

## Safety Boundaries Maintained

- No separate standalone dashboard; panel is integrated into the existing Unified Control Console.
- No arbitrary shell command surface added to Workbench UI.
- No fake project/session/test data paths; panel consumes real MCP results.
- No hardcoded success states; degraded banners follow tool/runtime failures.
- No secret values or raw sensitive artifacts are surfaced.
- P125/P126/P127/P129 scope intentionally excluded.

## Evidence

- `docs/evidence/p124/validation.md`
- `docs/evidence/p124/screenshots/01-project-selected.png`
- `docs/evidence/p124/screenshots/02-session-created.png`
- `docs/evidence/p124/screenshots/03-git-and-tests.png`
- `docs/evidence/p124/screenshots/04-handoff-saved.png`
- `docs/evidence/p124/screenshots/05-session-stopped.png`
- `docs/evidence/p124/screenshots/06-degraded-mcp-offline.png`
