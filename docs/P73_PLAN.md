# P73 Plan - Impact Analysis

Status: In Progress

## Objective

Implement blast-radius and weighted impact analysis in `ai/code_intel` by combining structural relationships, dependency graph traversal, and historical co-change signals.

## Scope

- Add blast-radius computation with hop depth.
- Replace hardcoded impact confidence values with weighted scoring.
- Add co-change analysis with a time window.
- Enhance test suggestion relevance with impacted-module hints.
- Expose blast-radius via a new MCP tool.

## Deliverables

1. `CodeIntelStore.query_blast_radius(changed_files, max_depth)`.
2. `CodeIntelStore.query_impact(...)` upgraded with:
   - `blast_radius`
   - `co_change_analysis`
   - weighted `impact_score` + confidence signals
3. `code.blast_radius` MCP tool in server/tools/allowlist.
4. `scripts/index-code.py --mine-history --max-commits` support.
5. New tests in:
   - `tests/test_dependency.py`
   - `tests/test_impact.py`

## Validation

```bash
ruff check ai/code_intel/ ai/mcp_bridge/ tests/
python -m pytest tests/test_code_intel.py tests/test_dependency.py tests/test_impact.py -v
python scripts/index-code.py --mine-history --max-commits 100
```
