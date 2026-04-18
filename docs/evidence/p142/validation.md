# P142 Validation — Final Stabilization and Happy-path Evidence

Date: 2026-04-18
Phase row: `346f793e-df7b-8031-a3ab-cb048203415d`

## White-shell Root Cause Status

Status: **fully fixed with durable mitigation** in current repo/runtime scope.

Primary root causes observed during P142:

1. **Stale Turbopack dev chunk/cache state** caused `_next/static` chunk failures (HTTP 500), resulting in unstyled white HTML with content present.
2. **127.0.0.1 dev-origin blocking for HMR resources** produced repeated websocket errors (`/_next/webpack-hmr`) and prevented clean happy-path hydration/runtime behavior during browser validation.

## Durable Mitigations Applied

- Added stable dev launcher cache reset:
  - `ui/scripts/dev-stable.mjs`
  - clears stale `.next/cache/turbopack`, `.next/server/chunks`, `.next/static/chunks` before `next dev`
- Wired operator startup path to stable launcher:
  - `scripts/start-console-ui.sh`
- Disabled persisted Turbopack dev cache restore:
  - `ui/next.config.ts`
  - `experimental.turbopackFileSystemCacheForDev: false`
- Allowed local dev origins used in validation/browser flows:
  - `ui/next.config.ts`
  - `allowedDevOrigins: ['127.0.0.1', 'localhost']`
- Added MCP RPC timeout protection so UI hooks do not hang indefinitely on stalled bridge calls:
  - `ui/src/lib/mcp-client.ts`
  - `AbortSignal.timeout(10000)` on initialize/RPC requests

## Runtime Truth Cleanup

- Consolidated chat runtime state to one canonical source by deriving `runtimeBinding` from active thread + current workspace session + live provider/model catalogs:
  - `ui/src/hooks/useChat.ts`
- Runtime state now cleanly distinguishes:
  - no active thread -> `No thread`
  - selected but incomplete -> `Pending setup`
  - valid active selection -> `Bound`
  - invalid selection -> `Invalid selection`
- Runtime strip now reflects active-thread context intentionally and avoids contradictory header messaging:
  - `ui/src/lib/console-simplify.js`
  - `ui/src/components/chat/ChatContainer.tsx`
- Introspection responses now use the bound runtime state in-path (no stale pre-bind snapshot):
  - `ui/src/hooks/useChat.ts`

## Happy-path Project Flow

- Home -> project selection -> open chat now drives a project-bound chat context:
  - selected project persisted for chat context handoff
  - chat adopts persisted project when thread context is missing
- Files:
  - `ui/src/components/home/HomeContainer.tsx`
  - `ui/src/lib/home-dashboard.js`
  - `ui/src/hooks/useChat.ts`

Verified happy-path runtime sample captured from browser:

- Runtime strip: `z.ai / glm-4.7-flash / fast / proj_671e12a78022`
- Bound badge visible in chat header strip
- No `model=none`, no `project=no-project`, no contradictory pending badge in canonical happy-path screenshot

## Thread Rail Cleanup

- Reduced duplicate thread rendering across sections:
  - `Pinned` and `Recent` remain highlighted views
  - `By Project` now shows remaining active threads not already listed in highlighted sections
- Added explicit section framing text in sidebar so section semantics are deliberate:
  - `Pinned (Priority)`
  - `Recent (Latest)`
  - `By Project (Remaining)` with omission note
- Files:
  - `ui/src/lib/thread-store.js`
  - `ui/src/components/chat/ThreadSidebar.tsx`

## Validation Commands

- `cd ui && node --test src/lib/workspace-session-binding.test.mjs src/lib/thread-store.test.mjs src/lib/console-simplify.test.mjs` -> pass (26/26)
- `cd ui && npx tsc --noEmit` -> pass
- `cd ui && npm run build` -> pass
- `curl -s http://127.0.0.1:3000` -> returns expected HTML with stylesheet/chunk links
- `curl -s http://127.0.0.1:8766/health` -> `{"status":"ok","tools":193,...}`
- `curl -s http://127.0.0.1:8767/health` -> `{"status":"ok",...}`
- Static asset probe (`/_next/static/*` from home HTML):
  - `asset_count = 51`
  - `asset_error_count = 0`

## Evidence — Canonical Screenshot Set

- `docs/evidence/p142/screenshots/p142-home-dashboard-happy-path.png`
- `docs/evidence/p142/screenshots/p142-active-project-success.png`
- `docs/evidence/p142/screenshots/p142-chat-workspace-bound-happy-path.png`
- `docs/evidence/p142/screenshots/p142-thread-organization-final.png`
- `docs/evidence/p142/screenshots/p142-bulk-select-final.png`
- `docs/evidence/p142/screenshots/p142-merge-modal-final.png`
- `docs/evidence/p142/screenshots/p142-archived-restore-final.png`

Note: `p142-runtime-degraded-state.png` intentionally omitted from canonical happy-path proof set in this pass.
