# P90 — Console Runtime Recovery + Contract Reconciliation

**Status**: ✅ COMPLETE  
**Dependencies**: P81-P89  
**Risk Tier**: High  
**Backend**: opencode  
**Closed**: 2026-04-14

## Objective

Recover broken localhost console panels by reconciling frontend MCP transport/contracts with the live FastMCP streamable-http runtime, then surface accurate operator-visible status/error states without masking host-manual security/firmware boundaries.

## Root Cause Clarification

**Important**: The "site can't be reached" behavior observed during P90 validation was NOT a broken panel contract. It was caused by the Next.js dev server not running. The UI requires an active local runtime and is NOT always-on. This is expected behavior, not a bug.

## Plan

1. Replace stale `/tools/call` and `/tools/list` fetch flow with streamable `/mcp` JSON-RPC session flow.
2. Route all panel hooks through a shared MCP client that handles initialize/session/SSE parsing.
3. Reconcile tool-call shapes and response envelopes against `ai/mcp_bridge/tools.py`.
4. Improve panel error messaging to distinguish integration faults from manual host/operator blockers.
5. Reconcile project-phase truth in backend aggregation (`project.context` + `project.phase_timeline`).
6. Fix Next.js Turbopack workspace root warning.
7. Add documented startup workflow for operators.
8. Validate with lint/typecheck/tests and live MCP smoke calls across panel namespaces.

## Implemented

### Transport and contract reconciliation

- `ui/src/lib/mcp-client.ts`
  - Implemented FastMCP session handshake (`initialize` + `notifications/initialized`).
  - Added session-id header persistence (`mcp-session-id`).
  - Switched to JSON-RPC `tools/list` and `tools/call` over `/mcp`.
  - Added SSE payload parsing for `event: message` / `data:` framed responses.
  - Preserved `executeTool()` compatibility for existing chat envelope consumers.

### Panel runtime wiring fixes

- `ui/src/hooks/useProviders.ts`
- `ui/src/hooks/useSecurity.ts`
- `ui/src/hooks/useProjectWorkflow.ts`
- `ui/src/hooks/useShellSessions.ts`
- `ui/src/components/settings/SettingsContainer.tsx`

All above surfaces now call the shared MCP client instead of stale direct fetches to non-existent endpoints.

### Truth/status reconciliation

- `ai/project_workflow_service.py`
  - Hand-off parsing now tracks current phase, completion markers, and phase names from handoff truth.
  - Current phase inference now uses handoff completion truth (not docs file presence).
  - Timeline generation now unions docs + handoff-completed + current phase and maps gated/ready semantics.

### Operator signal cleanup

- `ui/src/app/page.tsx`
  - Replaced stale hardcoded status chips with neutral runtime labels to reduce false confidence.

### Developer ergonomics

- `ui/next.config.ts`
  - Added `turbopack.root` configuration to fix workspace root inference warning.
  - Eliminates the "detected multiple lockfiles" warning without unsafe lockfile deletions.

- `scripts/start-console-ui.sh`
  - New helper script to start the UI dev server with clear documentation.
  - Validates prerequisites (node_modules, package.json) before starting.
  - Prints clear URL and stop instructions.
  - Supports `--build` flag for production builds.

## Runtime Behavior Documentation

### UI Startup Requirements

The Unified Control Console UI is **not always-on**. It requires:

1. **Active dev server**: Must run `npm run dev` in the `ui/` directory
2. **Backend services**: MCP bridge (`bazzite-mcp-bridge.service`) and LLM proxy (`bazzite-llm-proxy.service`) must be running
3. **Local access**: Available only at `http://localhost:3000` (127.0.0.1)

### Quick Start

```bash
# From repo root
./scripts/start-console-ui.sh

# Or manually
cd ui && npm run dev
```

Then open: http://localhost:3000

### Verification

While the server is running:
```bash
curl -I http://localhost:3000  # Returns 200 OK
curl -I http://127.0.0.1:3000  # Returns 200 OK
```

If you see "site can't be reached", the dev server is not running — start it first.

## Validation Evidence

### Static and tests

- `ruff check ai/ tests/ scripts/` -> PASS
- `pytest -q tests/test_project_workflow_service.py` -> PASS (2 passed)
- `.venv/bin/python -m pytest tests/ -x -q --tb=short` -> PASS (2133 passed, 183 skipped)
- `npx tsc --noEmit` (from `ui/`) -> PASS
- `npm run build` (from `ui/`) -> PASS

### Live MCP smoke validation (localhost bridge)

Validated streamable-http session + tool execution against `http://127.0.0.1:8766/mcp`:

- `settings.pin_status` -> OK
- `settings.list_secrets` -> OK
- `providers.health` / `providers.models` / `providers.routing` -> OK
- `security.ops_overview` / `security.ops_provider_health` -> OK
- `project.context` / `project.phase_timeline` -> OK
- `shell.list_sessions` -> OK

### UI runtime validation

- `scripts/start-console-ui.sh` starts cleanly with no Turbopack warnings
- `curl -I http://127.0.0.1:3000` returns 200 OK while server is running
- UI panels render correctly with live MCP data when server is active

## Manual/Host Boundaries Preserved

The following remain explicit manual/degraded states and are not treated as UI regressions:

1. Gemini/Cohere key/quota/operator actions
2. `system-health.service` host-side diagnostics
3. `logrotate.service` boot log permission posture
4. firmware/efivarfs and staged reboot verification

## Files Delivered

- `docs/P90_CONSOLE_RUNTIME_RECOVERY_CONTRACT_RECONCILIATION.md` (this file)
- `ui/src/lib/mcp-client.ts` — MCP streamable HTTP client
- `ui/src/hooks/useProviders.ts` — Provider panel hook
- `ui/src/hooks/useSecurity.ts` — Security panel hook
- `ui/src/hooks/useProjectWorkflow.ts` — Project/workflow panel hook
- `ui/src/hooks/useShellSessions.ts` — Shell panel hook
- `ui/src/components/settings/SettingsContainer.tsx` — Settings panel
- `ui/src/app/page.tsx` — Main shell with corrected status chips
- `ui/next.config.ts` — Turbopack root configuration
- `ai/project_workflow_service.py` — Phase truth reconciliation
- `tests/test_project_workflow_service.py` — Regression tests
- `scripts/start-console-ui.sh` — UI startup helper

## Closeout Summary

P90 is **COMPLETE**. The console runtime recovery:

1. ✅ Fixed MCP transport contract to use streamable HTTP
2. ✅ Reconciled all panel hooks with correct backend contracts
3. ✅ Fixed project-phase truth aggregation in backend
4. ✅ Added developer startup script and documented runtime requirements
5. ✅ Fixed Turbopack workspace root warning
6. ✅ Validated all changes with lint, tests, typecheck, build, and live smoke tests

The "site can't be reached" issue was identified as expected behavior (dev server not running), not a broken contract. The UI now starts cleanly with documented procedures.

## Suggested Follow-ons (P91-P95)

- **P91**: Console Runtime Health Banner + per-panel degraded-state taxonomy (contract/runtime/manual-host).
- **P92**: End-to-end Playwright smoke suite for Settings/Providers/Security/Projects/Shell panel contracts.
- **P93**: MCP client resilience pass (retry budget, backoff, session refresh telemetry, structured error codes).
- **P94**: Replace static shell header chips with live aggregated signals from project/security/provider services.
- **P95**: Identity tranche revisit (P80 successor): auth/2FA/recovery/Gmail with explicit migration policy.
