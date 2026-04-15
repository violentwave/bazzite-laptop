# P99 Evidence Baseline — Live Console Rebaseline

Evidence timestamp: `2026-04-14T21:32Z`  
Live URL: `http://127.0.0.1:3000`

## Evidence Inputs

- `docs/evidence/p99/panel-evidence.json`
- `docs/evidence/p99/panel-visible-text.json`
- Screenshots:
  - `docs/evidence/p99/screenshots/chat.png`
  - `docs/evidence/p99/screenshots/settings.png`
  - `docs/evidence/p99/screenshots/models.png`
  - `docs/evidence/p99/screenshots/security.png`
  - `docs/evidence/p99/screenshots/projects.png`
  - `docs/evidence/p99/screenshots/terminal.png`
- Service health from host shell:
  - `curl -sS http://127.0.0.1:8766/health` -> ok
  - `curl -sS http://127.0.0.1:8767/health` -> ok
- Browser-context network probes:
  - `fetch("http://127.0.0.1:8766/health")` -> `TypeError: Failed to fetch`
  - `fetch("http://127.0.0.1:8767/health")` -> `TypeError: Failed to fetch`

## Panel Validation Matrix

| Panel | P96/P77-P88 Expected State | Observed Localhost Behavior | Screenshot | Status | Classification | Remaining Issues | Recommended Next Action |
|---|---|---|---|---|---|---|---|
| Chat | Primary interaction surface with live-ready input and MCP/LLM integration | Header and shell wiring correct; welcome/suggestions render; panel reachable | `docs/evidence/p99/screenshots/chat.png` | Partial pass | fixed | Runtime execution path not proven in this capture because cross-origin fetch fails in browser context | Add same-origin proxy route for MCP/LLM calls, then re-run send-message and tool-call evidence pass |
| Settings | PIN-gated settings/secrets with unlock/setup and audit actions | Panel renders PIN protection flow; shows setup path; also shows MCP bridge connectivity error | `docs/evidence/p99/screenshots/settings.png` | Fail | still defective | Browser cannot reach MCP bridge from UI context | Route settings calls through same-origin API layer or enable strict localhost CORS policy for UI origin |
| Providers | Health/models/routing tabs with runtime data and degraded states | Panel loads shell chrome and tabs; data section in connection-failed state (`Failed to fetch`) | `docs/evidence/p99/screenshots/models.png` | Fail | still defective | Provider calls fail despite backend being healthy from host shell | Fix browser-to-bridge connectivity path, then validate provider health/model/routing payload rendering |
| Security | Overview/alerts/findings/health tabs with action sidebar and truthful degraded states | Panel reaches global header but main content is `Security Data Unavailable` with retry only | `docs/evidence/p99/screenshots/security.png` | Fail | still defective | No security payload due browser fetch failure | Restore reachable MCP path first; then verify alert feed, findings, quick actions, and health tab behavior |
| Projects & Phases | Context/timeline/workflows/artifacts with recommendations and truthful sync status | Panel structure renders; data load fails (`Project data load failed: Failed to fetch`); fallback placeholders shown | `docs/evidence/p99/screenshots/projects.png` | Partial fail | accepted debt | Truthful fallback is correctly shown, but primary data path is non-functional | Keep truthful fallback; resolve connectivity to recover live context payloads |
| Terminal / Shell Gateway | Session controls, side pane, audit/context strip, command execution lifecycle | Panel and controls render (`+ New Session` present), but state reports error/no active session under failed data path | `docs/evidence/p99/screenshots/terminal.png` | Partial fail | still defective | Session list/context retrieval not reachable from UI runtime | Repair browser-to-MCP connectivity, then capture session create/execute/audit evidence |

## Cross-Panel Findings

1. **Shell and navigation parity improved**: P97/P98 UI reconciliation changes are visible (no fake placeholder command set, no fake notifications feed/badge).
2. **Primary runtime blocker is systemic**: host services are healthy, but browser context cannot fetch bridge/proxy endpoints (`TypeError: Failed to fetch`).
3. **Truthful degraded rendering is present**: panels show explicit failure/fallback states instead of fabricated success.

## Debt Classification Snapshot

- **fixed**: 2 (shell-level anti-fake affordances and truthful UI surfaces from P98 remain in place)
- **deferred**: 0 (P80 remains historical deferred scope)
- **accepted debt**: 1 (Projects truthful fallback while primary data path unavailable)
- **still defective**: 4 (Settings, Providers, Security, Terminal primary runtime paths)

## Trust-Restore Baseline

The live console now has a reliable truth baseline:

- Structural UI and phase reconciliation work from P97/P98 is visible.
- Core data-backed panel behavior is currently blocked by browser reachability to MCP/LLM endpoints.
- Future phases must treat browser-to-backend connectivity as the first gating fix before claiming panel-level completion.

## Notion Validation Summary (Ready to Paste)

P99 complete: rebaselined the live console with browser-verified localhost evidence across Chat, Settings, Providers, Security, Projects, and Terminal. Captured screenshots and structured evidence (`docs/evidence/p99/*`) and compared observed behavior against P96 reference docs plus P97/P98 reconciliation artifacts. Confirmed shell-level anti-fake affordance cleanup from P98 remains in place, but identified a systemic runtime defect where browser-context requests to MCP (`:8766`) and LLM proxy (`:8767`) fail with `TypeError: Failed to fetch` despite host health endpoints being healthy. Classified remaining debt explicitly (fixed/accepted debt/still defective), updated phase index/register/handoff, and established an evidence-backed trust baseline for follow-on remediation.
