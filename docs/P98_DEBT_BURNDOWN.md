# P98 Debt Burn-Down Matrix — Console UX Truthfulness

This matrix captures remaining accepted UX debt reconciled in P98 with a runtime-truth-first policy.

| Issue | Panel | Prior Classification | Live Behavior Before | Figma / UX Expectation | Root Cause | P98 Resolution | Validation |
|---|---|---|---|---|---|---|---|
| Fake command entries in command palette | Global shell | Accepted debt (placeholder) | Palette listed tool/agent/theme actions that executed no real behavior | Palette should not promise non-wired actions | Legacy placeholder command list carried forward from shell scaffold | Removed non-functional command entries; limited palette to real navigation commands only in `ui/src/components/shell/CommandPalette.tsx` | `npx tsc --noEmit` pass, localhost behavior aligns with available actions |
| Fabricated notifications feed | Global shell | Accepted debt (placeholder) | Side panel rendered synthetic alerts not backed by runtime data | Notifications should reflect runtime events or clearly indicate unavailable stream | Static mock notifications left in active UI | Removed fabricated feed and non-wired footer actions; now shows explicit "not wired" status in `ui/src/components/shell/NotificationsPanel.tsx` | `npx tsc --noEmit` pass, panel no longer displays fake incidents |
| Persistent red badge with no source | Top bar | Accepted debt | Notification badge always visible regardless of runtime events | Badge should indicate actual unread notifications only | Hardcoded visual indicator | Removed always-on badge from `ui/src/components/shell/TopBar.tsx` | `npx tsc --noEmit` pass |
| Non-functional related-action deep-link | Security Alerts | Accepted debt | "View related" rendered as `href="#"` and implied navigation | Action references should be actionable or explicitly informational | Link placeholder was never wired to route/tool context | Replaced fake link with explicit informational copy in `ui/src/components/security/AlertFeed.tsx` | `npx tsc --noEmit` pass |
| Non-functional audit history affordance | Shell audit strip | Accepted debt | "History" button rendered with no handler | Controls should be functional or omitted | Leftover scaffold button | Removed non-functional control from `ui/src/components/shell/Layout.tsx` | `npx tsc --noEmit` pass |

## Validation Summary

- TypeScript: `cd ui && npx tsc --noEmit` ✅
- Python lint: `.venv/bin/ruff check ai/ tests/ scripts/` ✅
- Python tests: `.venv/bin/python -m pytest tests/ -q --tb=short` ✅ (`2188 passed, 183 skipped`)

## Remaining Debt (Intentional, Truthful)

- Notification event-stream backend is still not wired for live feed delivery.
- Security related actions remain informational when no deterministic deep-link target exists.
