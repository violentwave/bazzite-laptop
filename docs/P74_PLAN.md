# P74 Plan - Code Intelligence Fusion Layer

Status: In Progress

## Objective

Bridge structural code intelligence, semantic code RAG, task patterns, and phase artifacts into one retrieval path without creating a parallel platform.

## Scope

- Keep existing stores (`code_files`, `code_nodes`, `relationships`, learning stores) intact.
- Add a deterministic mapping layer between semantic chunks and structural nodes.
- Expose fused retrieval via MCP/tooling surfaces.
- Document canonical linking strategy and outputs.

## Canonical Link Strategy

Primary join path:
1. Normalize file path (`code_files.relative_path` ↔ `code_nodes.file_path`).
2. Rank node candidates by line-range overlap.
3. Use symbol-name fallback when overlap is weak.
4. Emit deterministic `stable_id` (`sha256(path|symbol|line_start|line_end)[:16]`) for cross-reference.

## Deliverables

1. Mapping-layer APIs in `ai/code_intel/store.py`:
   - `map_code_chunk_to_nodes(...)`
   - `get_node_relationship_neighbors(...)`
2. Fused retrieval in `ai/rag/code_query.py`:
   - `code_fused_context(question, limit=5)`
3. MCP exposure:
   - new tool `code.fused_context` in allowlist + dispatch
4. Validation and test coverage:
   - add `tests/test_code_fusion.py`
   - keep P71-P73 suites green
5. Docs and phase artifacts updated per P70 policy.

## Validation

```bash
ruff check ai/code_intel/ ai/rag/ ai/mcp_bridge/ tests/
python -m pytest tests/test_code_intel.py tests/test_dependency.py tests/test_impact.py tests/test_code_fusion.py -v
rg -n "code_files|code_nodes|relationships|fusion|cross-reference|artifact" ai docs
```
