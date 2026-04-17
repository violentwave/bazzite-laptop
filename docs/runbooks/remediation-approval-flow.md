# Runbook: Remediation Approval Flow

## Trigger / entry condition

- Security incident triage recommends remediation action.
- A P122 executor action is requested that is destructive or approval-gated.

## Prerequisites

- Policy mode and decision inspected from P120/P127 systems.
- Requested action is in the fixed P122 allowlist.
- Request payload validated and redacted-safe.

## Required evidence

- Policy decision trace (`PolicyResult` / MCP policy evaluation result).
- Approval metadata: approver, reason, ticket or phase reference.
- Relevant findings/incidents/evidence bundle IDs.

## Approval requirements

- No execution for high-risk actions without explicit approval metadata.
- Approval must be attributable, timestamped, and auditable.
- P128 step-up is required for privileged approval operations.

## Operator steps

1. Confirm action category and policy decision (auto, approval, blocked).
2. If approval is required, collect approver identity and change rationale.
3. Attach ticket or phase reference for high/critical operations.
4. Execute only via P122 fixed executor request path.
5. Review resulting audit event and evidence bundle for completion.

## Escalation path

- Escalate blocked decisions to security lead for policy review.
- Escalate malformed/unsafe payloads to incident owner for correction.

## Verification / exit criteria

- Decision outcome is one of: executed, prepared, rejected (deterministic).
- Audit event includes policy decision and approval state.
- Evidence bundle includes redacted payload and result metadata.

## Audit and handoff artifacts

- P122 audit entry (`sample-audit.jsonl` style structure in runtime ledger).
- Evidence bundle ID and request ID recorded in handoff.
- Follow-up runbook reference if further manual action is required.
