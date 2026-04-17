# P125 — Browser Runtime Acceptance

## Phase Overview

- **Phase:** P125
- **Name:** Browser Runtime Acceptance
- **Backend:** Full System Validation
- **Risk Tier:** critical
- **Execution Mode:** bounded
- **Approval Required:** false

## Dependencies

- P121 (Security Autopilot UI) - Done
- P124 (Agent Workbench UI) - Done

## Objective

Prove the Security Autopilot UI and Agent Workbench UI work end-to-end in a live browser against localhost MCP/LLM services, with real MCP responses and no misleading placeholders.

## Done Criteria

Browser evidence shows:
- Security Autopilot views (findings, incidents, evidence, audit, policy, remediation queue)
- Agent Workbench project picker, agent selector, git diff, tests, session state
- MCP bridge and LLM proxy health pass
- TypeScript, UI build, ruff, and tests pass

## Implementation Notes

- Use existing Bazzite tools and MCP patterns
- No P126 scope additions
- Browser evidence mandatory
- No fake success states

## Evidence

See: `docs/evidence/p125/validation.md`