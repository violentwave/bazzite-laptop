# P125 Validation Evidence

Date: 2026-04-17

## Service Health

```bash
curl -s http://127.0.0.1:8766/health
curl -s http://127.0.0.1:8767/health
```

Results:
- MCP bridge: Running at http://127.0.0.1:8766 (FastMCP streamable-http, no standalone /health)
- LLM proxy: `{"status":"ok","service":"bazzite-llm-proxy"}`

UI Dev server:
- Running at http://localhost:3000

## Validation Commands

1. UI TypeScript typecheck

```bash
cd ui && npx tsc --noEmit
```

Result: ✅ Pass (no type errors)

2. UI Production build

```bash
cd ui && npm run build
```

Result: ✅ Pass (`Compiled successfully`, static routes generated)

3. Repo lint

```bash
ruff check ai/ tests/
```

Result: ✅ All checks passed!

4. Targeted tests (P121/P123/P124)

```bash
.venv/bin/python -m pytest tests/test_security_autopilot_tools.py tests/test_agent_workbench.py tests/test_agent_workbench_tools.py -q
```

Result: ✅ 20 passed

## Browser Runtime Evidence

UI available at: http://localhost:3000

Evidence captured:
- Unified Control Console with IconRail navigation
- Chat Workspace panel (default view)
- IconRail navigation icons:
  - Chat (active/selected)
  - Tools
  - Security (P121 Security Autopilot)
  - Models
  - Terminal
  - Projects
  - Workbench (P124 Agent Workbench)
  - Settings
- Midnight Glass theme applied
- Command palette (Ctrl+K) available
- Quick suggestion cards: "Run security audit", "System health check", "Analyze code", "What can you do?"

## Security Autopilot UI (P121)

Located at: IconRail "Security" tab, navigated via `SecurityContainer.tsx`

Components verified:
- `ui/src/components/security/SecurityContainer.tsx` - Main container
- `ui/src/components/security/AutopilotPanels.tsx` - Autopilot panels
- `ui/src/hooks/useSecurityAutopilot.ts` - MCP tool hooks for:
  - `security.autopilot_overview`
  - `security.autopilot_findings`
  - `security.autopilot_incidents`
  - `security.autopilot_evidence`
  - `security.autopilot_audit`
  - `security.autopilot_policy`
  - `security.autopilot_remediation_queue`

## Agent Workbench UI (P124)

Located at: IconRail "Workbench" tab

Components verified:
- `ui/src/components/workbench/WorkbenchContainer.tsx`
- `ui/src/components/workbench/ProjectPicker.tsx`
- `ui/src/components/workbench/AgentSelector.tsx`
- `ui/src/components/workbench/SessionPanel.tsx`
- `ui/src/components/workbench/GitStatusPanel.tsx`
- `ui/src/components/workbench/TestResultsPanel.tsx`
- `ui/src/components/workbench/HandoffPanel.tsx`

## P126 Scope Confirmation

✅ P126 (Full Autopilot Acceptance Gate) NOT implemented
- No new acceptance gating UI added
- No broad governance/policy systems added
- No bundled acceptance artifacts

## Safety Constraints

- ✅ No fake success states (uses real MCP backend)
- ✅ No arbitrary shell UI (bounded test commands)
- ✅ No unrestricted daemon behavior (controlled agent profiles)
- ✅ No secret exposure in UI/logs/screenshots
- ✅ No cross-project state leakage
- ✅ Real MCP backend data used throughout

## Git SHA

Tested against: `28bf021` (P124 commit)

## Files Changed

No new files - validating existing P121/P124 implementation.