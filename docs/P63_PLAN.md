# P63 Plan - Website Build Validation + UX/Visual QA

Status: Ready

## Objective

Implement a lightweight, evidence-driven QA layer for generated frontend work that fits this repository's Python control-plane architecture.

## Scope

- Define required QA evidence for frontend outputs:
  - checklist
  - screenshots
  - command outputs
- Keep validation workflow guidance in docs and retrievable patterns.
- Reuse existing orchestration, RAG, and MCP surfaces.
- Do not add a detached frontend runtime or persistent service.

## Architecture Fit

- This repository is not a frontend runtime; it is a control-plane.
- P63 should improve guidance, retrieval, and review orchestration for external frontend projects.
- Existing pattern retrieval already supports frontend metadata in Python:
  - `ai/rag/pattern_store.py`
  - `ai/rag/pattern_query.py`

## Deliverables

1. Validation documentation hardening
   - Update `docs/frontend-capability-pack/validation-flow.md` with required evidence package and storage format.
   - Normalize phase closure wording to `Done` where phase-control is referenced.

2. Frontend phase-status compatibility
   - Ensure phase-control maps `Complete` and `Completed` to `Done` in Notion parsing.

3. Frontend retrieval parity in MCP allowlist
   - Extend `knowledge.pattern_search` argument schema for:
     - `typescript`, `frontend`
     - `archetype`, `pattern_scope`, `semantic_role`

4. Notion phase hygiene
   - P61 and P62 closed.
   - P63 opened as Ready with normalized dependencies and automation-safe validation commands.

## Validation Strategy

Repository-level verification:

```bash
ruff check ai/ tests/ docs/
python -m pytest tests/ -q --tb=short
```

Phase-level evidence for generated websites (external project execution):

- Checklist evidence
- Screenshot evidence (mobile/tablet/desktop + reduced-motion)
- Command output evidence (lint/typecheck/test/build/a11y)

## Risks and Mitigations

- Risk: Notion uses `Complete` while phase-control expects `Done`.
  - Mitigation: parser maps `complete|completed` to `Done`.

- Risk: Validation commands in Notion use shell chaining.
  - Mitigation: store commands as newline-separated commands compatible with static argv execution.

- Risk: Frontend metadata exists in Python but not fully exposed in MCP argument schema.
  - Mitigation: align allowlist schema with existing query implementation.

## Out of Scope

- Creating a frontend build daemon or service inside this repository.
- Running full Node-based frontend QA inside this repository by default.
- Introducing a parallel knowledge or orchestration stack.
