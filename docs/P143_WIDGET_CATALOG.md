# P143 - Bazzite Widget Catalog

This catalog covers the widgets and compact panels that P144-P146 should implement. Widgets are live, truthful, and removable only when the workflow can recover them.

## Widget Matrix

| Widget | Purpose | Data Source / Hook / System | Area | Default Visibility (G / S / E) | Persistence |
|---|---|---|---|---|---|
| Active Project | Primary project entry and launch point | `useAgentWorkbench`, `home-dashboard.js` | Home | Yes / Yes / Yes | Yes |
| Recent Threads | Return to recent work quickly | `useChat`, `thread-store.js` | Home | Yes / Yes / Yes | No |
| Services Status | MCP/LLM/provider health summary | `useProviders`, `mcp-client`, `llm-client` | Home | Yes / Yes / Yes | No |
| Quick Actions | Fast navigation to core surfaces | Shell panel routing, app navigation | Home | No / Yes / Yes | No |
| Security Snapshot | Safety summary and alert count | `useSecurity` | Home | No / Yes / Yes | No |
| Activity Feed | Recent operator/system events | `useSecurity`, audit/event sources | Home | No / No / Yes | No |
| Chat Runtime Strip | Compact truth tuple for current workspace | `useChat`, `workspace-session-binding.js`, `operator-runtime.js` | Chat | Yes / Yes / Yes | Session state only |
| Thread Rail | Pinned/recent/project/archive navigator | `useChat`, `thread-store.js` | Chat | Yes / Yes / Yes | Yes |
| Diagnostics Panel | Deep runtime and degraded-state details | `useChat`, `console-simplify.js`, runtime health | Chat | No / No / Yes | No |
| Composer Context Hint | Low-noise guidance for operator input | `useChat`, `ChatInput` state | Chat | Yes / Yes / Yes | No |

## Widget Details

### Active Project
- Purpose: choose or register the project that anchors work.
- Interactions: select project, register project, open in Chat, open in Workbench.
- Empty state: no project selected, prompt to pick or register one.
- Failure state: project list unavailable, show retry and preserve local selection if possible.
- Persistence: keep last selected project locally; do not invent account sync.

### Recent Threads
- Purpose: resume the newest local conversations.
- Interactions: open thread, show project/folder/mode summary.
- Empty state: no recent threads yet, prompt to start Chat.
- Failure state: thread store unavailable, show truthful local-only failure.
- Persistence: source of truth is the existing thread store, not widget settings.

### Services Status
- Purpose: show the health of runtime dependencies without noise.
- Interactions: open details, refresh, expose degraded states.
- Empty state: none; always renders a live summary.
- Failure state: explicit unhealthy or partial-data state, never a green placeholder.
- Persistence: no.

### Quick Actions
- Purpose: jump to the console surfaces operators use most.
- Interactions: navigate to Chat, Security, Tools, Providers, Projects, Workbench.
- Empty state: none.
- Failure state: disabled if a destination is unavailable, with explanation.
- Persistence: no.

### Security Snapshot
- Purpose: summarize findings and risk at a glance.
- Interactions: open Security Ops, drill into alert counts.
- Empty state: zero findings still shows counts.
- Failure state: sensor offline or partial data state must be explicit.
- Persistence: no.

### Activity Feed
- Purpose: show recent notable system and operator events.
- Interactions: open detail, scroll history.
- Empty state: no recent activity.
- Failure state: feed unavailable, display minimal recovery hint.
- Persistence: no, unless later backed by an audit feed contract.

### Chat Runtime Strip
- Purpose: keep provider, model, mode, and project truth visible.
- Interactions: change mode/provider/model, inspect binding state.
- Empty state: no active thread, show setup state.
- Failure state: invalid binding or missing provider/model must block sending.
- Persistence: active session binding persists; the strip itself does not store extra state.

### Thread Rail
- Purpose: navigator for pinned, recent, project-grouped, and archived threads.
- Interactions: select thread, pin/unpin, rename, move, archive, restore, merge, bulk select.
- Empty state: no threads yet, offer start-chat action.
- Failure state: storage unavailable or merge blocked, expose exact reason.
- Persistence: yes, via local thread store and any later durable sync layer.

### Diagnostics Panel
- Purpose: expose deeper runtime health, context, and degraded details.
- Interactions: expand/collapse, copy or inspect data if implemented later.
- Empty state: collapsed by default.
- Failure state: show only what is truthfully unavailable.
- Persistence: no.

### Composer Context Hint
- Purpose: reduce operator friction without adding chrome.
- Interactions: updates as thread/runtime state changes.
- Empty state: default helper text.
- Failure state: if runtime is degraded, say why before sending.
- Persistence: no.

## Widget System Model
- Widgets are live modules, not decorative cards.
- Each widget exposes title, summary, body, and actions.
- Core workflow widgets must be recoverable after removal.
- Default grid sizing should stay simple: compact, standard, wide.
- Failure states are visible and truthful, never hidden behind placeholder data.
