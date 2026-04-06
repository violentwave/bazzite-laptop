# Performance Bottleneck Analysis - Bazzite AI Layer

**Date:** 2026-04-06 (refreshed)
**Codebase:** Python-based AI enhancement layer
**Scope:** ai/, scripts/, systemd services

---

## Executive Summary

This document was refreshed on 2026-04-06 to reflect the current implementation state.
Many recommendations from the original analysis have been implemented.

**Current Implementation Status:**
- ✅ Parallel RAG table searches (ThreadPoolExecutor)
- ✅ Config mtime tracking to avoid unnecessary file reads
- ✅ Health score caching with invalidation
- ✅ In-memory rate limiter with background flush
- ✅ Performance metrics instrumentation (ai/metrics.py)
- ✅ HTTP client connection pooling (httpx.Client)
- ✅ Embedding LRU cache

**Still Open Opportunities:** See "Active Recommendations" below.

---

## Implemented Optimizations (Completed)

### 1. Parallel RAG Searches ✅
**Status:** Already existed in codebase, verified in P34

**Implementation:**
- `ai/rag/query.py` uses `ThreadPoolExecutor(max_workers=3)` for concurrent log/threat/doc searches
- Reduces latency from sum of all searches to ~max of all searches

---

### 2. Config Mtime Tracking ✅
**Status:** Implemented in P34

**Implementation:**
- `ai/router.py` tracks `_config_mtime` 
- Avoids unnecessary file reads when config hasn't changed

---

### 3. Health Score Caching ✅
**Status:** Implemented in P34

**Implementation:**
- `ai/health.py` has `_cached_score` + `_score_cache_time` on `ProviderHealth`
- `invalidate_cache()` called from `record_success()`/`record_failure()`

---

### 4. In-Memory Rate Limiter ✅
**Status:** Implemented in P34

**Implementation:**
- `ai/rate_limiter.py`: In-memory cache with background flush daemon (60s)
- Uses `threading.RLock`, `atexit` flush on shutdown

---

### 5. HTTP Connection Pooling ✅
**Status:** Implemented in P34

**Implementation:**
- `ai/router.py`: `httpx.Client` with `max_keepalive=20, max_connections=100`
- Other modules use module-level `requests.Session()` for connection reuse

---

### 6. Embedding LRU Cache ✅
**Status:** Implemented earlier

**Implementation:**
- `@lru_cache(maxsize=500)` for `embed_single`

---

### 7. Performance Metrics Module ✅
**Status:** Implemented in P24

**Implementation:**
- `ai/metrics.py` with `@track_performance` decorator
- `record_metric()` for arbitrary metric recording
- MCP tool `system.perf_metrics` (now `system.metrics_summary`)

---

## Active Recommendations (Still Open)

### 🔴 High Priority: Embedding Batch Throughput

**File:** `ai/rag/embedder.py`

**Status:** Partially addressed - `embed_texts_async()` exists with asyncio.gather

**Remaining work:** 
- Batch embedding for very large text sets could use additional batching
- Consider streaming for extremely large documents

---

### 🟡 Medium Priority: Unbounded Cache Growth

**File:** `ai/cache.py` (JsonFileCache)

**Current state:** No size limit, only TTL expiry

**Risk:** Disk exhaustion on external SSD with unbounded growth

**Recommendation:** Add LRU eviction at configurable entry limit (e.g., 50k entries)

---

### 🟡 Medium Priority: Schema Caching

**File:** `ai/rag/store.py`

**Current state:** Schema generated on each table access

**Recommendation:** Add `@lru_cache` to schema generation for frequently accessed tables

---

### 🟡 Medium Priority: Rate Limiter State Cleanup

**File:** `ai/mcp_bridge/tools.py`

**Current state:** Lists grow unbounded

**Recommendation:** Consider using `collections.deque(maxlen=...)` for call time tracking

---

## Measurement & Baseline

### Current Metrics Tools

The repo includes built-in performance measurement:

| Tool | Location | Purpose |
|------|----------|---------|
| `ai/metrics.py` | `MetricsRecorder` | Time-series metrics in LanceDB |
| `system.metrics_summary` | MCP tool | Aggregate metrics for last 24h |
| `system.perf_profile` | MCP tool | LLM, MCP, file I/O, LanceDB profiling |
| `tests/test_performance.py` | 14 regression tests | Performance regression tests |

### Running Performance Measurements

```bash
# Get metrics summary
curl http://127.0.0.1:8766/mcp -d '{"tool": "system.metrics_summary", "args": {}}'

# Run performance profiler
python -m ai.system.perf_profiler

# Run performance tests
pytest tests/test_performance.py -v
```

---

## Test Coverage

- **Performance tests:** `tests/test_performance.py` (14 tests)
- **Metrics tests:** `tests/test_metrics.py`
- **Rate limiter tests:** `tests/test_rate_limiter.py`
- **Health tests:** `tests/test_health.py`, `tests/test_health_v2.py`

---

## References

- CHANGELOG.md Phase P34: Performance Hardening
- CHANGELOG.md Phase P24: MetricsRecorder
- `docs/test-coverage-analysis.md` (refreshed 2026-04-06)
