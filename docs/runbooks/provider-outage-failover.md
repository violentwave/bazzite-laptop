# Runbook: Provider Outage and Routing Failover

## Trigger / entry condition

- Provider health issues, repeated routing failures, or degraded response quality.
- Security or workbench workflows are impacted by provider availability.

## Prerequisites

- Current provider health snapshot captured.
- Routing profile and budget status available.
- P131 replay lab available for decision support.

## Required evidence

- `system.provider_status`
- `providers.health`
- `providers.routing`
- Replay explanation payload from `ai.routing_replay` for similar scenario

## Approval requirements

- Diagnostic/routing evaluation is read-only and does not require approval.
- Any provider mutation follows existing provider registry and policy controls.

## Operator steps

1. Confirm outage/degradation symptoms from health and routing tools.
2. Run replay fixture closest to observed scenario (failover/stale/budget).
3. Compare selected and rejected routes with reason summary.
4. Choose bounded operator action: wait, route profile adjustment, or incident
   escalation.
5. Record rationale and references in handoff/evidence.

## Escalation path

- Escalate multi-provider failure to platform owner immediately.
- Escalate persistent auth failures to secrets/credentials rotation process.

## Verification / exit criteria

- Failover recommendation includes explicit provider health and budget context.
- Any manual change request references policy and approval requirements.
- Routing replay evidence is attached for post-incident review.

## Audit and handoff artifacts

- Provider status snapshots and replay fixture IDs used.
- Route explanation payload summary (redacted).
- Ticket/phase reference for any approved provider-side changes.
