# P143 - UI Implementation Map

This map splits the redesign spec into three implementation phases without collapsing them into one large UI rewrite.

## Phase Overview

| Phase | Scope | Primary Outcome |
|---|---|---|
| P144 | Home Dashboard redesign implementation | Calm widget-based Home with project-first entry |
| P145 | Chat Workspace and thread rail redesign | Focused chat, navigator-style rail, progressive diagnostics |
| P146 | Workspace personalization and preset persistence | Durable user preferences without cloud/account invention |

## P144 - Home Dashboard Redesign Implementation

### Scope
- Replace the fixed Home card layout with a widget grid.
- Make Active Project the primary card.
- Add the minimal widget set: Recent Threads, Services Status, Quick Actions.
- Include Security Snapshot and Activity Feed only when the preset calls for them.
- Keep Home and Chat distinct surfaces.

### Affected Repo Files
- `ui/src/components/home/HomeContainer.tsx`
- `ui/src/lib/home-dashboard.js` and `.d.ts`
- `ui/src/lib/console-simplify.js` if Home summaries need reshaping
- `ui/src/hooks/useAgentWorkbench.ts`, `useProviders.ts`, `useSecurity.ts`, `useChat.ts` as data sources

### Backend / State Dependencies
- No new backend required.
- Uses existing live hooks and local thread/project state.
- Widget order can remain local during P144.

### Risks
- Home becomes too dense if every widget is visible by default.
- Project launch flow can regress if it is split across too many controls.
- Widgets may become static shells if they stop reading live truth.

### Validation Expectations
- Home loads with the correct default preset.
- Active Project remains the main entry path.
- Empty states stay truthful.
- No regressions to project registration or recent-thread launch.

## P145 - Chat Workspace and Thread Rail Redesign

### Scope
- Tighten Chat header/runtime strip.
- Rework the thread rail into a professional navigator.
- Preserve pinned, recent, project-grouped, and archived sections.
- Keep bulk select, merge, archive, restore, and move flows.
- Make diagnostics collapsible, not dominant.

### Affected Repo Files
- `ui/src/components/chat/ChatContainer.tsx`
- `ui/src/components/chat/ThreadSidebar.tsx`
- `ui/src/components/chat/ChatMessage.tsx`
- `ui/src/components/chat/ChatInput.tsx`
- `ui/src/components/chat/ChatProfileSelector.tsx`
- `ui/src/lib/thread-store.js` and `.d.ts`
- `ui/src/lib/workspace-session-binding.js`
- `ui/src/lib/operator-runtime.js`
- `ui/src/lib/console-simplify.js`

### Backend / State Dependencies
- No new backend required for the current local-first behavior.
- Thread merge/archive/move already has local store support.
- Any new backend merge service would be a later follow-up, not P145.

### Risks
- Rail duplication can return if pinned/recent/project buckets are not clearly separated.
- Diagnostics can overwhelm the chat surface if made default-open.
- Merge/archive UX can become ambiguous if destructive choices are not explicit.

### Validation Expectations
- Thread selection still works.
- Bulk actions still work.
- Merge modal still reflects real local thread data.
- Runtime truth remains visible and consistent.

## P146 - Workspace Personalization and Preset Persistence

### Scope
- Persist preset choice.
- Persist widget selection and ordering.
- Persist sidebar or workspace visibility preferences if the spec requires them.
- Add a single preference model shared by Home and Chat.

### Affected Repo Files
- `ui/src/components/home/HomeContainer.tsx`
- `ui/src/components/chat/ChatContainer.tsx`
- `ui/src/components/chat/ThreadSidebar.tsx`
- `ui/src/components/chat/ChatProfileSelector.tsx`
- `ui/src/components/shell/CommandPalette.tsx` if preset switching is exposed there
- New or existing preference storage module under `ui/src/lib/`

### Backend / State Dependencies
- Preferred path: local-first persistence backed by an existing repo settings mechanism if available.
- Do not invent cloud sync or account login.
- If no settings API is ready, use localStorage as the first durable layer and mark server sync as future work.

### Risks
- Persistence can drift from live truth if preference state is allowed to override unavailable data.
- A settings service dependency can stall the phase if it is not already contract-ready.
- Cross-surface preference handling can become inconsistent without one canonical schema.

### Validation Expectations
- Preset changes survive reloads.
- Widget layout survives reloads.
- Workspace preferences do not hide required truth.
- No regression to Home/Chat launch paths.

## Recommended Order
1. P144 first: establish the Home model and widget structure.
2. P145 second: reshape Chat and the thread navigator using the same truth model.
3. P146 last: persist the user preferences after the structure is stable.

## Must Not Regress From P140-P142
- Local-first thread storage and project binding truth.
- Archive, restore, merge, and bulk-thread actions.
- Live provider/model/runtime diagnostics.
- Active project selection and launch behavior.
- Stable empty states and degraded-state honesty.
