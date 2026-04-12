# P71 Plan - Structural Analysis Enhancement

Status: In Progress

## Objective

Make the existing `ai/code_intel` stack production-functional by fixing missing store methods, improving AST relationship extraction, and wiring incremental indexing for practical updates.

## Scope

- Extend `CodeParser` to capture broader call shapes and inheritance edges.
- Implement missing `CodeIntelStore` APIs used by MCP handlers.
- Add incremental index workflow in `scripts/index-code.py`.
- Replace MCP fallback behavior with real store-backed implementations for all 6 code-intel tools.
- Expand structural-analysis test coverage.

## Deliverables

1. `ast.Attribute` call extraction (including `self.method()`, `module.func()`, `obj.method()`).
2. Populated `inherits` relationships from class bases.
3. Missing `CodeIntelStore` methods implemented:
   - `find_callers`
   - `suggest_tests`
   - `get_complexity_report`
   - `get_class_hierarchy`
4. Incremental indexing flags in `scripts/index-code.py`:
   - `--incremental`
   - `--force`
   - `--file`
5. MCP code-intel tool paths backed by real store methods.
6. Expanded tests in `tests/test_code_intel.py` and drift verification.

## Validation

```bash
ruff check ai/code_intel/ tests/test_code_intel.py
python -m pytest tests/test_code_intel.py -v
python -m pytest tests/test_mcp_drift.py -q --tb=short
python scripts/index-code.py --incremental
```
