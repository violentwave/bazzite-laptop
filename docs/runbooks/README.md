# Human-in-the-Loop Runbooks (P132)

This directory contains high-risk operator runbooks that align with existing
policy, approval, audit, and identity controls.

## Runbook set

- `security-incident-triage.md`
- `remediation-approval-flow.md`
- `privileged-workbench-actions.md`
- `provider-outage-failover.md`
- `phase-execution-handoff.md`

Machine-readable workflow definitions live in `docs/runbooks/workflows/`.

## Alignment constraints

- P122 Safe Remediation Runner action bounds and audit model
- P127 MCP policy-as-code approval gates (default-deny, attributable approvals)
- P128 step-up security for privileged operations
- P131 routing replay outputs for failover and provider decision review

These runbooks are guidance and orchestration metadata only. They do not bypass
or replace backend policy or approval gates.
