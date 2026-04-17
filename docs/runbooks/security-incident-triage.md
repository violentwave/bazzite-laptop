# Runbook: Security Incident Triage and Escalation

## Trigger / entry condition

- Security Ops shows critical/high autopilot findings or active alerts.
- MCP health/status tools indicate malware, exploit activity, or repeated policy
  blocks requiring human review.

## Prerequisites

- Operator identity established and session attributable.
- Security Autopilot policy mode verified (`security.autopilot_policy`).
- MCP/LLM service health checked before deeper analysis.

## Required evidence

- `security.autopilot_overview`
- `security.autopilot_findings`
- `security.autopilot_incidents`
- `security.autopilot_evidence`
- `security.autopilot_audit`

## Approval requirements

- Investigation is read-only by default and does not require execution approval.
- Any transition to remediation must follow the remediation approval runbook and
  policy gates from P122/P127.

## Operator steps

1. Confirm incident severity and blast radius from findings and incidents.
2. Validate whether current policy mode permits only plan/recommend output.
3. Capture evidence bundle references and relevant audit IDs.
4. Classify decision: monitor, contain plan, or escalate for remediation review.
5. If containment/remediation is needed, hand off to remediation approval flow.

## Escalation path

- Escalate to security lead when severity is critical, repeated, or unclear.
- Escalate to platform operator if service health degradation limits evidence
  confidence.

## Verification / exit criteria

- Incident triage decision recorded with timestamp and operator identity.
- Evidence IDs and audit IDs linked in handoff notes.
- Next action explicitly selected: monitor-only or remediation approval.

## Audit and handoff artifacts

- Incident triage note in `HANDOFF.md` (no secrets/paths).
- Linked evidence IDs from autopilot evidence/audit outputs.
- Optional workflow run IDs if a machine-readable runbook workflow was used.
