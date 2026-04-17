# Runbook: Phase Execution and Closeout Handoff

## Trigger / entry condition

- High-risk phase execution starts, pauses, or completes.
- Approval-gated phase requires explicit human checkpoint.

## Prerequisites

- Preflight commands completed and recorded.
- Dependency phases confirmed done.
- Notion row status, approval requirement, and approval state verified.

## Required evidence

- Command validation logs (lint/tests/build/health as applicable).
- Evidence bundle path (`docs/evidence/pNNN/validation.md`).
- Final commit SHA and push confirmation.

## Approval requirements

- Manual-approval phases require explicit operator approval before code edits.
- Closeout to Done requires approval state transition to approved.

## Operator steps

1. Record preflight and dependency checks.
2. Confirm or obtain explicit approval for manual-approval phases.
3. Execute only scoped deliverables; block out-of-scope requests.
4. Run validation commands and capture pass/fail counts.
5. Update phase docs, ledgers, and handoff pointer with final SHA.
6. Post Notion closeout text with validation summary.

## Escalation path

- Escalate unresolved blockers or failed validations to phase owner.
- Escalate approval ambiguity before any implementation for gated phases.

## Verification / exit criteria

- Repo clean after push.
- Evidence file exists and references before/after SHA.
- PHASE_INDEX, PHASE_ARTIFACT_REGISTER, CHANGELOG, and HANDOFF updated.
- Notion row has status Done, approval state approved, commit SHA populated.

## Audit and handoff artifacts

- Final command result summary and evidence links.
- Notion closeout text used.
- `HANDOFF.md` update with next phase pointer and open tasks.
