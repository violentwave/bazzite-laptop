# P68 — GitNexus Code-Graph Augmentation Pilot Plan

**Phase:** P68  
**Status:** In Progress  
**Dependencies:** P60, P65, P66, P67  
**Risk Tier:** High  

---

## Executive Summary

GitNexus is a zero-server code intelligence engine that creates knowledge graphs from repositories (dependencies, call chains, execution flows). This document evaluates whether GitNexus would augment or duplicate existing Bazzite code intelligence capabilities.

**Recommendation:** Defer GitNexus integration. Implement targeted enhancements to existing `code_query.py` and `pattern_query.py` instead, adding the specific missing capabilities (call graph, dependency analysis) without the complexity and licensing concerns of a new tool.

---

## 1. Current Bazzite Code Intelligence Capabilities

### 1.1 Code RAG (`ai/rag/code_query.py` + `ai/rag/ingest_code.py`)

- **What it does:** Semantic search over Python code chunks
- **How it works:**
  - Ingests `.py` files on function/class boundaries
  - Embeds each symbol chunk using the configured embedding provider
  - Stores in LanceDB `code_files` table
  - Supports natural language queries with optional LLM synthesis
- **Strengths:**
  - Already integrated with Bazzite embedding providers
  - Already exposed via MCP tools (`code.rag_query`, `code.search`)
  - Uses existing rate limiting and fallback chain
  - Handles large files with word truncation
  - Mtime-based incremental updates
- **Limitations:**
  - No structural analysis (call graphs, dependencies)
  - No change impact analysis
  - Language-specific (Python only)
  - No rename refactoring across files
  - Returns chunks, not relationship graphs

### 1.2 Pattern Store (`ai/rag/pattern_store.py` + `ai/rag/pattern_query.py`)

- **What it does:** Curated pattern corpus for code generation workflows
- **How it works:**
  - Stores curated patterns with semantic metadata
  - Filters by language, domain, archetype, scope, role
  - Hybrid search (semantic vector + metadata filters)
- **Strengths:**
  - Domain-specific (frontend patterns, workflow patterns)
  - High-quality curated content
  - Extensible schema
- **Limitations:**
  - Curated only, not auto-extracted from codebase
  - No automatic learning from successful code

### 1.3 Agent Knowledge Store (`ai/collab/knowledge_base.py`)

- **What it does:** Agent-scoped knowledge for coordination
- **Strengths:**
  - Integrated with agent bus
  - Supports task patterns and session history

---

## 2. GitNexus Capabilities

### 2.1 Core Features

GitNexus provides:

| Feature | Description |
|---------|-------------|
| **Code Graph** | AST-based knowledge graph: imports, calls, inheritance |
| **Impact Analysis** | Blast radius of changes (rename, delete, refactor) |
| **Context Extraction** | 360° symbol context (callers, callees, tests, deps) |
| **Hybrid Search** | Semantic + structural search |
| **Change Detection** | Smart change detection (minimal re-indexing) |
| **Rename Support** | Safe rename refactoring across files |
| **MCP Integration** | 7+ MCP tools: `impact`, `context`, `query`, `detect_changes`, `rename` |

### 2.2 Technical Profile

- **Runtime:** Browser WASM or CLI (zero server)
- **Languages:** Multi-language support (Python, JS/TS, Go, Rust, etc.)
- **License:** PolyForm Noncommercial (limits enterprise adoption)
- **Deployment:** Local-first, optional cloud sync

### 2.3 GitNexus MCP Tools

1. `gitnexus_impact` — Blast radius of changes
2. `gitnexus_context` — Full symbol context
3. `gitnexus_query` — Hybrid search
4. `gitnexus_detect_changes` — Smart change detection
5. `gitnexus_rename` — Safe refactoring
6. `gitnexus_graph` — Dependency/call graph
7. `gitnexus_summary` — Codebase overview

---

## 3. Gap Analysis

### 3.1 What GitNexus Would Add

| Capability | Current | With GitNexus |
|------------|---------|---------------|
| Call graph | ❌ None | ✅ Full call chains |
| Dependency analysis | ❌ None | ✅ Import/dep graph |
| Change impact | ❌ None | ✅ Blast radius |
| Rename refactoring | ❌ None | ✅ Safe rename |
| Multi-language | ❌ Python only | ✅ Python + others |
| Structural search | ❌ None | ✅ AST-based |

### 3.2 What Would Be Duplicated

| Capability | Existing | GitNexus |
|------------|----------|----------|
| Semantic search | ✅ code_query | ✅ gitnexus_query |
| Vector embeddings | ✅ LanceDB | ✅ WASM embed |
| Pattern retrieval | ✅ pattern_query | ✅ pattern matching |
| Code context | ✅ code_rag | ✅ gitnexus_context |

### 3.3 Unique Value

GitNexus' unique value is **structural analysis** — call graphs, dependency graphs, and change impact analysis. These are NOT currently in Bazzite.

---

## 4. Integration Options

### Option A: Full Replacement (Not Recommended)
- Replace `code_query.py` with GitNexus
- **Pros:** Single code intelligence system
- **Cons:** 
  - Lose Bazzite-optimized embedding pipeline
  - Lose rate limiting/fallback chain
  - Lose MCP bridge integration
  - Licensing concerns for enterprise users

### Option B: Parallel Addition (Possible)
- Add GitNexus as optional layer alongside `code_query.py`
- **Pros:**
  - Keep existing capabilities
  - Add structural analysis
  - Optional for users
- **Cons:**
  - Maintenance burden of two systems
  - Potential confusion about which to use
  - Duplication of semantic search

### Option C: Targeted Enhancement (Recommended)
- Enhance `code_query.py` + `pattern_query.py` with structural analysis
- Use AST parsing to extract call graphs and dependencies
- Keep single integrated system
- **Pros:**
  - No new dependency
  - No licensing issues
  - Single codebase to maintain
  - Uses existing embedding infrastructure
- **Cons:**
  - Development effort required
  - Multi-language support would need separate implementation

---

## 5. Benchmark Criteria

If implementing GitNexus (or any structural analysis), measure:

| Metric | Target | Measured |
|--------|--------|----------|
| Query latency | < 200ms | — |
| Index time (this repo) | < 30s | — |
| Memory footprint | < 500MB | — |
| Impact analysis accuracy | > 90% | — |
| Rename safety | 100% (no missed refs) | — |

### 5.1 Comparison Tests

1. **Semantic search accuracy:**
   - Current `code_rag_query` vs GitNexus `gitnexus_query`
   - Measure relevance of top 5 results for 20 test queries

2. **Impact analysis:**
   - GitNexus `gitnexus_impact` vs manual grep
   - Measure false positives/negatives

3. **Context extraction:**
   - GitNexus `gitnexus_context` vs current code RAG + manual file reading
   - Measure completeness of symbol context

---

## 6. Repo-Scale and Agent-Context Tradeoffs

### 6.1 Scale Considerations

| Factor | Bazzite `code_query` | GitNexus |
|--------|---------------------|----------|
| Repo size | Works for any size | Works for any size |
| Incremental updates | ✅ Mtime-based | ✅ Change detection |
| Cross-repo | ❌ Single repo | ✅ Multi-repo support |
| Embedding cost | Uses Bazzite providers | WASM local |

### 6.2 Agent Context Tradeoffs

| Factor | Bazzite | GitNexus |
|--------|---------|----------|
| MCP integration | ✅ Native | ✅ Available |
| RuFlo coordination | ✅ Integrated | ⚠️ Would need adapter |
| Pattern store sync | ✅ Integrated | ⚠️ Would need sync |
| Rate limiting | ✅ Integrated | ❌ Need new impl |

---

## 7. Recommendation

### Defer GitNexus Integration

**Rationale:**

1. **Duplication of existing capabilities:** GitNexus duplicates semantic search which Bazzite already has via LanceDB + embedding providers.

2. **Unique value is limited:** The only truly unique value is structural analysis (call graphs, dependency graphs). This can be added to existing `code_query.py` without GitNexus.

3. **Licensing concerns:** PolyForm Noncommercial license limits enterprise adoption of Bazzite.

4. **Maintenance burden:** Operating two code intelligence systems would increase complexity.

5. **Integration work:** Would need MCP bridge adapter, rate limiting, fallback chain.

### Alternative: Enhance Existing Code Intelligence

Instead of GitNexus, enhance Bazzite's existing code intelligence:

1. **Add structural analysis to `ingest_code.py`:**
   - Use Python AST to extract call graphs
   - Extract import dependencies
   - Store in LanceDB alongside code chunks

2. **Add impact analysis tool:**
   - `code.impact` MCP tool
   - Given a symbol, find all callers
   - Given a file, find all dependents

3. **Add dependency graph tool:**
   - `code.deps` MCP tool
   - Show import hierarchy
   - Identify circular dependencies

4. **Multi-language support (future):**
   - TypeScript ingest (for frontend patterns)
   - Rust ingest (for RuFlo core)

---

## 8. Implementation Plan (If Deferred)

If this recommendation is accepted:

### Phase 1: Structural Analysis Enhancement (P69)
- Augment `ai/rag/ingest_code.py` to extract call graphs
- Store call graph edges in LanceDB
- Add `code.callers` and `code.callees` MCP tools

### Phase 2: Dependency Analysis (P70)
- Extract import dependencies
- Add `code.deps` MCP tool
- Add circular dependency detection

### Phase 3: Impact Analysis (P71)
- Add `code.impact` MCP tool
- Integrate with diff analysis
- Support rename suggestion

**Estimated effort:** 2-3 phases, similar to P61-P63 scope.

---

## 9. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-12 | Defer GitNexus | See Section 7 recommendations |
| — | — | — |

---

## 10. References

- GitNexus: https://github.com/contextlab/gitnexus
- CodeGraphContext (MIT alternative): https://github.com/context-labs/codegraphcontext
- Bazzite code_query.py: `ai/rag/code_query.py`
- Bazzite pattern_query.py: `ai/rag/pattern_query.py`
- LanceDB: https://lancedb.github.io/lancedb/

---

## 11. Done Criteria

From Notion:

- [x] GitNexus pilot plan implemented or documented — This document
- [x] Benchmark criteria defined — Section 5
- [x] Optional integration path documented — Section 4, Option B
- [x] Repo-scale and agent-context tradeoffs recorded — Section 6
- [x] Recommendation made — Section 7 (Defer)
- [ ] Docs and handoff updated — Next step

---

**Next Steps:**

1. Update HANDOFF.md with P68 completion
2. Mark P68 as Done in Notion
3. Optionally: Create P69, P70, P71 phase proposals for structural analysis enhancements