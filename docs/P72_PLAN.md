# P72 Plan - Dependency Graph Expansion + Impact Analysis Alignment

Status: In Progress

## Objective

Deliver real module-level dependency graph results and align impact analysis to use those dependency edges, closing the known gap left intentionally out of P71.

## Scope

- Replace fallback dependency behavior with store-backed import graph traversal.
- Honor `direction` and `max_depth` in dependency queries.
- Include circular dependency reporting.
- Improve impact analysis with dependency-graph signals and optional test suggestions.
- Keep scope clear of speculative P73 work (no rename refactoring, no multi-language expansion).

## P73 Non-Contradiction Check

- No dedicated `P73` phase artifact exists in the repo.
- Existing roadmap notes after P68 only identify dependency and impact increments as upcoming structural work.
- P72 therefore combines dependency + impact hardening without overlapping a documented P73 contract.

## Deliverables

1. `ImportGraphBuilder` updated to use valid `grimp` APIs, with AST fallback preserved.
2. `CodeIntelStore.query_dependency_graph(module, direction, max_depth)` added.
3. `code.dependency_graph` handlers switched to real dependency graph output.
4. `store_import_graph()` made replace-safe to avoid edge duplication across re-indexes.
5. `query_impact(...)` updated to use dependency graph and optional test suggestions.
6. New tests for dependency direction/depth/cycles and impact integration.
7. MCP allowlist updated to include `max_depth` for dependency graph.

## Validation

```bash
ruff check ai/ tests/ scripts/
python -m pytest tests/test_code_intel.py -q --tb=short
python -m pytest tests/test_mcp_drift.py -q --tb=short
python -m pytest tests/ -x -q --tb=short
python scripts/index-code.py --incremental
```
