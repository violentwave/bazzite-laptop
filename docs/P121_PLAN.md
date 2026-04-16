# P121 — Security Autopilot UI

**Status:** Done  
**Date:** 2026-04-16  
**Dependencies:** P119, P120  
**Risk Tier:** High  
**Execution Mode:** bounded  
**Backend:** opencode

## Objective

Extend the Unified Control Console Security Ops panel with Security Autopilot
surfaces: `Overview`, `Findings`, `Incidents`, `Evidence`, `Audit`, `Policy`,
and `Remediation Queue`, while preserving plan-only and no-destructive-action
constraints.

## Scope Delivered

- Added read-only Security Autopilot tool aggregation module:
  - `ai/security_autopilot/ui_service.py`
  - normalizes findings from existing security signals
  - groups incidents
  - derives redacted evidence bundles
  - reads audit ledger events
  - exposes policy summary and plan-only remediation queue
- Added MCP tool handlers in `ai/mcp_bridge/tools.py`:
  - `security.autopilot_overview`
  - `security.autopilot_findings`
  - `security.autopilot_incidents`
  - `security.autopilot_evidence`
  - `security.autopilot_audit`
  - `security.autopilot_policy`
  - `security.autopilot_remediation_queue`
- Added allowlist entries in `configs/mcp-bridge-allowlist.yaml` for all
  `security.autopilot_*` read-only tools.
- Added UI hook/types and panel rendering:
  - `ui/src/types/security-autopilot.ts`
  - `ui/src/hooks/useSecurityAutopilot.ts`
  - `ui/src/components/security/AutopilotPanels.tsx`
  - updated `ui/src/components/security/SecurityContainer.tsx` tab set and
    rendering pipeline for the seven P121 surfaces.
- Added tests:
  - `tests/test_security_autopilot_tools.py`

## Safety Boundaries Maintained

- No destructive remediation execution added.
- Remediation queue remains explicitly plan-only.
- Evidence is redacted and exposed as read-only UI data.
- No raw secret reads or arbitrary shell/sudo automation introduced.

## Validation

```bash
cd ui && npx tsc --noEmit
cd ui && npm run build
.venv/bin/python -m pytest tests/test_security_autopilot_tools.py -q
ruff check ai/ tests/
.venv/bin/python -m pytest tests/ -q --tb=short
```

Validation outcome:
- UI typecheck/build passed.
- P121 targeted tests passed.
- Full test suite passed (2421 passed, 183 skipped).
- Ruff passed.

## Artifacts

- `docs/evidence/p121/validation.md`

## Next Phase

- P122 — Security Autopilot Workflow + Execution Governance UI (as planned in
  roadmap/Notion).
