# P113 Runtime UI Repair Evidence

**Date:** 2026-04-15
**Status:** In Progress

## Provider/Model Surface

### ModelsList Component
- File: `ui/src/components/providers/ModelsList.tsx`
- Purpose: Reusable models list with empty state
- Displays "No models available" when models list is missing or empty
- Exports to `ui/src/components/providers/index.ts`

### AddProviderPanel Component
- File: `ui/src/components/providers/AddProviderPanel.tsx`
- Purpose: Provider onboarding UX
- Lists known providers not yet configured
- Step-by-step instructions for manual config editing
- Disclaimer: "Provider config persistence is deferred to P115/P116. Manual config editing required until then."

### ProvidersContainer Updates
- Added "Add" tab to access AddProviderPanel
- Imports and renders AddProviderPanel when tab is active

### RoutingConsole Updates
- Added disclaimer: "Routing is controlled by backend config (litellm-config.yaml). Runtime persistence is deferred to P115/P116."

### Validation
- TypeScript: PASS (`npx tsc --noEmit`)
- Build: PASS (`npm run build`)

### Deferred to P115/P116
- Live provider config persistence (add/edit providers in UI)
- Live model switching persistence
- Provider registry CRUD operations
- Routing runtime configuration

## Shell Screen

### Components Checked
- `ShellContainer.tsx`: Uses useShellSessions hook, handles session create/execute/terminate
- `SessionTabs.tsx`: Tab management for sessions
- `TerminalCanvas.tsx`: Terminal output rendering
- `ShellStatusBar.tsx`: Status display

### Hooks Checked
- `useShellSessions.ts`: Core shell session management hook
- Handles sessions array, activeSession, sessionContext, output
- Error handling with descriptive messages

### Status
- No obvious broken imports detected
- Null-state handling present (activeSession checks)
- Empty state handling present (sessions.length === 0)

### Validation
- TypeScript: PASS
- Build: PASS

## Security Screen

### Components Checked
- `SecurityContainer.tsx`: Main container with tabs
- `SecurityOverview.tsx`: Overview panel
- `AlertFeed.tsx`: Alert display
- `FindingsPanel.tsx`: Scan findings display
- `HealthCluster.tsx`: Health status display

### Hooks Checked
- `useSecurity.ts`: Security state management
- Handles providers, models, security alerts, scan findings

### Status
- No obvious broken imports detected
- Null-state handling present
- Empty states handled appropriately

### Validation
- TypeScript: PASS
- Build: PASS

## Validations Run

1. `cd ui && npx tsc --noEmit` - PASS
2. `cd ui && npm run build` - PASS
3. Shell components reviewed - No obvious issues found
4. Security components reviewed - No obvious issues found

## Deferred Items for P115/P116

- Provider config persistence (add/edit/delete providers in UI)
- Model routing persistence (change primary/fallback providers in UI)
- Provider health auto-refresh configuration
- Live task type routing changes
- Provider onboarding wizard with API key validation
- Model availability auto-detection

## Notes

P113 provides targeted runtime UI improvements for provider onboarding and models display. The components are truthful about what they do vs. what requires P115/P116 persistence.
Shell and security screens have existing null-state and empty-state handling that appears functional.