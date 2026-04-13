# P72 Completion Report

**Phase**: P72 - Dependency Graph Expansion + Impact Analysis Alignment  
**Date**: 2026-04-13  
**Status**: Complete

## Objective

Make dependency graph tooling truly module-aware and align impact analysis with dependency data, while remaining consistent with post-P71 scope boundaries.

## Delivered

### 1) Import graph builder corrections

- Updated `ai/code_intel/parser.py`:
  - Switched `grimp` usage to valid package-based graph construction.
  - Replaced unsupported direct graph field access with method-based edge extraction.
  - Added cycle-edge detection helper and cycle output.
  - Improved AST fallback module naming to canonical dotted names under `ai.*`.

### 2) Store-level dependency graph query

- Updated `ai/code_intel/store.py`:
  - Added `query_dependency_graph(module, direction="both", max_depth=3)`.
  - Added module resolution compatibility for `ai.*` and non-prefixed legacy names.
  - Added bounded BFS traversal for depth-aware dependency/dependent queries.
  - Added structured output: `dependencies`, `dependents`, `edges`, `circular`.

### 3) Import graph storage stability

- Updated `store_import_graph(...)`:
  - Added replace behavior (default on) to prevent stale/duplicate edge accumulation.
  - Preserved edge metadata and circular flags from builder output.

### 4) Impact analysis alignment

- Updated `query_impact(...)`:
  - Added dependency-graph-based affected module expansion.
  - Added optional test suggestions (`include_tests` support).
  - Added richer confidence signals (`dependency_graph`, `test_coverage`).

### 5) MCP handler alignment

- Updated `ai/mcp_bridge/tools.py`:
  - `code.impact_analysis` now forwards `include_tests` and `max_depth`.
  - `code.dependency_graph` now uses `query_dependency_graph(...)`.
- Updated `ai/mcp_bridge/server.py`:
  - Dependency handler now honors `direction` and `max_depth`.
  - Impact handler now honors `include_tests` and `max_depth`.
- Updated `configs/mcp-bridge-allowlist.yaml`:
  - Added `max_depth` arg to `code.dependency_graph`.

### 6) Test expansion

- Updated `tests/test_code_intel.py`:
  - Added dependency graph direction/depth coverage.
  - Added cycle edge/circular output coverage.
  - Added impact analysis integration test for dependency and test suggestions.

## Validation

- `ruff check ai/ tests/ scripts/` ✅ passed
- `python -m pytest tests/test_code_intel.py -q --tb=short` ✅ 29 passed
- `python -m pytest tests/test_mcp_drift.py -q --tb=short` ✅ 4 passed
- `python -m pytest tests/ -x -q --tb=short` ⚠️ environment failure: missing `hypothesis` (`ModuleNotFoundError`) in `tests/test_properties.py`
- `python scripts/index-code.py --incremental` ⚠️ executed but embedding providers failed in this environment (Gemini key invalid, Cohere trial/rate limits)

## P73 Boundary Check

- No in-repo `P73` plan artifact exists to conflict with.
- P72 implementation remains within dependency graph + impact hardening and does not include rename refactor or multi-language expansion.
