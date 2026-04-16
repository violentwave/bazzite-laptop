# P119 — Security Autopilot Core

**Status:** Done  
**Date:** 2026-04-16  
**Dependencies:** P118  
**Risk Tier:** High  
**Backend:** opencode

## Objective

Implement a repo-native Security Autopilot core that uses existing Bazzite
security/system/log/agent signals to normalize findings, group incidents,
create redacted evidence bundles, and generate remediation plans.

P119 is strictly plan-only: no destructive autonomous remediation is allowed.

## Scope Delivered

- Added `ai/security_autopilot/` package with:
  - `models.py` for typed findings/incidents/decisions/plans/audit/evidence models.
  - `sensors.py` safe sensor adapters for approved Bazzite tool signals.
  - `classifier.py` heuristics for finding normalization + incident grouping.
  - `planner.py` remediation plan generation with explicit no-destructive constraints.
  - `audit.py` append-only audit ledger + redacted evidence manager.
  - `__init__.py` public exports for integration.
- Added `tests/test_security_autopilot.py` for model safety, sensor behavior,
  classification, incident grouping, redaction, planning, and audit chaining.

## Safety Boundaries

- No external SIEM introduced.
- No shell execution or autonomous mutating remediation added.
- `RemediationAction` rejects destructive actions by design.
- `RemediationPlan` enforces `execution_mode = "plan-only"`.
- Evidence handling redacts token/key/password/email patterns before persistence.

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_security_autopilot.py -q
ruff check ai/security_autopilot tests/test_security_autopilot.py
.venv/bin/python -m pytest tests/ -q --tb=short
```

## Notes

- Broader execution/policy gating integration is deferred to later phases.
- P119 intentionally ships core primitives only (models/adapters/classifier/planner/audit).
