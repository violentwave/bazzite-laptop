# P120 — Security Policy Engine

**Status:** Done  
**Date:** 2026-04-16  
**Dependencies:** P119  
**Risk Tier:** Critical  
**Execution Mode:** manual-approval  
**Backend:** opencode

## Objective

Implement the Security Autopilot policy engine and configuration model that
determines whether actions are `auto_allowed`, `approval_required`, or
`blocked`, while preventing arbitrary AI-driven execution.

## Dependencies

- P119 Security Autopilot Core (`d502c21`) for remediation models, planner
  outputs, and existing safety posture.

## Implementation Scope

- Added `ai/security_autopilot/policy.py`:
  - policy mode enum (`monitor_only`, `recommend_only`, `safe_auto`,
    `approval_required`, `lockdown`)
  - decision enum (`auto_allowed`, `approval_required`, `blocked`)
  - action category enum (all P120 categories)
  - `PolicyRequest` / `PolicyResult` data models
  - `SecurityAutopilotPolicy` evaluator
  - `load_policy_config(path: Path | None = None)`
  - `evaluate_action(request: PolicyRequest) -> PolicyResult`
  - `evaluate_remediation_action(...)` integration for P119 `RemediationAction`
  - payload redaction helper for decision/audit output safety
- Added `configs/security-autopilot-policy.yaml` with safe defaults.
- Added `tests/test_security_autopilot_policy.py` coverage for allow/approval/
  block paths, malformed input, redaction, config loading, lockdown behavior,
  and P119 integration.

## Policy Modes

- `monitor_only`: observe-only behavior; no remediation auto-execution.
- `recommend_only`: recommendation-focused mode; no risky remediation execution.
- `safe_auto`: allows only explicitly safe non-destructive categories.
- `approval_required`: risky/destructive categories require manual approval.
- `lockdown`: only read-only/evidence operations permitted.

## Action Categories

- `read_only`, `scan`, `evidence`, `notify`, `ingest`
- `quarantine`, `terminate_process`, `disable_service`, `rotate_secret`,
  `firewall_change`, `delete_file`
- `arbitrary_shell`, `sudo`, `secret_read`, `system_write`, `unknown`

## Default Policy Behavior

- `arbitrary_shell`, `sudo`, and `secret_read` are always blocked.
- Destructive categories are never auto-allowed by default.
- `lockdown` blocks everything except read-only/evidence actions.
- Target path validation blocks `system_write`/`delete_file` requests outside
  allowlisted roots.
- Sensitive payload fields are redacted before policy output/audit metadata.

## Safety Constraints

- No arbitrary shell execution.
- No `shell=True` usage.
- No sudo automation.
- No destructive remediation execution.
- No raw secret exposure.
- No external SIEM dependency introduced.
- No policy bypass framework added outside existing Bazzite architecture.

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_security_autopilot_policy.py -q
ruff check ai/security_autopilot tests/test_security_autopilot_policy.py
.venv/bin/python -m pytest tests/ -q --tb=short
```

## Definition of Done

- Policy engine exists and enforces mode/category decisions.
- YAML policy config exists and is loaded safely.
- Input validation rejects malformed mode/category/action.
- Sensitive values are redacted in policy outputs.
- P119 remediation actions evaluate through policy without execution.
- Tests pass for required P120 behaviors.
- Notion row and page body updated for Security Policy Engine scope.

## Handoff and Update Requirements

- Update `HANDOFF.md` with P120 completion state.
- Update `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`, and
  `CHANGELOG.md`.
- Update Notion P120 row closeout fields and replace stale page body content.

## Next Phase

- P121 — Security Autopilot UI
