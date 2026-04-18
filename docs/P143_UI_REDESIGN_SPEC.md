# P143 - Adaptive Minimalist UI Redesign Spec

## Design Goals
- Calm, minimalist control surface by default.
- Home and Chat stay distinct, but visually belong to one operator console.
- Project selection is the primary workflow entry.
- Runtime, provider, model, and diagnostics truth remain available, never fabricated.
- Power features stay reachable through progressive disclosure, not hidden away.

## Anti-Goals
- No fake data or simulated green states.
- No new backend/account/cloud model in this phase.
- No loss of archive/restore/merge/bulk capability.
- No redesign that turns Chat into a second Home.
- No decorative complexity that weakens operator trust.

## Redesign Bundle Summary
Source: `/home/lch/projects/bazzite-redesign/redesign_ui/`

Top-level contents:
- `README.md`, `COMPARISON_REPORT.md`, `ATTRIBUTIONS.md`
- `package.json`, `vite.config.ts`, `postcss.config.mjs`, `index.html`
- `src/main.tsx`, `src/app/App.tsx`
- `src/styles/*` for theme, tokens, fonts, and baseline layout
- `src/imports/*` for figma-imported reference assets and notes

Relevant nested UI files:
- `src/app/components/HomeDashboard.tsx`
- `src/app/components/ChatWorkspace.tsx`
- `src/app/components/MinimalHeader.tsx`
- `src/app/components/WidgetSelector.tsx`
- `src/app/components/widgets/*` for Active Project, Threads, Services, Security, Activity, Quick Actions, Projects
- `src/app/components/ui/*` for shadcn/radix primitives

What is visual/design-only:
- Theme files, primitive components, layout polish, imported Figma assets.
- Hardcoded sample data in widgets.
- Static screenshots/attribution/import notes.

What is implementation-ready:
- The widget-first Home structure.
- Preset selector behavior.
- Compact header and widget selector flow.
- Chat workspace split into rail, runtime strip, message feed, and diagnostics drawer.
- Bulk-select / merge / archive affordances.

What conflicts with current architecture:
- Static project/thread data.
- Local-only widget persistence without a durable settings contract.
- A separate Vite app shell that does not map 1:1 to the Next.js repo.
- Any design that replaces current live hooks with mock content.

What needs backend/state support:
- Durable widget order and preset persistence.
- Optional persistent workspace preferences beyond localStorage.
- Any future server-backed thread metadata expansion.

## Current Repo Comparison

### Home Dashboard
- Current repo: `HomeContainer.tsx` renders four fixed cards plus project launch and recent threads.
- Redesign: widget grid with a calmer header, explicit presets, and module selection.
- Reuse: `useAgentWorkbench`, `useProviders`, `useSecurity`, `useChat`, `home-dashboard.js` summaries.
- Replace: monolithic card layout and ad hoc status density.
- Defer: drag/reorder persistence until P146.

### Chat Workspace
- Current repo: `ChatContainer.tsx` already has runtime strip, diagnostics, message feed, and profile selector.
- Redesign: tighter header, clearer thread navigator, less always-visible noise, more compact runtime truth.
- Reuse: `useChat`, `ThreadSidebar`, `ChatInput`, `ChatMessage`, session binding helpers.
- Replace: duplicated or overly verbose diagnostics presentation.
- Defer: any deep refactor of message rendering that is purely aesthetic.

### Thread Rail
- Current repo: grouped pinned/recent/by-project/archive rail with bulk select and merge.
- Redesign: more professional navigator feel, clearer section hierarchy, fewer duplicated labels.
- Reuse: local thread store, pin/archive/move/merge actions, project grouping.
- Replace: dense menu clutter and repeated list exposure.
- Defer: non-local persistence of thread organization.

### Active Project Flow
- Current repo: select/register/open project, then bind to Chat or Workbench.
- Redesign: project selection is a primary Home action and an explicit runtime anchor.
- Reuse: existing workbench project discovery and registration validation.
- Replace: split, low-emphasis project controls.
- Defer: any backend project model rewrite.

### Runtime / Diagnostics
- Current repo: truth-heavy but still too present in some states.
- Redesign: compact summaries first, details only when expanded or when degraded.
- Reuse: `buildHomeSystemStatus`, `buildRuntimeStrip`, `buildDegradedStateSummary`.
- Replace: always-expanded diagnostics blocks.
- Defer: new telemetry sources not already in repo.

## Recommended Final Direction
Adopt the redesign as a layout and information-architecture target, not as a direct code port. Keep the existing Next.js app, live hooks, and local-first truth model; recompose them into a calmer Home, a more focused Chat, and a cleaner thread navigator.

## Home Information Architecture
- Minimal header with preset selector and add-widget action.
- One primary project card, then a small widget grid.
- Default widgets: Active Project, Recent Threads, Services Status, Quick Actions.
- Expert additions: Security Snapshot and Activity Feed.
- Empty state should still show project launch first.

## Chat Workspace Information Architecture
- Compact top bar with thread title, project binding, and runtime chips.
- Message feed stays central.
- Diagnostics live behind a disclosure control.
- Composer stays simple, but never hides runtime truth.

## Thread Rail Information Architecture
- Sections: Pinned, Recent, By Project, Archived.
- Bulk mode is an explicit state, not a hidden menu trick.
- Archive and merge remain first-class actions.
- Thread rail behaves like a navigator, not a storage dump.

## Active Project Flow
- Select existing project or register a new one.
- Make selection the default path into Chat or Workbench.
- Show root path and last-updated metadata, but keep it compact.

## Widget System Model
- A widget is a self-contained live module with title, summary, body, and actions.
- Widgets can be removed from Home, but core workflow widgets must be recoverable.
- Grid sizing should be simple: standard, wide, and full-width only.

## Guided / Standard / Expert Presets
- Guided: 3 core widgets, lowest density, hidden advanced diagnostics.
- Standard: balanced default, includes primary status and quick actions.
- Expert: full module set, richer visibility, denser layout.

## Progressive Disclosure Rules
- Default to summary text and counts.
- Expand on demand for diagnostics, audit, and raw metadata.
- Use modals/drawers for destructive or multi-step operations.
- Never hide failure states behind decoration.

## Visual Hierarchy Rules
- Primary actions use strong contrast.
- Secondary actions use borders or ghost treatment.
- Status colors: success, info, warning, danger only.
- Spacing should stay calm and consistent; no packed dashboards.

## Density / Spacing / Typography Guidance
- Use a restrained density on Home, slightly denser on Chat.
- Prefer short labels and one-line summaries.
- Reserve monospaced text for IDs, paths, and runtime tuples.
- Avoid overusing badges unless they convey real state.

## Empty-State Rules
- Empty states must explain the next operator action.
- Empty Home: select/register a project first.
- Empty Chat: start a thread from the selected project.
- Empty diagnostics: show what is unavailable and why.

## Archive / Restore / Merge UX Rules
- Archive is non-destructive and visible in Archived.
- Restore is always available from archived context.
- Merge requires explicit selection and confirmation.
- Archive-originals must remain an operator choice.

## Runtime / Diagnostics Visibility Rules
- Keep runtime truth visible in compact form.
- Show details only when expanded or when degraded.
- Never imply health if sources are partial or unavailable.

## Always Visible vs Collapsible
- Always visible: active project, selected runtime tuple, current thread title, primary message composer, essential navigation.
- Collapsible: deep diagnostics, audit/history, raw provider lists, low-priority activity detail.

## Implementation Notes and Migration
- Keep current Next.js architecture and live hooks.
- Do not port the redesign bundle as a separate app.
- Preserve current local-first thread behavior and operator truth rules.
- P144 should focus on Home only, P145 on Chat/rail only, P146 on personalization and persistence.
