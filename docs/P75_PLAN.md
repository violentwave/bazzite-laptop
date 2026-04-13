# P75 Plan - Project Intelligence Preflight + Execution Gating

Status: In Progress

## Objective

Make intelligence retrieval a required preflight step before implementation by generating a phase-native preflight summary that combines phase state, artifacts, code context, task patterns, and health signals.

## Scope

- Reuse existing `ai/phase_control` orchestration path.
- Add a structured preflight payload + gate decision before backend execution.
- Inject preflight summary into execution prompt generation.
- Persist preflight context for auditability without creating a new orchestration stack.

## Minimum Preflight Payload

- Phase context (number, status, mode, risk, dependencies)
- Artifact context (phase docs, handoff snippets, artifact register ref)
- Code context (fused retrieval + impact summary)
- Pattern context (task patterns, agent knowledge, shared context)
- Health signals (timers, pipeline, provider health)
- Gate decision (allowed, severity, blockers, warnings)

## Deliverables

1. New preflight builder in `ai/phase_control/preflight.py`.
2. New `PreflightRecord` model in `ai/phase_control/result_models.py`.
3. New policy gate in `ai/phase_control/policy.py`.
4. `PhaseControlRunner.run_once()` consumes preflight before executing backend.
5. Backend request includes preflight summary + record.
6. New tests for preflight + runner gating behavior.
7. Phase docs/handoff/index/register updated per policy.

## Validation

```bash
ruff check ai/ tests/ docs/
python -m pytest tests/ -q --tb=short
rg -n "preflight|phase context|artifact context|code context|task patterns|health signals" ai docs .opencode
```
