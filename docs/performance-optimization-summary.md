# Performance Optimization Summary - Actionable Recommendations

**Analysis Date:** 2026-04-02  
**Analyst:** Claude (Sonnet 4.5)  
**Codebase:** Bazzite AI Layer (Python)

---

## Quick Wins (High Impact, Low Effort)

### 1. Enable Rate Limiter In-Memory Cache ✅ P0
**File:** `ai/rate_limiter.py`  
**Impact:** 95% reduction in file I/O, 0.5ms → 0.01ms per check  
**Effort:** 30 minutes

```python
class RateLimiter:
    def __init__(self, ...):
        self._cache: dict | None = None
        self._cache_time: float = 0
        self._cache_ttl: float = 5.0  # 5-second TTL
    
    def _read_state(self) -> dict:
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache
        
        # Read from disk only if cache expired
        with open(self.state_path) as f:
            self._cache = json.load(f)
        self._cache_time = now
        return self._cache
```

**Why:** High-frequency `can_call()` checks (300+/min) re-read JSON file every time.

---

### 2. Add Embedding Cache Layer ✅ P0
**File:** `ai/router.py`  
**Impact:** 60-80% cache hit rate, $3/month → $0.60/month cost savings  
**Effort:** 45 minutes

```python
_embedding_cache: dict[str, tuple[list[float], float]] = {}

def _try_embed(task_type: str, prompt: str, **kwargs) -> str:
    cache_key = hashlib.sha256(prompt.encode()).hexdigest()
    now = time.time()
    
    # Check 24-hour cache
    if cache_key in _embedding_cache:
        vector, cached_at = _embedding_cache[cache_key]
        if now - cached_at < 86400:
            return json.dumps(vector)
    
    # Cache miss - call API
    response = router.embedding(model="embed", input=[prompt], **kwargs)
    vector = response["data"][0]["embedding"]
    
    # LRU eviction at 10K entries
    if len(_embedding_cache) >= 10_000:
        oldest = min(_embedding_cache, key=lambda k: _embedding_cache[k][1])
        del _embedding_cache[oldest]
    
    _embedding_cache[cache_key] = (vector, now)
    return json.dumps(vector)
```

**Why:** Same error messages/log patterns embedded repeatedly (50+ times/day).

---

### 3. Replace Tray Polling with inotify ✅ P0
**File:** `tray/security_tray_qt.py`  
**Impact:** 99% I/O reduction (28,800 → 50-200 reads/day)  
**Effort:** 1 hour

```python
import select
import os

class FileWatcher:
    def __init__(self, path: Path):
        self.fd = os.inotify_init()
        self.wd = os.inotify_add_watch(
            self.fd, str(path),
            os.IN_MODIFY | os.IN_CLOSE_WRITE
        )
    
    def wait_for_change(self, timeout_ms: int) -> bool:
        r, _, _ = select.select([self.fd], [], [], timeout_ms / 1000)
        if r:
            os.read(self.fd, 1024)  # Consume event
            return True
        return False

# In SecurityTrayQt:
self._watcher = FileWatcher(STATUS_FILE)

def _poll_status(self):
    if not self._watcher.wait_for_change(3000):
        return  # No changes, skip read
    # File changed - read and process
    raw = STATUS_FILE.read_bytes()
    # ...
```

**Why:** Polling reads file every 3 seconds (99% detect no changes).

---

## Medium-Impact Optimizations

### 4. Parallel Threat Intel Lookups ⚡ P1
**File:** `ai/threat_intel/lookup.py`  
**Impact:** 15s → 2-5s (70% latency reduction)  
**Effort:** 2 hours (requires async refactor)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def lookup_hash_parallel(sha256: str, rate_limiter: RateLimiter):
    """Query all providers concurrently."""
    
    async def _try_provider(fn):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, fn, sha256, rate_limiter)
    
    providers = [_lookup_malwarebazaar, _lookup_otx, _lookup_virustotal]
    
    # Launch all, return first valid result
    for coro in asyncio.as_completed([_try_provider(fn) for fn in providers]):
        result = await coro
        if result and result.has_data:
            return result
    
    return ThreatReport(hash=sha256, source="none", ...)
```

**Trade-off:** More API calls (all 3 providers queried concurrently) vs faster results. Best for interactive queries.

---

### 5. Bound Long-Running Stats Trackers 🎯 P1
**File:** `ai/router.py`  
**Impact:** Fixes memory leak in 24/7 daemons  
**Effort:** 1.5 hours

```python
from collections import deque
from datetime import UTC, datetime, timedelta

class BoundedStatsTracker:
    def __init__(self, max_hours: int = 24):
        self._hourly_snapshots = deque(maxlen=max_hours)
        self._current_hour = {"tokens": 0, "cost": 0.0, "by_provider": {}}
        self._hour_start = datetime.now(UTC)
    
    def record_usage(self, provider: str, tokens: int, cost: float):
        now = datetime.now(UTC)
        
        # Rotate to new hour if needed
        if now - self._hour_start > timedelta(hours=1):
            self._hourly_snapshots.append((self._hour_start, self._current_hour.copy()))
            self._current_hour = {"tokens": 0, "cost": 0.0, "by_provider": {}}
            self._hour_start = now
        
        self._current_hour["tokens"] += tokens
        self._current_hour["cost"] += cost
    
    def get_stats(self, last_hours: int = 24):
        # Aggregate from ring buffer
        return {"total_tokens": sum(...), ...}
```

**Why:** `_cost_stats["by_provider"]` grows unbounded as new providers are tried.

---

### 6. Memoize Hash Calculations 🔧 P2
**File:** `ai/cache.py`  
**Impact:** 50% fewer hash calculations, 0.5ms → 0.25ms per cache op  
**Effort:** 30 minutes

```python
class JsonFileCache:
    def __init__(self, ...):
        self._hash_cache: dict[str, str] = {}
    
    def _key_hash(self, key: str) -> str:
        if key in self._hash_cache:
            return self._hash_cache[key]
        
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # LRU eviction at 1000 entries
        if len(self._hash_cache) >= 1000:
            self._hash_cache.pop(next(iter(self._hash_cache)))
        
        self._hash_cache[key] = key_hash
        return key_hash
```

**Why:** Same cache keys hashed multiple times (set then get = 2x hash).

---

## Anti-Patterns Identified

### ❌ Pattern: Nested File I/O in Loops
**Files:** Multiple (ingest scripts, analyzers)

```python
# BAD: File read inside loop
for file_path in file_list:
    for chunk in process_file(file_path):
        # Multiple file operations per chunk
        store.add([chunk])  # 1 write per chunk
```

```python
# GOOD: Batch file operations
chunks = []
for file_path in file_list:
    chunks.extend(process_file(file_path))
    if len(chunks) >= 100:  # Batch at 100 chunks
        store.add(chunks)
        chunks.clear()
if chunks:
    store.add(chunks)  # Final batch
```

---

### ❌ Pattern: Synchronous I/O in Async Context
**File:** `ai/llm_proxy.py` (MCP bridge)

```python
# BAD: Blocking file I/O in async function
async def handle_request(request):
    config = json.loads(Path("config.json").read_text())  # Blocks event loop
    result = await process(config)
    return result
```

```python
# GOOD: Use aiofiles for async I/O
import aiofiles

async def handle_request(request):
    async with aiofiles.open("config.json") as f:
        config = json.loads(await f.read())
    result = await process(config)
    return result
```

---

### ❌ Pattern: Missing Connection Pooling
**File:** `ai/rag/store.py` (LanceDB connections)

```python
# BAD: New connection per operation
def add_chunks(chunks):
    db = lancedb.connect(str(DB_PATH))  # New connection
    table = db.open_table("logs")
    table.add(chunks)
```

```python
# GOOD: Singleton connection with lazy init
class VectorStore:
    def __init__(self):
        self._db = None
    
    def _connect(self):
        if self._db is None:
            self._db = lancedb.connect(str(DB_PATH))
        return self._db
```

*(Already implemented in current code - good!)*

---

## Performance Testing Strategy

### Benchmark Suite
```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run baseline
pytest tests/test_performance_tuning.py --benchmark-only --benchmark-save=baseline

# After optimizations
pytest tests/test_performance_tuning.py --benchmark-only --benchmark-compare=baseline
```

### Load Test Example
```python
# tests/test_load.py
import time
from ai.threat_intel.lookup import lookup_hashes

def test_threat_intel_throughput():
    """Verify batch lookup performance."""
    hashes = ["abc..."*64 for _ in range(100)]
    
    start = time.time()
    results = lookup_hashes(hashes, full=False)
    elapsed = time.time() - start
    
    # Target: <120s for 100 hashes (was 300s sequential)
    assert elapsed < 120
    assert len(results) == 100
```

---

## Monitoring Metrics Post-Deployment

### 1. LLM Router Stats
```python
# /mcp/stats endpoint
{
  "cache_hit_rate": 0.78,  # Target: 60-80%
  "avg_latency_ms": 450,   # Target: <500ms (was 800ms)
  "embedding_cache_size": 5400
}
```

### 2. Rate Limiter I/O
```bash
# Count file reads via strace
strace -e openat -p $(pgrep -f llm-proxy) 2>&1 | grep -c rate-limits-state.json

# Target: <12 reads/min (was 300/min)
```

### 3. Memory Growth Check
```python
import resource

def log_memory_usage():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_mb = usage.ru_maxrss / 1024  # KB to MB on Linux
    print(f"Memory: {rss_mb:.1f} MB")

# Monitor daemons for 24 hours - memory should plateau, not grow
```

---

## Implementation Checklist

- [ ] **P0 Quick Wins** (Day 1-2):
  - [ ] Rate limiter cache (30 min)
  - [ ] Embedding cache (45 min)
  - [ ] inotify file watcher (1 hr)

- [ ] **P1 Medium Impact** (Week 1):
  - [ ] Parallel threat intel (2 hr)
  - [ ] Bounded stats tracker (1.5 hr)

- [ ] **P2 Polish** (Week 2):
  - [ ] Memoized hash calc (30 min)
  - [ ] Batch file operations (review all scripts)

- [ ] **Testing** (Week 2):
  - [ ] Benchmark suite runs
  - [ ] Load testing (100-hash batch)
  - [ ] Memory profiling (24-hour soak)

- [ ] **Monitoring** (Week 3+):
  - [ ] Deploy to staging
  - [ ] 7-day metrics collection
  - [ ] Production rollout

---

## Expected Cumulative Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Threat intel lookup (avg)** | 8-15s | 2-5s | 70% ↓ |
| **Rate limiter I/O** | 300 reads/min | 12 reads/min | 95% ↓ |
| **Tray app I/O** | 28,800 reads/day | 50-200 reads/day | 99% ↓ |
| **Embedding cost** | $3/month | $0.60/month | 80% ↓ |
| **Cache hit rate** | 20-30% | 60-80% | 2-3x ↑ |
| **Memory (daemon)** | Growing | Stable | Leak fixed |

---

## Risk Mitigation

1. **Backward Compatibility:** All changes are internal. Public APIs unchanged.
2. **Rollback Plan:** Feature flags for each optimization (disable via env var).
3. **Gradual Rollout:** Deploy P0 quick wins first, monitor 48h before P1/P2.
4. **Testing:** Comprehensive benchmark suite + 24-hour soak test.

---

## References

- Original analysis: `docs/PERFORMANCE-ANALYSIS.md`
- Benchmark tests: `tests/test_performance_tuning.py`
- Rate limiter: `ai/rate_limiter.py`
- Router: `ai/router.py`
- Tray app: `tray/security_tray_qt.py`

---

**Next Action:** Start with P0 quick wins (3 hours total effort, 90%+ of impact).
