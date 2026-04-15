# P98 — Console UX Debt Burn-Down + Figma Parity

**Status:** Complete  
**Dependencies:** P96, P97  
**Risk Tier:** High  
**Backend:** opencode  
**Execution Mode:** UI Reconciliation

## Objective

Resolve remaining accepted console UI debt and tighten parity between the live localhost console and the P96 Figma/Notion source material, while preserving truthful runtime/degraded states.

## Why P98

- P95 classified several UI debts as acceptable for launch.
- P97 reconciled claimed-vs-actual issues and fixed high-impact mismatches.
- P98 focuses on remaining UX polish and non-functional affordances that can now be cleaned up without masking backend/runtime truth.

## Source of Truth

1. `HANDOFF.md`
2. `docs/AGENT.md`
3. P96 Notion bundle child pages
4. `docs/P97_RECONCILIATION.md`
5. P89-P97 docs and closeouts
6. `docs/PHASE_DOCUMENTATION_POLICY.md`
7. `docs/PHASE_INDEX.md`
8. `docs/PHASE_ARTIFACT_REGISTER.md`

## Pre-flight (P98)

- `git status` and `git log --oneline -10` captured
- `ruff check ai/ ui/src/ tests/ docs/ 2>&1 | tail -100` captured (known pre-existing `docs/zo-tools/*` lint debt)
- `python -m pytest tests/ -q --tb=short 2>&1 | tail -160` captured (`2188 passed, 183 skipped`)
- `cd ui && npx tsc --noEmit` captured (pass)
- Notion phase status check:
  - P96: Done
  - P97: not present in DB
  - P98: created

## Focus Areas

1. Settings interaction polish and in-panel usability
2. Chat runtime completeness indicators
3. Security/Providers/Projects non-functional affordance cleanup
4. Shell UX truthfulness and side-pane clarity
5. Figma parity alignment where repo-feasible

## Validation Commands

- `cd ui && npx tsc --noEmit`
- `python -m pytest tests/ -q --tb=short`
- Manual localhost validation across Settings, Chat, Security, Projects, Terminal
- Compare live UI against P96 bundle and `docs/P97_RECONCILIATION.md`
