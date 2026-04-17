# Phase Documentation Policy — Bazzite AI Layer

> Rules for future artifact placement, naming conventions, and documentation standards.
> Generated 2026-04-12. Apply to all phases P70+.

## Purpose

This policy ensures that future phases produce consistent, discoverable documentation artifacts that integrate with the phase tracking system in both the repository and Notion.

## Scope

This policy applies to:
- All new phases P70 and beyond
- Retroactive documentation for P0-P69 where gaps exist
- Cross-phase documentation (indexes, roadmaps, evolution docs)

## Phase-Owned Artifacts

### Required Artifacts

Each completed phase MUST have:

| Artifact Type | File Pattern | Example | Must Have |
|---------------|--------------|---------|-----------|
| Planning Doc | `docs/P{NN}_PLAN.md` | `P70_PLAN.md` | Yes, unless stabilization phase |
| Completion Report | `docs/P{NN}_COMPLETION_REPORT.md` | `P70_COMPLETION_REPORT.md` | Optional, for complex phases |
| Notion Row | Database: `Bazzite Phases` | Phase 70 row | Yes, always |

### Optional Artifacts

| Artifact Type | File Pattern | Example | When to Use |
|---------------|--------------|---------|-------------|
| Training Summary | `docs/P{NN}_TRAINING_SUMMARY.md` | `P61_TRAINING_SUMMARY.md` | When training materials created |
| Remediation Summary | `docs/P{NN}_REMEDIATION_SUMMARY.md` | `P60_REMEDIATION_SUMMARY.md` | When fixing prior phase issues |

### Stabilization Phases

Phases labeled as "stabilization" or "process" phases (P22-P23, P42-P43, P56, P58) may omit `_PLAN.md` files. Instead, document in HANDOFF.md and Notion Validation Summary.

## Artifact Placement Rules

### Phase-Owned Artifacts → `docs/P{NN}_*`

Files specific to a single phase go in the repository root `docs/` directory with the phase number prefix.

**Examples:**
- `docs/P70_PLAN.md` — Planning document for P70
- `docs/P70_COMPLETION_REPORT.md` — Completion report for P70
- `docs/P44_INPUT_VALIDATION_SUMMARY.md` — Input validation analysis (if needed)

**Do NOT:**
- Create phase subdirectories (`docs/P70/`) — unnecessary nesting
- Mix phase artifacts with module code (`ai/security/P44_*.md`) — documentation belongs in `docs/`

### Cross-Phase Artifacts → `docs/` Root

Files that span multiple phases or serve as indexes go in `docs/` root without phase number prefix.

**Examples:**
- `docs/PHASE_INDEX.md` — Master index of all phases
- `docs/PHASE_DEPENDENCY_GRAPH.mmd` — Dependency visualization
- `docs/ARCHITECTURE_EVOLUTION.md` — Architecture evolution narrative
- `docs/PHASE_DOCUMENTATION_POLICY.md` — This policy document

### Module Documentation → Module Directory

Documentation for code modules stays with the module.

**Examples:**
- `ai/orchestration/README.md` — Orchestration module doc
- `ai/security/input_validator.py` docstrings — Inline documentation
- `docs/newelle-system-prompt.md` — Historical legacy-assistant integration doc

### Frontend Capability Pack → `docs/frontend-capability-pack/`

All frontend capability documentation goes in the dedicated directory.

**Examples:**
- `docs/frontend-capability-pack/README.md` — Entry point
- `docs/frontend-capability-pack/runtime-harness.md` — Runtime documentation
- `docs/patterns/frontend/hero-section.md` — Frontend patterns

## Notion Integration

### Required Fields

Every Notion phase row must have:

| Property | Format | Example |
|----------|--------|---------|
| Name | `P{NN} — {Title}` | `P70 — Phase Documentation Overhaul` |
| Phase Number | Integer | `70` |
| Status | Ready / InProgress / Done | `Done` |
| Commit SHA | Short form (8 chars) | `1ac7264` |
| Finished At | ISO date | `2026-04-12` |
| Validation Summary | Prose, not JSON | Normalized text describing deliverables |

### Validation Summary Format

**Good:**
```
P70 complete: Created PHASE_INDEX.md, PHASE_ARTIFACT_REGISTER.md, dependency graph, timeline, architecture evolution, and documentation policy. Updated AGENT.md and AGENTS.md with policy references. Created Notion cross-phase pages.
```

**Bad (old format):**
```
{"files": ["docs/PHASE_INDEX.md"], "status": "validated", "raw": "Planned documentation normalization..."}
```

Convert old JSON/prose summaries to clean prose format when updating Notion.

### Child Pages

Phase-specific documentation can be added as Notion child pages under the phase row. However:

**Fallback:** If Notion API child-page creation is limited or unreliable, use linked references in the Validation Summary field instead.

Document the limitation in the Validation Summary:
```
Note: Artifact represented via linked reference due to Notion API child-page limitation. See docs/PHASE_ARTIFACT_REGISTER.md for canonical listing.
```

## Minimum Artifact Set

Every mature phase should have:

1. **Planning Document** (`P{NN}_PLAN.md`)
   - Objective
   - Scope
   - Deliverables
   - Done criteria
   - Validation commands

2. **Test Evidence** (commit log or explicit test results)
   - `pytest tests/` output
   - `ruff check` output
   - Coverage or validation summary

3. **Notion Row** with:
   - Commit SHA (short form)
   - Finished At (date)
   - Validation Summary (prose)

4. **HANDOFF.md update** — Record what was done in the session

## Historical Phases (P0-P69)

### Gaps and Exceptions

The following phases lack dedicated plan documents:

| Phases | Reason |
|--------|--------|
| P0-P9 | Inferred historical boundaries, no explicit planning artifacts |
| P10-P18 | Rapid development, planning was informal |
| P19-P21 | Validation via Notion only |
| P34-P36 | Batch-committed, shared commit SHA |
| P45-P49 | Referenced in P44 validation |
| P56, P58 | Stabilization phases |

**Action:** Do not create retroactive plan documents for these phases. Mark them as "no dedicated plan doc" in PHASE_ARTIFACT_REGISTER.md.

### Duplicate Files

Several `docs/performance-*.md` files exist with different casing. Consolidate in a future pass if needed, but do not block P70 on cleanup.

## Documentation Workflow

### During Phase Execution

1. **Pre-flight**: Read HANDOFF.md, check which phase was last completed
2. **Create plan**: `docs/P{NN}_PLAN.md` if needed
3. **Execute**: Follow plan deliverables
4. **Validate**: Run `ruff check`, `pytest`, validation commands
5. **Record in Notion**: Update Status, Commit SHA, Finished At, Validation Summary
6. **Update HANDOFF.md**: Record what was done, commit SHA
7. **Create completion report** (optional): `docs/P{NN}_COMPLETION_REPORT.md` for complex phases

### After Phase Completion

1. Update PHASE_INDEX.md with new phase
2. Update PHASE_ARTIFACT_REGISTER.md with new artifacts
3. Update PHASE_DEPENDENCY_GRAPH.mmd if dependencies changed
4. Update PHASE_DELIVERY_TIMELINE.md with new phase entry
5. Update ARCHITECTURE_EVOLUTION.md if architecture changed
6. Update docs/AGENT.md and .opencode/AGENTS.md if rules changed

### Cross-Phase Documentation Updates

When adding cross-phase docs (indexes, roadmaps):

1. Create/update in `docs/` root
2. Reference from relevant phase rows in Notion
3. Reference from AGENT.md or AGENTS.md if agent-facing
4. Update PHASE_DOCUMENTATION_POLICY.md if new policy emerges

## Notion Database Schema

Do NOT modify the Bazzite Phases database schema. The current schema is:

| Property | Type | Notes |
|----------|------|-------|
| Name | Title | Phase title |
| Phase Number | Number | Integer identifier |
| Status | Select | Ready / InProgress / Done |
| Commit SHA | Rich Text | Short form (8 chars) |
| Finished At | Date | ISO date |
| Validation Summary | Rich Text | Prose, not JSON |
| Dependencies | Rich Text | Comma-separated phase numbers |
| Objective | Rich Text | Phase objective |
| Done Criteria | Rich Text | Completion criteria |
| Execution Prompt | Rich Text | Full prompt text |
| Validation Commands | Rich Text | Shell commands |

## File Naming Conventions

| Type | Convention | Example |
|------|------------|----------|
| Plan | `P{NN}_PLAN.md` | `P70_PLAN.md` |
| Completion | `P{NN}_COMPLETION_REPORT.md` | `P70_COMPLETION_REPORT.md` |
| Training | `P{NN}_TRAINING_SUMMARY.md` | `P61_TRAINING_SUMMARY.md` |
| Remediation | `P{NN}_REMEDIATION_SUMMARY.md` | `P60_REMEDIATION_SUMMARY.md` |
| Roadmap | `phase-roadmap-p{nn}.md` | `phase-roadmap-p53.md` |
| Prompt | `cc-prompts-p{nn}-{topic}.md` | `cc-prompts-p42-stabilization.md` |

## Enforcement

This policy is enforced by:

1. **AGENT.md** — Reference in Phase Implementation Rules section
2. **.opencode/AGENTS.md** — Reference in phase execution workflow
3. **PHASE_INDEX.md** — Master index links to policy
4. **PHASE_ARTIFACT_REGISTER.md** — Inventory tracks compliance

## Exceptions

Exceptions require explicit documentation in PHASE_ARTIFACT_REGISTER.md under "Known Gaps" section, with rationale.

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-12 | 1.0 | Initial policy for P70+ |
