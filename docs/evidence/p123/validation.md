# P123 Validation Evidence

Date: 2026-04-17

## Command Results

1) Targeted P123 tests

```bash
.venv/bin/python -m pytest tests/test_agent_workbench.py -q
```

Result:
- `13 passed in 2.11s`

2) Targeted lint

```bash
ruff check ai/agent_workbench tests/test_agent_workbench.py
```

Result:
- `All checks passed!`

3) Allowlist YAML parse

```bash
.venv/bin/python -c "from pathlib import Path; import yaml; yaml.safe_load(Path('configs/mcp-bridge-allowlist.yaml').read_text()); print('allowlist yaml parse ok')"
```

Result:
- `allowlist yaml parse ok`

4) Full regression suite

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
```

Result:
- `2443 passed, 183 skipped, 1724 warnings in 294.90s (0:04:54)`

## Scope-Specific Notes

- Full suite completed successfully in this run.
- Warnings are pre-existing deprecation/runtime warnings outside P123 scope.
- No failures or xfails were introduced by P123.
