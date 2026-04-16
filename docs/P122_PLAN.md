# P122 — Safe Remediation Runner

**Status:** Done  
**Date:** 2026-04-16  
**Dependencies:** P119, P120, P121  
**Risk Tier:** critical  
**Execution Mode:** manual-approval  
**Approval Required:** true  
**Backend:** opencode

## Objective

Implement a controlled remediation runner that executes only fixed, allowlisted,
policy-approved remediation actions, with deterministic rejection behavior,
audit/evidence records, and rollback metadata where possible.

## Dependencies

- P119 core autopilot models/audit/evidence primitives
- P120 policy engine and policy configuration
- P121 autopilot UI/data surfaces for evidence compatibility

## Implementation Scope

- Added `ai/security_autopilot/executor.py`:
  - fixed action registry metadata (category, destructive flag, approval
    requirement, payload schema, rollback availability)
  - structured request/result models:
    - `ExecutionApproval`
    - `RemediationExecutionRequest`
    - `RollbackMetadata`
    - `RemediationExecutionResult`
  - policy-gated executor flow:
    1. normalize request
    2. validate allowlisted action
    3. validate payload/path/shell/secret safety
    4. evaluate P120 policy decision
    5. enforce explicit approval where required
    6. execute fixed action or reject
    7. attach audit/evidence records
  - fixed `tool_runner` integration only for explicit tool names
- Updated `ai/security_autopilot/__init__.py` exports for executor types.
- Added `tests/test_security_autopilot_executor.py`.

## Fixed Action Catalog

- `refresh_threat_intel`
- `run_clamav_quick_scan`
- `run_health_snapshot`
- `run_log_ingest`
- `notify_operator`
- `prepare_quarantine_request`
- `prepare_service_disable_request`
- `prepare_secret_rotation_request`

No arbitrary action IDs are executable.

## Action Categories

- `scan`: `run_clamav_quick_scan`, `run_health_snapshot`
- `ingest`: `refresh_threat_intel`, `run_log_ingest`
- `notify`: `notify_operator`
- `quarantine`: `prepare_quarantine_request`
- `disable_service`: `prepare_service_disable_request`
- `rotate_secret`: `prepare_secret_rotation_request`

## Approval Model

- Policy decision is required for every request.
- If policy returns `approval_required` or action metadata marks approval
  required, request must include:
  - `approval.approved = true`
  - non-empty `approval.approver`
- Missing/invalid approval produces deterministic rejection.
- Destructive categories are represented as prepare-only operations in P122,
  not direct destructive execution.

## Safety Constraints

- Reject unknown action IDs.
- Reject malformed payloads and unexpected payload keys.
- Reject unsafe target paths (`..`, `/usr`, `/boot`, `/ostree`).
- Reject shell-like content (`bash`, `sh`, `sudo`, command chaining, command
  substitution patterns).
- Reject raw secret-like content (`api_key=`, `token=`, `password=`, `secret=`).
- Never execute model-produced raw shell text.
- No `shell=True` and no free-form command templates.

## Audit / Evidence Model

- Every attempted action (executed, prepared, or rejected) emits:
  - one redacted evidence bundle via `EvidenceManager`
  - one append-only audit event via `AuditLedger`
- Audit payload includes:
  - sanitized request reference
  - policy decision and reason
  - approval state
  - execution status
  - rollback metadata
  - evidence bundle ID reference

## Rollback Model

- Non-destructive execute actions: `rollback_possible = false`
- Prepare-only high-risk requests include rollback metadata:
  - `prepare_quarantine_request` → `cancel_quarantine_request`
  - `prepare_service_disable_request` → `cancel_service_disable_request`
  - `prepare_secret_rotation_request` → `cancel_secret_rotation_request`

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_security_autopilot_executor.py -q
ruff check ai/security_autopilot tests/test_security_autopilot_executor.py
.venv/bin/python -m pytest tests/ -q --tb=short
```

## Definition of Done

- Fixed allowlisted executor implemented.
- Policy gating and approval enforcement implemented.
- Unsafe execution paths deterministically rejected.
- Audit/evidence emitted for all attempted actions.
- Rollback metadata surfaced where applicable.
- Targeted and full validation commands pass.
- P122 docs, ledgers, and evidence updated.

## Definition of Not Done

- Any arbitrary shell command execution path exists.
- Any unknown action can execute.
- High-risk/destructive action executes without explicit approval.
- Missing audit/evidence for attempted actions.
- Validation results missing or failing without blocker documentation.

## Handoff / Update Requirements

- Update `HANDOFF.md` with P122 completion context and next phase pointer.
- Update `docs/PHASE_INDEX.md`, `docs/PHASE_ARTIFACT_REGISTER.md`, and
  `CHANGELOG.md`.
- Update Notion P122 row start/closeout fields and keep page body aligned.

## Next Phase

- P123 — Agent Workbench Core
