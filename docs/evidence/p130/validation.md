# P130 Validation Evidence — Cost Quotas and Budget Automation

**Phase:** P130 — Cost Quotas and Budget Automation  
**Date:** 2026-04-17  
**Status:** PASS  

## Overview

This phase adds cost quotas and budget automation across providers, Security Autopilot analysis, and Agent Workbench sessions. Budget state is visible, enforceable, auditable, and safe.

## Budget Model Summary

Created two new modules:

### ai/budget_scoped.py
- **BudgetScope**: global, workspace, project, session, autopilot_run
- **EnforcementState**: active, warning, stopped, exhausted
- **AuditEventType**: budget_created, budget_assigned, warning_triggered, stop_triggered, routing_constrained
- **Budget**: Canonical budget model with token_limit, cost_limit_usd, spent_tokens, spent_cost_usd, warning_threshold_pct, stop_threshold_pct
- **BudgetManager**: Manages budgets across scopes with CRUD operations
- **create_session_budget()**: Helper for workbench session budgets
- **create_autopilot_budget()**: Helper for Security Autopilot run budgets

### ai/budget_routing.py
- **BudgetRoutingGuard**: Enforces budget constraints on provider routing
- **select_provider_with_budget()**: Filters providers by budget availability
- **check_budget_and_record()**: Check and record spend in one operation
- **get_budget_status_summary()**: Get summary of all active budgets

## Scope Model

| Scope Type | ID Pattern | Use Case |
|------------|-----------|----------|
| global | budget-{hex} | System-wide provider budget |
| workspace | budget-{hex} | Workspace-level budget |
| project | budget-{hex} | Project-specific budget |
| session | budget-{hex} | Workbench session budget |
| autopilot_run | budget-{hex} | Security Autopilot run budget |

## Warning/Stop Semantics

- **Warning**: When usage >= warning_threshold_pct (default 80%)
- **Stop**: When usage >= stop_threshold_pct (default 100%)
- **can_spend()**: Returns (allowed, reason) tuple
- **check_can_spend()**: Returns full state dict with usage_pct
- **record_spend()**: Records spend and triggers audit events on state changes

## Routing Constraint Summary

- **BudgetRoutingGuard.select_provider_with_budget()**: Filters providers by remaining budget
- Returns empty list when no valid providers due to budget constraint
- Includes constraint_info with reason, remaining_tokens, usage_pct
- Does NOT implement P131 replay behavior (replay consumed from constraints later)

## Audit Events

Emitted to `~/.config/bazzite-ai/budget-audit.jsonl`:
- `budget_created`: When budget is created
- `budget_assigned`: When budget is assigned to target
- `warning_triggered`: When usage crosses warning threshold
- `stop_triggered`: When usage crosses stop threshold
- `routing_constrained`: When provider routing is limited by budget

## Validation Commands

```bash
# Budget tests
$ python -m pytest tests/test_budget_scoped.py -q
17 passed

# Existing tests (no regressions)
$ python -m pytest tests/test_budget.py tests/test_identity_stepup.py tests/test_workspace_isolation.py tests/test_mcp_policy.py -q
84 passed

# Ruff lint
$ ruff check ai/budget_scoped.py ai/budget_routing.py tests/test_budget_scoped.py
All checks passed
```

## Key Enforcement Points

1. **Soft Warning**: When usage >= warning_threshold_pct (default 80%)
2. **Hard Stop**: When usage >= stop_threshold_pct (default 100%)
3. **No Silent Loss**: `allowed` flag in response indicates budget status
4. **No Fail-Open**: check_can_spend returns explicit reason codes
5. **Audit Trail**: All state changes logged to budget-audit.jsonl
6. **Sanitization**: No secrets/paths in budget outputs

## Artifacts

- `ai/budget_scoped.py` — Scoped budget model
- `ai/budget_routing.py` — Budget routing guard
- `tests/test_budget_scoped.py` — 17 budget tests
- `docs/evidence/p130/validation.md` — This file

## Result

**PASS** — Cost quotas and budget automation implemented with:
- Budget model with token/cost limits, warning/stop thresholds
- Session and autopilot budget helpers
- Provider routing respects budget constraints
- Audit events for warning/stop/routing
- No silent partial-result loss
- No infinite retry on exhaustion (truthful state in response)
- All tests pass

## Next Phase

P131 replay-lab behavior not implemented (consumes P130 constraints later). P133 provenance graph also not in scope.