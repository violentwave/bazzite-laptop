# Project Memory — Bazzite AI Layer

> Last updated: 2026-04-03 | Session: claude-code

---

## 1. Past Work Summary

### Confirmed Architecture Decisions

| Component | Decision | Location |
|-----------|----------|----------|
| LLM Routing | LiteLLM with 6-provider chain (Groq, Gemini, Mistral, Cerebras, OpenRouter, ZAI) | `configs/litellm-config.yaml` |
| Vector Store | LanceDB at `~/security/vector-db/` | `ai/rag/store.py` |
| MCP Bridge | FastMCP 3.x at `127.0.0.1:8766`, 45 tools | `ai/mcp_bridge/server.py` |
| Embedding | Ollama (nomic-embed-text) primary + Gemini fallback, 768-dim | `ai/rag/embedder.py` |
| Document Ingestion | `ai/rag/ingest_docs.py` with state tracking | `docs/USER-GUIDE.md` |
| Log Ingestion | `ai/log_intel/ingest.py` (health, scans, freshclam) | `docs/USER-GUIDE.md` |

### Confirmed Bottlenecks (All Fixed This Session)

1. **Unhashable type error** — `TypeError: unhashable type: 'list'`
   - Root cause: `db.list_tables()` returns named tuple in LanceDB 0.30+, not list
   - Fixed in: `ai/rag/store.py:119-127`, `ai/agents/knowledge_storage.py:267-277`

2. **Table race condition** — `ValueError: Table 'X' already exists`
   - Root cause: No error handling when LanceDB table creation conflicts
   - Fixed in: `ai/rag/store.py:119-127`, `ai/log_intel/ingest.py:529-537`

3. **Vector type mismatch** — numpy arrays vs lists in validation
   - Root cause: LanceDB returns numpy arrays in pandas DataFrames
   - Fixed in: `ai/agents/knowledge_storage.py:204-238`

### Testing Gaps

- No simulation of table "already exists" race condition in tests

### Confirmed Work

- Corruption injection tests — `test_lancedb_auto_repair` validates auto-repair
- Backup retention pruning — `test_prune_keeps_only_3_recent` verifies 3-backup limit

### Active Constraints (Hard Stops)

Per `CLAUDE.md`:
- No `/usr/`, `/boot/`, `/ostree/` writes
- No `rpm-ostree` upgrade/rebase
- No `keys.env` value reads (names only)
- No swappiness changes
- No PRIME offload env vars

### Active Priorities

1. **Auto-repair with 3-rolling-backup** — Implemented in `ai/agents/knowledge_storage.py`
2. **Systemd path corrections** — Fixed `.venv/bin/python` → `/usr/bin/python3`
3. **E2E RAG verification** — Added `tests/test_rag_e2e.py`

---

## 2. Database Pipeline Current State

### Data Sources → Ingest Flow

| Source | Location | Tool | State File |
|--------|-----------|------|------------|
| Health logs | `/var/log/system-health/health-*.log` | `security.run_ingest` | `.ingest-state.json` |
| Scan logs | `/var/log/clamav-scans/scan-*.log` | `security.run_ingest` | `.ingest-state.json` |
| Freshclam | `/var/log/clamav-scans/freshclam.log` | `security.run_ingest` | `.ingest-state.json` |
| Documents | `docs/*.md` | `knowledge.ingest_docs` | `.doc-ingest-state.json` |
| Code | repo source files | `knowledge.ingest_code` | `.code-ingest-state.json` |

### Embedding Flow

```
Text input → chunk_markdown/chunk_scan_log/chunk_code → 
embed_texts() → [768-dim vector: Gemini Embedding 001 primary, 
                 Cohere rerank + fallback, Ollama emergency fallback only] →
VectorStore.add_doc_chunks/add_log_chunks/add_code_chunks() → LanceDB
```

**Note:** `ai/rag/embedder.py` implements provider chain: Gemini → Cohere → Ollama (emergency only).

### Vector Store / Retrieval Path

```
Query → embed_single(768-dim) → 
VectorStore.search_logs/search_threats/search_docs() →
merge + rank by _distance → _build_context() → 
rag_query() returns QueryResult (answer, context_chunks, sources)
```

**Query modes:**
- `knowledge.rag_query` — returns raw context chunks (no LLM synthesis)
- `knowledge.rag_qa` — returns LLM-synthesized answer via router

### Tables in LanceDB

| Table | Content | Row Count (current) |
|-------|---------|---------------------|
| `docs` | Chunked markdown documents | 6 |
| `health_records` | Health snapshot summaries | 52 |
| `scan_records` | ClamAV scan summaries | 16 |
| `security_logs` | Raw log chunks for RAG | 35 |
| `threat_intel` | Threat report data | 0 |

**Total: 109 rows** (as of 2026-04-03)

### Storage Locations

- **Vector DB**: `~/security/vector-db/` → symlinked to `/var/mnt/ext-ssd/bazzite-ai/vector-db` (external SSD)
- **State files**: `~/security/vector-db/.doc-ingest-state.json`, `.ingest-state.json`, `.code-ingest-state.json`
- **Storage reports**: `~/security/storage-reports/storage-YYYY-MM-DD-HHMM.json`
- **Backups**: `~/security/vector-db-backup-YYYYMMDD-HHMMSS/` (on external SSD at `/var/mnt/ext-ssd/bazzite-ai/`, keeps last 3)

### Known Failure Points (All Fixed)

1. **Embedding provider unavailable** — `ai/log_intel/ingest.py:608,700` now logs specific error, returns 0 instead of silent fail
2. **Missing state files** — `_read_ingest_state()` now falls back to file mtime for doc state
3. **Permission denied in systemd** — Services now use `/usr/bin/python3`

---

## 3. Next Session Starting Point

### Useful Follow-up Actions

1. **Test repair with corruption injection**
   - Manually corrupt a LanceDB table (add NaN vector)
   - Run `repair_database()` and verify recovery
   
2. **Add corruption simulation to test suite**
   - Create test case that injects malformed vectors
   - Verify `_detect_corruption()` catches it

3. **Verify backup pruning**
   - Create 4+ backups
   - Run `_prune_old_backups()`
   - Confirm only 3 remain

### Files to Read First

| File | Why |
|------|-----|
| `ai/agents/knowledge_storage.py` | Auto-repair logic, backup handling |
| `ai/rag/store.py` | Vector validation, table management |
| `tests/test_rag_e2e.py` | E2E pipeline verification |

---

## 4. Current Session Status

- **Storage check**: `healthy` (status)
- **Total vector rows**: 109 across 5 tables
- **Last ingest**: docs ~0 hours ago, logs ~0.8 hours ago

### Changes This Session

- Fixed LanceDB unhashable type error (vector validation)
- Fixed table race condition ("already exists" handling)
- Fixed systemd Python paths (`.venv/bin/python` → `/usr/bin/python3`)
- Added health check with corruption detection and auto-repair
- Added 3-rolling-backup retention with auto-pruning
- Added E2E test for RAG pipeline (ZRAM doc → embed → query)
- Added `test_lancedb_auto_repair` test validating corruption detection and repair
- Added `test_prune_keeps_only_3_recent` test validating backup pruning
- Updated USER-GUIDE.md with LanceDB health documentation
- Updated CHANGELOG.md with Database Integrity Test Suite entry
- Closed Testing Gaps: moved corruption injection tests and backup retention to Confirmed Work

### Blockers / Uncertainties

- None currently — pipeline healthy, storage check passes

### Recommended Next Actions

1. Verify morning briefing shows "healthy" status
2. Test repair with actual corruption (if it occurs)
3. Review new tests coverage

---

## Next Handoff

### Current Status
- Storage check: **healthy**
- Vector DB: 109 rows across 5 tables
- Git: on `master`, commit `639b0aa` pushed

### What Changed in This Run
- Fixed LanceDB `TypeError: unhashable type: 'list'` in `ai/rag/store.py` (vector validation) and `ai/agents/knowledge_storage.py` (numpy array handling)
- Fixed table creation race condition in both store.py and ingest.py
- Fixed systemd services to use `/usr/bin/python3` instead of `.venv/bin/python`
- Added comprehensive health check with `_detect_corruption()`, `_validate_table_vectors()`, `repair_database()`, `_prune_old_backups()`
- Created `tests/test_rag_e2e.py` verifying full RAG pipeline: ZRAM doc → ingest → query → Ollama embeddings
- Added `test_lancedb_auto_repair` test validating corruption detection and repair
- Added `test_prune_keeps_only_3_recent` test validating backup pruning logic
- Documented LanceDB health check in `docs/USER-GUIDE.md`
- Updated `docs/CHANGELOG.md` with Database Integrity Test Suite entry
- Closed Testing Gaps: moved corruption injection tests and backup retention to Confirmed Work in `project_memory.md`

### Blockers / Uncertainties
- None — all fixes verified, storage check passes

### Recommended Next 3 Actions
1. Verify morning briefing shows "healthy" status
2. Monitor backup pruning during actual operation
3. Test repair functionality if real corruption occurs

### Files Most Worth Reading First Next Session
- `ai/agents/knowledge_storage.py` (lines 240-420: repair logic)
- `ai/rag/store.py` (lines 97-140: connection + table management)
- `tests/test_rag_e2e.py` (full: E2E pipeline reference)

---

*Per AGENT.md: Read HANDOFF.md at session start, run save-handoff.sh at session end.*