# Runbook: Privileged Workbench and Session Actions

## Trigger / entry condition

- Operator requests privileged project-agent action in Agent Workbench.
- Action touches secrets/settings, privileged policy controls, or high-risk
  operational changes.

## Prerequisites

- Project/session context is valid and within allowed roots (P129).
- Actor identity is verified and step-up state is current (P128).
- Requested action maps to existing allowlisted tool paths.

## Required evidence

- Workbench session ID and project ID.
- Policy evaluation outcome for requested tool/action.
- Step-up approval status and approver attribution when required.

## Approval requirements

- Privileged actions require P128 step-up and P127 approval alignment.
- Read-only workbench actions remain permitted without elevated approval.

## Operator steps

1. Validate project/session scope and actor context.
2. Determine whether action is read-only or privileged.
3. For privileged action, require step-up and attach approval metadata.
4. Execute through existing workbench/MCP pathway only.
5. Record session outcome and artifacts in handoff note.

## Escalation path

- Escalate failed step-up or policy-denied requests to security/platform lead.
- Escalate repeated context mismatches to workspace isolation review.

## Verification / exit criteria

- Action result is truthful (success, denied, or blocked) with reason.
- Session logs and handoff note include only redacted references.
- No cross-project access or unsafe command path is observed.

## Audit and handoff artifacts

- Session ID, project ID, and approval reference.
- Any policy audit IDs and remediation request IDs.
- Handoff note summarizing action, result, and next owner.
