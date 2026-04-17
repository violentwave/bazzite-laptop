# Cleanup Validation — Newelle/PySide Runtime Surface Removal

Date: 2026-04-17
Scope: Deprecated Newelle fallback wrappers and PySide tray launch surface cleanup

## Preflight

- Branch: `master`
- Git status before edits: clean

## Commands Run

```bash
ruff check ai/ tests/ scripts/
.venv/bin/python -m pytest tests/ -x -q --tb=short
```

## Results

- `ruff check ai/ tests/ scripts/`: PASS
- `pytest tests/ -x -q --tb=short`: PASS
  - 2469 passed
  - 183 skipped
  - 0 failed

## Runtime Surface Changes Verified

- Removed scripts:
  - `scripts/newelle-exec.sh`
  - `scripts/newelle-sudo.sh`
  - `scripts/start-security-tray-qt.sh`
  - `scripts/validate_newelle_skills.py`
- Removed tests coupled to deprecated surfaces:
  - `tests/test_newelle_scripts.py`
  - `tests/test_validate_skills.py`
  - `tests/test_dashboard_keys_tab.py`
  - `tests/test_tray_state_machine.py`
- Removed PySide fixture setup from `tests/conftest.py`

## Documentation Reconciliation

- Updated active guidance to console/workflow-first:
  - `docs/USER-GUIDE.md`
  - `README.md`
- Marked legacy docs as historical where applicable:
  - `docs/newelle-system-prompt.md`
  - `docs/P87_MIGRATION_CUTOVER.md`
  - `docs/P88_UI_HARDENING_LAUNCH_HANDOFF.md`
- Recorded cleanup in:
  - `CHANGELOG.md`
  - `HANDOFF.md`

## Notes

- Notion query attempts timed out during this cleanup run; no phase status mutations were performed from this session.
