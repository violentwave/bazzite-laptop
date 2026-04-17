# P131 Validation Evidence — Routing Evaluation and Replay Lab

**Phase:** P131 — Routing Evaluation and Replay Lab  
**Date:** 2026-04-17  
**Status:** PASS

## Git SHA

- Before: `be08087` (P130 final SHA)
- After: `(set by final P131 commit)`

## Replay Fixture Inventory

Sanitized fixtures created under `docs/routing_replay/fixtures/`:

1. `security_analysis_reasoning.json` — security-analysis style prompt
2. `coding_agent_session.json` — coding-agent session prompt
3. `degraded_provider_failover.json` — degraded provider + failover
4. `budget_constrained_session.json` — P130 budget-constrained route rejection
5. `stale_metrics_health_variation.json` — stale metrics effective-score cap

All fixtures are deterministic, secret-free, and path-redacted.

## Explanation Payload Schema

Schema is documented in `docs/routing_replay/explanation_schema.md` and emitted
by `ai/routing_replay.py` with stable keys:

- `requested_task_type`
- `task_chain`
- `available_candidates`
- `provider_health_inputs`
- `budget_constraints`
- `failover_conditions`
- `selected_route`
- `rejected_routes`
- `reason_summary`

## Budget-Constraint Comparison Summary

- Replay consumes P130 semantics via `ai.budget_scoped.BudgetManager` in an
  isolated temp DB (evaluation-only).
- `budget-constrained-session` fixture returns `allowed=false` with reason
  `token_limit_exceeded` and `selected_route=null`.
- Non-budget fixtures return `reason=no_budget` and continue normal selection.

## Failover / Stale-Metrics Summary

- Failover: `degraded-provider-failover` fixture rejects `groq` with
  `forced_failover` + unhealthy state and selects next viable provider.
- Stale metrics: `stale-metrics-health-variation` caps stale provider
  `effective_score` at `<= 0.8`, changing selected route outcome.

## Validation Commands and Results

```bash
$ .venv/bin/python -m pytest tests/test_routing_replay.py tests/test_router.py -q
35 passed

$ ruff check ai/ tests/
All checks passed!

$ .venv/bin/python -m pytest tests/test_budget_scoped.py tests/test_mcp_policy.py tests/test_security_autopilot_tools.py tests/test_agent_workbench.py -q
59 passed
```

## Redaction and Secret-Safety Statement

- Fixture loading fails fast if secret-like patterns or sensitive local paths are
  detected.
- Replay output redacts source/prompt text with path and secret masking.
- No API keys, tokens, credentials, or local sensitive paths are persisted in
  fixtures, explanations, or evidence.

## Known Limitations

1. Replay uses deterministic fixture inputs and does not execute live provider
   calls.
2. Candidate scoring is evaluation-oriented and does not alter production
   runtime routing weights.
3. Notion sync may require manual closeout if Notion MCP availability is
   degraded.

## Next-Phase Notes

- **P132:** Use replay explanations and rejected-route reasons as human review
  inputs; do not auto-execute remediations from replay outcomes.
- **P138:** Canary automation remains out of scope; replay can provide candidate
  comparison inputs for future gated canary work.
