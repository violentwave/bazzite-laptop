# P76 — Ingestion Reliability + Continuous Learning Automation

**Status**: In Progress  
**Dependencies**: 60, 70, 74, 75  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Automate phase-closeout ingestion so repo artifacts, Notion updates, RuFlo memory, LanceDB documents, task patterns, and related metadata are ingested reliably with coverage tracking and failure visibility.

## Scope

### Ingestion Targets

| Target | Description | Implementation |
|--------|-------------|----------------|
| Repo docs → LanceDB | Ingest P{NN}_PLAN.md, P{NN}_COMPLETION_REPORT.md | RepoDocsIngestionTarget |
| Notion phase row → RuFlo memory | Store phase summary for future retrieval | NotionMemoryIngestionTarget |
| Phase artifacts → Task patterns | Log high-signal execution patterns | TaskPatternIngestionTarget |
| HANDOFF.md → Shared context | Parse and store handoff entries | HandoffIngestionTarget |
| Test results → Coverage tracking | Record validation coverage metrics | ValidationCoverageIngestionTarget |

### Failure Handling

- Retry with bounded exponential backoff (3 retries, 1s base, 60s max)
- Dead-letter logging for persistent failures
- Failures visible but do not block phase completion
- Manual retry/re-run supported

### Trigger

Primary: PhaseControlRunner when phase transitions to DONE
Secondary: Manual via run_closeout_manually()

## Implementation

### New Files

- ai/phase_control/closeout.py — Core engine, retry logic, dead-letter handling
- ai/phase_control/closeout_targets.py — Concrete ingestion targets
- tests/test_phase_control_closeout.py — Test suite (22 tests)

### Key Classes

- CloseoutIngestionEngine — Orchestrates ingestion workflow
- RetryConfig — Configurable retry with exponential backoff
- CoverageMetrics — Tracks coverage across 5 dimensions
- IngestionResult — Per-target result with metadata
- CloseoutReport — Complete closeout report

### Integration

Closeout runs automatically when PhaseControlRunner completes a phase:

```python
if phase.status == PhaseStatus.DONE:
    closeout_report = self._run_closeout_ingestion(phase, run_id)
    phase.metadata["closeout_report"] = closeout_report.to_dict()
```

## Ingestion Contract

### What

Phase docs, metadata, task patterns, handoffs, validation coverage

### When

On phase completion (primary) or manual trigger (recovery)

### Where

- Docs → LanceDB docs table
- Phase summaries → RuFlo memory (graceful degradation if unavailable)
- Task patterns → LanceDB task_patterns table
- Handoffs/coverage → LanceDB shared_context table
- Failures → JSONL dead-letter file

### Success Criteria

- Full: All targets succeed
- Partial: Some succeed, failures logged
- Failures do not block phase completion

## Validation

22 tests covering all components, dry-run mode for safe testing.

## References

- P60 — Intelligence Reliability
- P70 — Phase Documentation
- P74 — Code Fusion
- P75 — Preflight + Execution Gating
