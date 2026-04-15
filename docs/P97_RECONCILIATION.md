# P97 Reconciliation Matrix — Claimed vs Actual

This artifact records reality-based reconciliation for P89-P95 claims against live/runtime behavior and P96 design/source references.

| Issue | Panel | Claimed Fixed In | Actual Behavior Observed | Root Cause | Fix Applied | Validation Result |
|---|---|---|---|---|---|---|
| `window.prompt()` PIN prompts | Settings | P95 (accepted debt) | Browser-native prompt used for reveal/update/delete | Temporary UX shortcut persisted | Replaced with in-panel `Action PIN` input and reused PIN for secret actions in `ui/src/components/settings/SettingsContainer.tsx` | Typecheck pass; no `window.prompt` usage remains |
| `window.confirm()` delete dialog | Settings | P95 (accepted debt) | Browser-native confirm still used before delete | Temporary UX shortcut persisted | Replaced with two-step in-panel confirmation in `ui/src/components/settings/SecretsList.tsx` | Typecheck pass; no `confirm()` usage remains |
| Non-functional "View Audit Log" button | Settings | P95 (accepted debt) | Button had no handler | UI wiring gap | Added handler calling `settings.audit_log` and modal log viewer in `ui/src/components/settings/SettingsContainer.tsx` | MCP probe returns success object; UI now has click handler |
| Stale closure style in project errors | Projects & Phases | P95 | Error arbitration still depended on captured state path | Local error gating not fully normalized | Added local `hasError` arbitration in `ui/src/hooks/useProjectWorkflow.ts` | Typecheck pass |
| Security quick actions not executable | Security | P95 (partial) | Buttons marked "Coming Soon"; no MCP trigger | Placeholder state left in place | Wired quick scan and health check actions in `ui/src/components/security/SecurityContainer.tsx` + props in `ui/src/components/security/SecurityActionsPanel.tsx` | `security.run_scan` tool call succeeds; action message rendered |
| Chat health checks not wired | Chat | P95 (accepted debt) | Send attempted without checking bridge/proxy availability | Helper functions existed but unused | Added pre-send health preflight in `ui/src/hooks/useChat.ts` using `checkLLMProxyHealth` and `checkMCPBridgeHealth` | Typecheck pass |
| Active shell session not persisted | Terminal | P95 debt list | Session context lost on refresh/reload | No storage of active session ID | Added localStorage persistence in `ui/src/hooks/useShellSessions.ts` | Typecheck pass |
| Integer args rejected by bridge validator | Shell + Settings + others | Not explicitly tracked | Typed args (e.g., `limit`) treated as invalid unless string | `_validate_args` assumed all values are strings | Added typed validation support for `string/int/integer/number/boolean` in `ai/mcp_bridge/tools.py`; added tests in `tests/test_mcp_tools_validation.py` | Targeted pytest: 113 passed, 13 skipped |
| `project.context` returned null current phase | Projects & Phases | P93/P95 | Runtime context showed null phase and stale recommendation path | HANDOFF parser depended on old `## Current Phase` marker + broken workflow history import | Added HANDOFF recent-session fallback parsing and replaced invalid import with direct `workflow_runs` table read in `ai/project_workflow_service.py` | `project.context` now reports `current_phase=P97 in_progress`; `tests/test_project_workflow_service.py`: 10 passed |

## Runtime Evidence

- Services reachable:
  - `http://127.0.0.1:8766/health` → `{"status":"ok"...}`
  - `http://127.0.0.1:8767/health` → `{"status":"ok"...}`
  - `http://127.0.0.1:3000` → HTTP 200
- MCP probes after fix:
  - `shell.get_audit_log` with integer limit returns data (no type-validation failure)
  - `settings.audit_log` returns success payload
  - `security.run_scan` returns triggered=true
  - `security.run_health` currently returns service failure from host-side systemd timeout (explicitly surfaced, not masked)

## Remaining Non-Repo Blockers

- Notion API token used by this workspace can update existing phase rows but currently cannot create new database rows (`403` on `POST /v1/pages` with database parent).
- `security.run_health` depends on host service responsiveness (`system-health.service`) and can fail at runtime despite correct UI wiring.
