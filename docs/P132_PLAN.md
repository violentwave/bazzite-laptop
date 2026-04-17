# P132 Plan — Human-in-the-loop Orchestration Runbooks

## Phase

- Phase: P132
- Name: Human-in-the-loop Orchestration Runbooks
- Execution mode: manual-approval
- Risk tier: high
- Dependencies: P122, P126, P127

## Objective

Create explicit operator runbooks for high-risk operational workflows and add
machine-readable workflow metadata that surfaces required manual steps,
approval state, and escalation context.

## Scope

1. Add runbook corpus under `docs/runbooks/` for security triage, remediation
   approvals, privileged workbench actions, provider failover, and phase
   handoff.
2. Add machine-readable runbook workflow definitions in
   `docs/runbooks/workflows/*.yaml`.
3. Add loader/validator in `ai/workflows/runbooks.py`.
4. Surface runbook approval/manual-step metadata in existing workflow handlers
   without bypassing policy gates.
5. Add tests for runbook parsing/validation and workflow runbook surfacing.

## Boundaries

- Do not implement P133 provenance graph.
- Do not implement P135 integration governance execution.
- Do not implement P138 canary automation.
- Do not bypass P122/P127/P128 policy, approval, or audit controls.

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_runbooks.py tests/test_workflow*.py -q
ruff check ai/ tests/
```
