# Routing Replay Lab (P131)

The routing replay lab replays sanitized fixtures through an evaluation-only
path that mirrors provider selection constraints used by the live router.

## Scope

- Replay and compare candidate routes for `security_autopilot` and
  `agent_workbench` style tasks.
- Explain route selection inputs: task type, health, failover, and budget.
- Consume P130 budget semantics through `ai.budget_scoped.BudgetManager`.
- Never mutate production router defaults or provider registry state.

## Fixture Inventory

- `security_analysis_reasoning.json`
- `coding_agent_session.json`
- `degraded_provider_failover.json`
- `budget_constrained_session.json`
- `stale_metrics_health_variation.json`

All fixtures are deterministic, redacted, and safe to commit.

## Explanation Payload

Each replay returns a machine-testable payload with these keys:

- `requested_task_type`
- `task_chain`
- `available_candidates`
- `provider_health_inputs`
- `budget_constraints`
- `failover_conditions`
- `selected_route`
- `rejected_routes`
- `reason_summary`

## Running Replay

```bash
.venv/bin/python -c "from ai.routing_replay import replay_all_fixtures; import json; print(json.dumps(replay_all_fixtures(), indent=2))"
```

The replay module performs no outbound LLM calls and does not write to runtime
router config.
