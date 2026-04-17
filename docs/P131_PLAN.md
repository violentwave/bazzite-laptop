# P131 Plan — Routing Evaluation and Replay Lab

## Phase

- Phase: P131
- Name: Routing Evaluation and Replay Lab
- Backend: opencode
- Dependencies: P121, P130
- Execution mode: bounded

## Objective

Provide an evaluation-only replay lab that explains routing decisions across
provider health, task type, failover, latency/cost tradeoffs, and P130 budget
constraints.

## Scope Boundaries

- Do not mutate production routing defaults.
- Do not implement P132 runbooks, P133 provenance graph, or P138 canary
  automation.
- Do not add autonomous live route tuning.

## Deliverables

1. Sanitized replay fixture model and fixture inventory.
2. Replay engine that evaluates candidates and returns deterministic
   explanations.
3. Human-readable + machine-testable explanation schema.
4. Tests for stale metrics, failover, budget constraints, task-type differences,
   redaction, deterministic replay, and no production mutation.
5. Validation evidence and phase ledger updates.

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_routing_replay.py tests/test_router.py -q
ruff check ai/ tests/
.venv/bin/python -m pytest tests/test_budget_scoped.py tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py -q
```
