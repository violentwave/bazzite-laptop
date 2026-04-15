# P99 — Live Console Evidence Rebaseline + Trust Restore

**Status:** Complete  
**Dependencies:** P96, P97, P98  
**Risk Tier:** High  
**Backend:** opencode  
**Execution Mode:** Quality Verification

## Objective

Run a browser-verified localhost evidence pass across all six core console panels and establish a trustworthy baseline that distinguishes what is fixed, deferred, accepted debt, or still defective.

## Source of Truth Order

1. `HANDOFF.md`
2. `docs/AGENT.md`
3. P96 Figma/Notion bundle references (`docs/P96_PLAN.md` + mapped P77/P78/P79/P81-P88 docs)
4. `docs/P97_RECONCILIATION.md`
5. `docs/P98_DEBT_BURNDOWN.md`
6. Relevant P89-P98 docs and closeouts
7. `docs/PHASE_DOCUMENTATION_POLICY.md`
8. `docs/PHASE_INDEX.md`
9. `docs/PHASE_ARTIFACT_REGISTER.md`

## Pre-flight Results

- `git status` captured (dirty workspace from prior P93-P98 tranche work)
- `git log --oneline -10` captured
- `source .venv/bin/activate` verified (`Python 3.12.13`)
- `ruff check ai/ ui/src/ tests/ docs/ 2>&1 | tail -100` captured (known pre-existing `docs/zo-tools/*` lint debt)
- `python -m pytest tests/ -q --tb=short 2>&1 | tail -160` captured twice:
  - first run from system Python path (collection error)
  - corrected venv run passes (`2188 passed, 183 skipped`)
- `cd ui && npx tsc --noEmit` pass

## Evidence Method

- Browser evidence captured from live `http://127.0.0.1:3000` with headless Chromium via Playwright.
- Per-panel screenshots captured to `docs/evidence/p99/screenshots/`.
- Structured evidence captured in:
  - `docs/evidence/p99/panel-evidence.json`
  - `docs/evidence/p99/panel-visible-text.json`
- Runtime service checks captured from host and browser contexts to separate backend health from browser reachability.

## Completion Notes

- P98 debt burn-down is closed and documented.
- P99 establishes a new truth baseline backed by direct runtime evidence and explicit debt classification.
