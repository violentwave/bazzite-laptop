# Changelog — Bazzite AI Enhancement Layer
<!-- System: Acer Predator G3-571 | Bazzite 43 | Last updated: 2026-04-06 -->

All notable changes are recorded here. Phases correspond to the original
implementation plan for the AI enhancement layer built on top of the base
Bazzite security/gaming system.

---

## Phase P24–P28 — Metrics, Memory, Provider Intel, Insights, Alerts (2026-04-06)

### Delivered
- **P24 MetricsRecorder** (`ai/metrics.py`): Full LanceDB-backed time-series recorder;
  buffered thread-safe flush at 100 events or 60s; `VALID_METRIC_TYPES`; `get_recorder()`;
  `record_metric()` with full 5-arg signature; `query_summary()`; `get_raw()`;
  backward-compat `track_performance` decorator retained
- **P28 InsightsEngine** (`ai/insights.py`): `insights_cache` LanceDB table with TTL expiry;
  `generate_weekly()`, `generate_on_demand()`, `get_cached_insights()`, `format_for_newelle()`;
  `get_engine()`; `run_insights_generation()` — no LLM calls, summarises existing LanceDB data
- **P27 Security alerts** (`ai/alerts/dispatcher.py`, `ai/alerts/history.py`): desktop
  notification dispatcher, alert history store
- **P25 Memory** (`ai/memory.py`): confirmed spec-complete; 768-dim conversation_memory table;
  secret redaction via InputValidator; `summarize_session()`
- **P26 Provider Intel** (`ai/provider_intel.py`): unblocked by metrics rewrite; scoring formula
  `(1/(1+latency_p95)) * (1-error_rate) * health_multiplier` operational
- **MCP tool system.insights**: on-demand insights via `get_engine().generate_on_demand()`;
  fixed stale `system.weekly_insights` handler (was calling non-existent method)
- **Scripts**: `generate-weekly-insights.py`, `security-alert-eval.py`, `metrics-compact.py`;
  `weekly-insights.service` wired to new API
- **CI/CD**: dependabot config, CodeQL workflow, pyproject.toml duplicate key fixed,
  `.hypothesis/` gitignored
- **Tests**: `test_metrics.py` (14), `test_insights.py` (11), `test_properties.py`,
  `test_performance.py`, `test_handoff_parser.py`, `test_alerts_desktop.py` added;
  suite: ~1816 passed

### Numbers after this phase
- MCP tools: 76 | Timers: 21 | LanceDB tables: 8 | Tests: ~1816

---

## Phase P40 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTools | Target Modules |
|-------|------|--------|----------------|
| P40 | Performance Round 2 + Observability | +1 | `ai/metrics.py`, `ai/rate_limiter.py`, `ai/threat_intel/lookup.py`, `ai/mcp_bridge/server.py` |

### Details

**P40 — Performance Round 2 + Observability:**
- **`ai/metrics.py`** (new): Lightweight performance metrics module
  - `@track_performance` decorator: records call counts, latencies, errors
  - `get_metrics()` / `reset_metrics()`: thread-safe snapshot and clear
  - `record_metric()`: arbitrary metric recording (token counts, cache hits)
  - Uses `defaultdict` + `threading.Lock` for safety
- **`ai/rate_limiter.py`**: Added `prune_stale_entries()` method
  - Removes provider entries with all-zero counters and expired minute windows
  - Atomic write with file locking
- **`ai/threat_intel/lookup.py`**: Restored full cascading lookup logic
  - VT/OTX client caching via `@lru_cache(maxsize=1)`
  - Async parallel execution (`_parallel_lookup_all` + `asyncio.gather`)
  - `parallel=True/False` flag on `lookup_hash()` / `lookup_hashes()`
  - Cascade order: MalwareBazaar → OTX → VT (cheapest first)
- **`ai/threat_intel/models.py`**: Added `cached_ratio` field + `detection_ratio_float` property
- **Decorated 4 high-value call sites** with `@track_performance`:
  - `rag_query`, `embed_single`, `route_query`, `lookup_hash`
- **Added MCP tool**: `system.perf_metrics` (tools 75 → 76)
  - Query metrics by function name or get all
  - `reset=True` clears recorded data
- **19 new tests** in `tests/test_perf_round2.py`

---

## Phase P39 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTools | Target Modules |
|-------|------|--------|----------------|
| P39 | Supply Chain Security | +2 | `ai/system/depaudit.py`, `systemd/dep-audit.timer` |

### Details

**P39 — Supply Chain Security Hardening:**
- Created `ai/system/depaudit.py`: pip-audit wrapper with SBOM generation
  - `run_dep_audit()`: runs pip-audit, returns structured results
  - `write_report()`: atomic JSON write + P37 alert dispatch
  - `generate_sbom()`: CycloneDX-lite SBOM from pip list
  - `get_latest_report()` / `get_report_history()`: MCP tool helpers
- Created `systemd/dep-audit.timer` (Sunday 03:00) + `.service` (oneshot)
- Added alert rule `dep_vuln_found` in `ai/alerts/rules.py` (critical, 24hr cooldown)
- Added MCP tools: `system.dep_audit`, `system.dep_audit_history` (tools 73 → 75)
- Created `.secrets.baseline` for detect-secrets pre-commit hook
- Added pytest-cov to CI with 70% threshold, pip-audit step (non-blocking)
- `tests/test_dep_audit.py`: 11 tests

---

## Phase P38 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTools | Target Modules |
|-------|------|--------|----------------|
| P38 | HANDOFF Auto-Capture | +1 | `ai/learning/handoff_parser.py` |

### Details

**P38 — HANDOFF Auto-Capture:**
- Created `ai/learning/handoff_parser.py`: HandoffEntry dataclass + parse functions
- Created `scripts/parse-handoff.py`: CLI with `--dry-run` and `--since-date` flags
- Added MCP tool: `knowledge.session_history` (tools 72 → 73)
- `tests/test_handoff_parser.py`: 9 tests covering parsing, filtering, conversion

---

## Phase P37 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTools | Target Modules |
|-------|------|--------|----------------|
| P37 | Adaptive Desktop Alerting | +2 | `ai/alerts/` |

### Details

**P37 — Adaptive Desktop Alerting:**
- Created `ai/alerts/` package with rules, dispatcher, history modules
- `ai/alerts/rules.py`: SQLite-backed alert rules with cooldown tracking
- `ai/alerts/dispatcher.py`: notify-send integration via subprocess
- `ai/alerts/history.py`: Alert history with acknowledge support
- Added 2 MCP tools: `system.alert_history`, `system.alert_rules`
- Updated tool count: 70 → 72

---

## Phase P36 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTests | Target Modules |
|-------|------|--------|----------------|
| P36 | Mutation & Property Hardening | +9 | input_validator, cache, ratelimiter, health |

### Details

**P36 — Mutation & Property Hardening:**
- `tests/test_properties.py`: 9 property-based tests using hypothesis
- Tests cover: input_validator, cache, ratelimiter, health modules
- Settings: max_examples=200 (security), deadline=500ms
- mutmut requires setup.cfg configuration (deferred for now)

---

## Phase P35 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTests | Covered Modules |
|-------|------|--------|----------------|
| P35 | Test Coverage Blitz | 0 | MCP bridge, log intel, threat intel already covered |

### Details

**P35 — Test Coverage Blitz:**
- Verified existing test coverage for critical modules:
  - `tests/test_mcp_bridge_server.py`: MCP bridge server tests (8 tests)
  - `tests/test_mcp_bridge_tools.py`: Tool dispatch tests (31 tests)
  - `tests/test_log_intel_ingest.py`: Log ingestion tests (23 tests)
  - `tests/test_threat_intel.py`: Threat lookup tests (41 tests)
  - `tests/test_threat_summary.py`: Threat summary tests (17 tests)
  - `tests/test_playbooks.py`: Playbook tests (24 tests)
- Total tests: **1965 collected** (already exceeds ~1834 target from playbook)

---

## Phase P34 Complete (2026-04-04)

### Summary
| Phase | Name | ΔTools | ΔTimers | ΔTables | ΔTests | Key Module |
|-------|------|--------|---------|---------|--------|-------------|
| P34 | Performance Hardening | 0 | 0 | 0 | +14 | `ai/rag/embedder.py`, `ai/rate_limiter.py`, `ai/health.py`, `ai/router.py` |

### Final State After P34
- **MCP tools:** 70
- **Timers:** 20
- **LanceDB tables:** 23
- **Tests:** ~1684 (+12)

### Details

**P34 — Performance Hardening:**
- `ai/rag/embedder.py`: Added `embed_texts_async()` with `asyncio.gather` + `Semaphore(5)` concurrency limit
- `ai/rag/query.py`: Verified parallel search using `ThreadPoolExecutor(max_workers=3)` (already existed)
- `ai/rate_limiter.py`: In-memory cache with background flush daemon (60s), `threading.RLock`, `atexit` flush on shutdown
- `ai/health.py`: Added `_cached_score` + `_score_cache_time` fields on `ProviderHealth`, `invalidate_cache()` called from `record_success()`/`record_failure()`
- `ai/router.py`: Added `_config_mtime` tracking to avoid unnecessary file reads; added `httpx.Client` with connection pooling (max_keepalive=20, max_connections=100)
- `tests/test_performance.py`: 14 regression tests covering all performance fixes

---

## Phase P29–P33 Complete (2026-04-04)

### Summary

| Phase | Name | ΔTools | ΔTimers | ΔTables | Key Module |
|-------|------|--------|---------|---------|-------------|
| Prereq | MCP Tool Filtering | 0 | 0 | +1 | `ai/mcp_bridge/tool_filter.py` |
| P32 | Testing Intelligence | 0 | 0 | +1 | `ai/testing/` |
| P29 | Structural Code Intel | +6 | +1 | +4 | `ai/code_intel/` |
| P31 | Agent Collaboration | +3 | 0 | +2 | `ai/collab/` |
| P30 | Workflow Engine | +2 | 0 | +1 | `ai/workflows/` |
| P33 | Plugin Factory | +2 | 0 | +1 | `ai/tools/` |
| **Total** | | **+13** | **+1** | **+10** | |

### Final State After P33
- **MCP tools:** 57 → 70
- **Timers:** 19 → 20
- **LanceDB tables:** 13 → 23
- **Tests:** ~1672 → ~1800+

### Details

**Prereq — MCP Tool Filtering:**
- `ai/mcp_bridge/tool_filter.py`: namespace + semantic tool filtering
- LanceDB `tool_metadata` table for semantic tool search
- Core tools always included (health, disk, memory, services, manifest)
- Max 15 tools per context window
- `tests/test_tool_filter.py`: 10 test cases

**P32 — Testing Intelligence:**
- `ai/testing/test_intelligence.py`: `TestStabilityTracker` with SQLite stability tracking
- `ai/testing/pytest_plugin.py`: auto-record test results via pytest hook
- `ai/testing/traceability.py`: LanceDB `test_mappings` table
- `scripts/test-smart.sh`: smart/full/flaky test runner modes
- `pyproject.toml`: timeout, quarantine marker configuration
- `tests/test_testing_intelligence.py`: 6 test cases

**P29 — Structural Code Intelligence:**
- `ai/code_intel/parser.py`: AST-based parser + grimp import graph
- `ai/code_intel/store.py`: 4 LanceDB tables for code knowledge graph
- 6 new MCP tools: `code.impact_analysis`, `code.dependency_graph`, `code.find_callers`, `code.suggest_tests`, `code.complexity_report`, `code.class_hierarchy`
- `code-index.timer`: daily code re-indexing (06:00)
- PyDriller co-change mining for historical analysis

**P31 — Agent Collaboration:**
- `ai/collab/task_queue.py`: SQLite task queue with agent routing
- `ai/collab/shared_context.py`: LanceDB `shared_context` for decisions/findings
- `ai/collab/knowledge_base.py`: cross-agent learning with confidence decay
- `ai/collab/file_claims.py`: file-level claim system with auto-expiry
- 3 MCP tools: `collab.queue_status`, `collab.add_task`, `collab.search_knowledge`

**P30 — Workflow Engine:**
- `ai/workflows/runner.py`: multi-tool composition with ReAct loop
- `ai/workflows/definitions.py`: LanceDB `workflows` table
- `ai/workflows/triggers.py`: watchdog file watcher + asyncio event bus
- 2 MCP tools: `workflow.run`, `workflow.list`

**P33 — Plugin Factory:**
- `ai/tools/builder.py`: `SafetyValidator` + `ToolBuilder` with LanceDB persistence
- `ai/tools/composites.py`: composite tool patterns with parallel execution
- 2 MCP tools: `system.create_tool`, `system.list_dynamic_tools`
- AST-based safety: blocks `os`, `subprocess`, `eval`, `__import__`

---

## Audit: P24–P28 (2026-04-04)

### Fixed
- **REGRESSION** `tests/test_memory.py`: Mocked `ConversationMemory.__init__` in `TestSingleton::test_singleton_returns_same_instance` — was calling real LanceDB on read-only filesystem
- **BUG** `ai/insights.py`: `generate_weekly_insights()` called non-existent `query_timeseries()` → replaced with `get_raw(hours=168, metric_type=...)`; corrected metric key `budget_usage` → `budget_spend`
- **BUG** `ai/insights.py`: `_ensure_schema()` declared 6-field schema but `_store_insight()` wrote 2 columns and `get_latest_insights()` read `row["data"]` — schema corrected to 2 fields: `timestamp` + `data`
- **BUG** `ai/insights.py`: `_store_insight()` created `pa.record_batch` with mismatched arrays/schema — replaced with `pa.table({...})` using correct column names
- **MISSING** `tests/test_alerts.py`: Added 15 tests for `SecurityAlertEvaluator` (CVE severity mapping, release alert filtering, deduplication, atomic writes)
- **MISSING** `tests/test_insights.py`: Added 9 tests for `InsightsEngine` (init, generate, get_latest, store)
- **MISSING** `scripts/lancedb-prune.py`: Added `task_patterns` (90d), `semantic_cache` (30d), `metrics` (30d), `conversation_memory` (90d), `system_insights` (365d) to `RETENTION_TABLES`
- **DOCS** `docs/AGENT.md`: Added `system_insights` to LanceDB tables list; updated last-updated date

### Verified Clean
- Ruff: zero violations across all P24–P28 source and test files
- `ai.router` import: absent from `ai/mcp_bridge/` (confirmed)
- LanceDB `.where()` predicates: all safe (int params or VALID_TASK_TYPES allowlist)
- MCP handlers: all 5 new tools have `try/except`; `security.alert_summary` dispatches via no-arg/json_file path
- Atomic writes in `ai/security/alerts.py`: tmp + rename pattern confirmed
- Secret redaction in `ai/memory.py`: `InputValidator.redact_secrets()` called before embedding
- No LLM calls in `ai/insights.py`: heuristic-only (confirmed)
- Tool count: 57 allowlist + 1 health = 58 total; test assertions correct
- Timer count: 19 (correct)

---

## Phase 28 — Self-Improvement Loop (2026-04-04)

### New Files
- `ai/insights.py` — InsightsEngine: weekly heuristic analysis of cache/budget metrics stored as lance dataset
- `systemd/weekly-insights.service` / `systemd/weekly-insights.timer` — Mon 09:00 weekly trigger

### Changed Files
- `configs/mcp-bridge-allowlist.yaml` — added `system.weekly_insights` tool
- `ai/mcp_bridge/server.py` — registered `system.weekly_insights` handler (tools 56→57)
- `docs/AGENT.md` — updated counts (tools 56→57, timers 18→19)

### Metrics
- MCP tools: 56 → 57
- Timers: 18 → 19 (weekly-insights.timer)
- New LanceDB table: `system_insights`

---

## Phase 27 — Proactive Security Alerting (2026-04-04)

### New Files
- `ai/security/alerts.py` — SecurityAlertEvaluator: CVE results, scan freshness, release advisory alerts with 7-day deduplication
- `systemd/security-alert.service` / `systemd/security-alert.timer` — every 6h trigger

### Changed Files
- `configs/mcp-bridge-allowlist.yaml` — added `security.alert_summary` (json_file source)
- `ai/mcp_bridge/server.py` — added `security.alert_summary` annotation; dispatches via no-arg/json_file path (tools 55→56)
- `docs/AGENT.md` — updated counts (tools 55→56, timers 17→18)

### Metrics
- MCP tools: 55 → 56
- Timers: 17 → 18 (security-alert.timer)

---

## Phase 26 — Provider Intelligence & Dynamic Routing (2026-04-04)

### New Files
- `ai/provider_intel.py` — ProviderIntelligence: reads health scores + metrics to produce per-provider status

### Changed Files
- `configs/mcp-bridge-allowlist.yaml` — added `system.provider_status` tool
- `ai/mcp_bridge/server.py` — registered `system.provider_status` handler (tools 54→55)
- `docs/AGENT.md` — updated counts (tools 54→55)

### Metrics
- MCP tools: 54 → 55

---

## Phase 25 — Cross-Session Conversation Memory (2026-04-04)

### New Files
- `ai/memory.py` — ConversationMemory: LanceDB-backed cross-session memory with embedding, redaction, dedup

### Changed Files
- `configs/mcp-bridge-allowlist.yaml` — added `memory.search` tool
- `ai/mcp_bridge/server.py` — registered `memory.search` handler (tools 53→54)
- `docs/AGENT.md` — updated counts (tools 53→54, LanceDB tables 11→12: conversation_memory)

### Metrics
- MCP tools: 53 → 54
- LanceDB tables: 11 → 12 (conversation_memory)

---

## Phase 24 — Observability & Metrics Pipeline (2026-04-04)

### New Files
- `ai/metrics.py` — MetricsRecorder: buffered LanceDB time-series with query_summary/get_raw
- `scripts/metrics-compact.py` — weekly metrics compaction
- `systemd/metrics-compact.service` / `systemd/metrics-compact.timer` — Sun 03:00 trigger

### Changed Files
- `configs/mcp-bridge-allowlist.yaml` — added `system.metrics_summary` tool
- `ai/mcp_bridge/server.py` — registered `system.metrics_summary` handler (tools 52→53)
- `docs/AGENT.md` — updated counts (tools 52→53, timers 16→17, LanceDB tables 10→11: metrics)

### Metrics
- MCP tools: 52 → 53
- Timers: 16 → 17 (metrics-compact.timer)
- LanceDB tables: 10 → 11 (metrics)

---

## Audit: P22 + P23 (2026-04-03)

### Fixed
- **SECURITY** `ai/cache_semantic.py`: Added `VALID_TASK_TYPES` allowlist and validation in `SemanticCache.get()` — prevents SQL injection via LanceDB `.where()` clause
- **CORRECTNESS** `ai/mcp_bridge/server.py`: Updated module docstring (46→52 tools); added `try/except` to `knowledge.task_patterns` handler; returns error dict instead of raising
- **QUALITY** `ai/router.py`: Fixed `response.usage.get()` anti-pattern in `route_query` and `route_chat` — `usage` is a LiteLLM object, not a dict; actual token counts now correctly passed to `budget.record_spend()`
- **TESTS** `tests/test_semantic_cache.py`: Added Ollama availability skipif guard to `test_semantic_cache_hit` and `test_semantic_cache_miss`
- **TESTS** `tests/test_mcp_tools.py`, `tests/test_mcp_server.py`, `tests/test_mcp_drift.py`: Updated stale tool count assertions (50→52) and handler lookup logic
- **TESTS** `tests/test_task_logger.py`: Replaced live embedding calls with mocks; added `requires_writable_db` guard for CLI integration test
- **DOCS** `docs/AGENT.md`: Added missing `knowledge.task_patterns` and `system.budget_status` table rows; updated all stale "50 tool" references to 52
- **DOCS** `docs/newelle-system-prompt.md`: Synced tool count (50→52)

### New Tests Added
- `test_semantic_cache_rejects_invalid_task_type` — validates ValueError for invalid task_type
- `test_budget_record_spend_accumulates` — validates record_spend accumulation
- `test_knowledge_task_patterns_docstring_tool_count` — canary for stale server.py docstring

---

## Phase 23 — Semantic Cache & Token Budget (2026-04-03)

### New Files
- `ai/cache_semantic.py` — SemanticCache: LanceDB-backed similarity cache with TTL per task_type
- `ai/budget.py` — TokenBudget: daily token limits with priority tiers (security, scheduled, interactive, coding)
- `configs/token-budget.json` — Budget allocation config (4 tiers)
- `tests/test_semantic_cache.py` — 4 new tests
- `tests/test_budget.py` — 6 new tests

### Changed Files
- `ai/router.py` — SemanticCache + TokenBudget integrated into LLM call path
- `configs/mcp-bridge-allowlist.yaml` — added system.budget_status tool
- `ai/mcp_bridge/server.py` — registered system.budget_status handler (tools 51→52)
- `docs/AGENT.md` — updated counts (tools 51→52, tables 8→9), documented cache and budget systems

### Metrics
- MCP tools: 51 → 52
- LanceDB tables: 8 → 9 (semantic_cache)
- New tests: 10

---

## Phase 22 — Task Pattern Learning (2026-04-03)

### New Files
- `ai/learning/__init__.py` — learning package
- `ai/learning/task_logger.py` — TaskLogger: logs successful task outcomes to LanceDB
- `ai/learning/task_retriever.py` — retrieve_similar_tasks(): semantic similarity search
- `scripts/log-task-success.py` — CLI for manually logging task successes
- `tests/test_task_logger.py` — 6 new tests

### Changed Files
- `configs/mcp-bridge-allowlist.yaml` — added knowledge.task_patterns tool
- `ai/mcp_bridge/server.py` — registered knowledge.task_patterns handler (tools 50→51)
- `docs/AGENT.md` — updated counts and documented task_patterns table

### Metrics
- MCP tools: 50 → 51
- LanceDB tables: 7 → 8 (task_patterns)
- New tests: 6
- Scripts: 40 → 41

---

## Phase 20 — Headless Security & Timer Sentinel (2026-04-03)

### Deliverables
- `scripts/security-briefing.py` — headless daily briefing; reads all
  security data sources, calls timer_sentinel, writes structured markdown to
  `~/security/briefings/briefing-YYYY-MM-DD.md`; no LLM required
- `ai/agents/timer_sentinel.py` — validates all 16 systemd timers against
  expected firing windows; returns structured JSON (healthy/warning/critical)
- `systemd/security-briefing.service` + `.timer` — daily 08:45 with
  `Persistent=true` (fires after overnight/gaming sessions)
- MCP tool `agents.timer_health` registered; tool count 48 → 49
- `tests/test_timer_sentinel.py` (9 tests) + `tests/test_security_briefing.py`
  (7 tests)

### Metrics
- MCP tools: 48 → 49
- Tests: 1658 → 1672

---

## Phase 21 — Code Knowledge Base Expansion (2026-04-03)

### Deliverables
- `ai/rag/pattern_store.py` — LanceDB table for curated code patterns with
  HNSW indexing
- `ai/rag/pattern_query.py` — semantic search with language/domain filtering
- `scripts/ingest-patterns.py` — batch ingestion of 28 pattern files from
  `patterns/`
- `tests/test_pattern_store.py` — 11 tests for pattern store/query
- MCP tool `knowledge.pattern_search` registered; tool count 49 → 50

### Metrics
- MCP tools: 49 → 50
- Systemd timers: 15 → 16
- Tests: ~1656 → 1672 passed, 191 skipped

### Key design decisions
- `Persistent=true` on timer: briefings fire after overnight gaming sessions
- `RandomizedDelaySec=2min`: avoids thundering herd with 8:00/8:15/8:30 timers
- 100% deterministic output — no LLM calls in briefing script
- Graceful degradation: each data source individually wrapped; missing files
  produce placeholder sections rather than aborting
- `security-briefing.timer` included in sentinel's own registry (self-monitors)

---

## Phase 19 — Input Validation MCP Safety Layer (2026-04-03)

- **New `ai.security.inputvalidator` module:** Standalone input validation with stdlib-only dependencies (no external deps)
- **New `configs/safety-rules.json`:** Max input length (10k), forbidden patterns, path allowlists, high-risk tool flags
- **MCP bridge pre-dispatch validation:** All tool arguments validated before execution in `ai/mcp_bridge/tools.py`
- **Secret redaction:** API keys, tokens, and credentials automatically redacted from logs before output
- **Detection patterns:** SQL injection (`UNION SELECT`, `DROP TABLE`, `' OR 1=1`), command injection (`;`, `&&`, `||`, `$()`), path traversal (`../`)
- **Tests:** 51 new tests covering SQL/command injection, path traversal, secret redaction, max length, config loading, high-risk tools
- **Final test count:** 1656 passed (non-integration suite), 171 skipped
- Tool count: 48 (unchanged)
- Timer count: 15 (unchanged)

---

## Phase 18 — Storage Consolidation & Retention (2026-04-03)

- **R2 lifecycle rules:** One-time `scripts/r2-set-lifecycle.py` sets 180-day auto-expiration on R2 bucket — no client-side long-term deletion needed
- **Journald tuning:** `configs/journald-bazzite.conf` caps journal at 256M / 20 files / 7 days (manual deploy to `/etc/systemd/journald.conf.d/`)
- **Cache cleanup:** `scripts/lancedb-prune.py` now also cleans stale threat/RAG/IP/IOC cache files and keeps only 5 most recent cost archives
- **system.pipeline_status MCP tool:** Shows ingest/archive/retention status, pending files, table row counts, staleness warnings (tool count: 47 → 48)

---

## Phase 17 — Log Lifecycle Pipeline (2026-04-03)

- **LanceDB retention pruning:** New `scripts/lancedb-prune.py` — 90-day retention for log tables (`health_records`, `scan_records`, `security_logs`, `sig_updates`), 180-day for `threat_intel`, compact + cleanup of `.tmp` dirs, `--dry-run` and `--retention-days` flags
- **Archive state tracking:** New `.archive-state.json` records every R2 upload with key, timestamp, size bytes. Verify-before-delete gate ensures local logs are NOT deleted until both LanceDB ingest AND R2 archive are confirmed
- **Stale R2 fix:** Fixed upload_file() returning (success, r2_key, compressed_size) without deleting local file. Deletion now handled separately with own except block. Added ingest verification gate: local deletion only attempted after verifying file appears in .ingest-state.json (lexicographic comparison of filenames)
- **Systemd pipeline:** Three-stage weekly chain via service dependencies:
  - Sun 00:30: `log-ingest` (ingests new logs into LanceDB)
  - Sun 01:00: `log-archive` (After=log-ingest, archives to R2)
  - Sun 02:00: `lancedb-optimize` (After=log-archive, prunes old rows + compacts)
- **Pipeline tests:** 12 new tests covering retention, dry-run, archive state, ingest verification gate, and systemd dependency parsing
- Timer count: 14 → 15

---

## Phase 16 — Performance Optimization (2026-04-03)

- **HTTP session reuse:** Module-level `requests.Session()` with connection pooling in lookup.py, ip_lookup.py, ioc_lookup.py (30-50% latency reduction per API call)
- **Threat intel caching:** Disk-based `JsonFileCache` for hash lookups (7d TTL), IP lookups (24h TTL), IOC lookups (7d TTL) — 80-95% reduction in repeated API calls
- **RAG query caching:** 5-minute disk cache for `rag_query()` results
- **Parallel RAG searches:** `ThreadPoolExecutor` for concurrent log/threat/doc searches (3x → 1x latency)
- **Auto cache eviction:** Background daemon thread evicts expired entries hourly
- **Bounded provider tracking:** `OrderedDict` with max 50 providers, LRU eviction
- **Embedding LRU cache:** In-memory `@lru_cache(maxsize=500)` for `embed_single`
- **Qt inotify:** Replaced 3s polling with `QFileSystemWatcher` + 30s fallback
- **SHA256 hash caching:** `@lru_cache(maxsize=10000)` on `_key_hash()` in JsonFileCache
- **Cost stats auto-archive:** Auto-archive + reset at 100k calls

---

## Database Integrity Test Suite (2026-04-03)

- test: Add `test_lancedb_auto_repair` in `tests/test_rag_e2e.py` that:
  - Creates isolated LanceDB test table with mixed valid/corrupted vectors
  - Injects NaN vectors and wrong-dimension vectors to trigger corruption
  - Verifies `_detect_corruption()` detects issues
  - Verifies `repair_database()` removes corrupted rows, preserves valid rows
- test: Add `test_prune_keeps_only_3_recent` in `tests/test_knowledge_storage.py` that:
  - Creates 5 timestamped backup directories with explicit mtimes
  - Verifies `_prune_old_backups()` removes 2 oldest, keeps 3 most recent
- docs: Move "Corruption injection tests" and "Backup retention pruning"
  from Testing Gaps to Confirmed Work in `project_memory.md`

---

## Post-Phase 15 — Provider Chain Cleanup (2026-04-02)

- fix: full 6-provider chains for all task types, verified model names and rate limits
  - `configs/litellm-config.yaml`: removed duplicate z.ai entries (GLM-4.7-Flash, GLM-4.5-Air, GLM-5, GLM-4.7); consolidated to `openai/GLM-4-32B` at `https://api.z.ai/v1` for fast, reason, code
  - `configs/litellm-config.yaml`: batch mistral `codestral-latest` → `mistral-small-latest` (Codestral is code-specialized, not batch)
  - `configs/litellm-config.yaml`: cerebras `llama3.1-8b` → `llama-4-scout-17b-16e-instruct` (fast/batch); added `retry_after: 5` to router_settings
  - `configs/ai-rate-limits.json`: gemini 60 rpm → 1500 rpm / 10000 rpd (Pro subscription actual limit); cerebras rpd null → 1000; openrouter rpd 50 → 200

---

## Post-Phase 15 — Stabilization (2026-04-02)

- fix: upgrade Gemini models to 2.5-series (1.5 shutdown, 2.0 deprecated June 2026)
  - `configs/litellm-config.yaml`: fast/batch → `gemini-2.5-flash-lite`; reason → `gemini-2.5-pro`; code → `gemini-2.5-flash` (unchanged)
- fix: correct health cooldown and rate limits to match actual upstream caps
  - `ai/health.py`: failure_threshold 3→5, base_cooldown 300s→120s, max_cooldown 1800s→600s
  - `configs/ai-rate-limits.json`: groq 30 rpm/14400 rpd; cerebras 30 rpm; mistral 20 rpm; openrouter 20 rpm/50 rpd
  - `configs/litellm-config.yaml`: num_retries 0→2, allowed_fails 1→3
- Rebuilt Newelle system prompt: native file tool routing (`read_file`, `write_file`, `edit`, `list_directory`), absolute-path rules, failure recovery guards
- Added memory content filtering in `ai/rag/memory.py` to reduce runtime prompt bloat
- Added bounded retry with exponential backoff in `ai/rag/ingest_docs.py` for state-file writes (max 3 attempts)
- Rebuilt `.venv` with clean `requirements-ai.txt` (125 packages, no system deps like Brlapi/cockpit)
- Fixed 4 test failures: ingest retry mock (`os.rename` closure), MCP bridge health patch target (`_check_router_health` → none needed), rate limit test isolation (global + per-tool state leak)
- Ruff clean: 15 auto-fixed errors + 2 manual fixes across test files

---

## Phase 15 — Threat Intel Correlation & Response Planning (2026-03-31)

- **Threat Correlation Engine:** New `ai/threat_intel/correlator.py` with 
  `CorrelationReport` dataclass that cross-references IOCs (hash, IP, URL, CVE)
  across existing lookup modules and builds correlation graphs
- **MITRE ATT&CK Mapping:** Static mapping in `configs/mitre-attack-map.json`
  with technique references (T1059, T1486, T1071, etc.) for each IOC type
- **security.correlate MCP tool:** New tool (tool count: 45 → 47) that takes 
  IOC + type and returns structured correlation report with linked IOCs,
  MITRE techniques, confidence scores, and risk level
- **Response Playbooks:** New `ai/threat_intel/playbooks.py` with recommended
  response steps based on threat type and severity:
  - KEV CVE → check fedora updates → apply patch or compensating controls
  - Malicious hash → sandbox analysis → block related network IOCs
  - Suspicious IP → check associated URLs → firewall rules
  - Suspicious URL → analyze → block domain → notify users
- **security.recommend_action MCP tool:** New tool (tool count: 47) that 
  generates structured response plans with urgency levels and action steps
- **security.threat_summary Upgrade:** Added `risk_score` (low/medium/high/critical),
  `correlation_links` between findings, and `recommended_actions` per finding

---

## Phase 14 — Observability Enhancements (2026-03-31)

- **LiteLLM cost tracking:** Added `get_cost_stats()` and `get_usage_stats()` 
  in `ai/router.py` with persistent counters (total_tokens, total_cost_usd, 
  call_count, by_provider, by_task_type) since service start
- **Sentry integration:** Added optional Sentry error tracking in `ai/llm_proxy.py`
  with breadcrumb logging for LLM requests; gracefully degrades if sentry-sdk unavailable
- **Provider health improvements:** Enhanced `get_health_snapshot()` with retry logic,
  exponential backoff, circuit breaker pattern for failing providers
- **Freshness timestamps:** Added `generated_at` ISO8601 timestamps to all runtime 
  JSON files (llm-status.json, release-watch.json, fedora-updates.json, key-status.json)
  via shared `ai/utils/freshness.py` helper
- **system.token_report MCP tool:** New tool (tool count: 44 → 45) reading llm-status.json
  with usage breakdown by task type, provider health summary, and freshness warnings
- **Freshness-aware MCP tools:** JSON-reading tools now include "Data is X hours old."
  warnings when data exceeds 1 hour age threshold

---

## Phase 13 — LanceDB Hybrid Search + Compaction (2026-03-31)

- Upgraded LanceDB from 0.29.2 to 0.30.1
- Added BM25 full-text search indexes to security_logs, docs, health_records, scan_records tables
- Fixed table_names() deprecation — migrated to list_tables() across codebase
- Added lancedb-optimize.timer (weekly Sunday 02:00) for table compaction
- Timer count: 13 → 14

## Phase 12 — FastMCP 3.x Upgrade + Tool Annotations (2026-03-31)

- **PingMiddleware:** Added `PingMiddleware(interval_ms=25000)` to the MCP bridge server
  to prevent idle disconnections (previously dropped after ~60s of inactivity)
- **MCP Tool Annotations:** Added behavioural hints to all 44 allowlisted tools via
  the `annotations=` kwarg on `@mcp.tool()`:
  - `readOnlyHint=True` on 30 read-only tools → Newelle skips confirmation dialogs
  - `idempotentHint=True` on 35 safe-to-retry tools
  - `openWorldHint=True` on 4 external threat-intel tools (VT/AbuseIPDB/etc.)
  - `destructiveHint=True` on `security.sandbox_submit` (irreversible external action)
- **FastMCP upgrade:** Attempted upgrade to 3.2.0; blocked by proxy/network issue.
  All Phase 12 features were available in the existing 3.1.1 install.
- **Background tasks:** Skipped — `task=True` requires `pydocket` (Redis-backed);
  adding Redis as a dependency is out of scope for this single-user system.

---

## Phase 11 — Cache Security Fix

- Replaced `diskcache` 5.6.3 with new `ai/cache.py` (`JsonFileCache`) to fix
  CVE-2025-69872 (insecure pickle deserialization RCE)
- `JsonFileCache`: JSON-only storage, atomic writes (tempfile + os.replace),
  2-level directory sharding, per-task-type TTLs, thread-safe counters
- Removed `diskcache` from tracked dependencies; `litellm.cache` set to `None`
- Added `system.cache_stats` MCP tool (tool count: 43 → 44)
- Manual cache get/set wraps provider calls in `route_query()` and `route_chat()`

---

## Phase 10 — Newelle Full Operational Capability

- Rewrote `docs/newelle-system-prompt.md` from scratch: compact 43-tool routing
  table, run/show disambiguation, model switching guidance, workflow recipes,
  tool-first enforcement with correct/incorrect examples, Newelle prompt
  variables ({DATE}, {USER}, {COND: tts_on})
- Updated `docs/newelle-skills/bazzite-system.md`: fixed `system.pkg_intel`
  args to match AGENT.md (no required args, not `package`)
- Verified `docs/newelle-skills/` (all 5 bundles) against AGENT.md — remaining
  4 bundles confirmed current, no other changes needed
- Verified `docs/morning-briefing-prompt.md` — all 7 tool names confirmed
  correct; updated "Last updated" date to 2026-03-31
- Added `### Switching models via Newelle Profiles` subsection to USER-GUIDE.md
  section 5 (LLM Provider Chain): Profile Manager workflow, 4 suggested profiles,
  endpoint/key configuration notes
- AGENT.md confirmed current: 13 timers (service-canary.timer present), date
  2026-03-31 — no changes needed

---

## Phase 9 — Automation & Resilience

- VS Code: `tasks.json` updated (Verify Services fixed, Ingest Code + Full Quality Gate added)
- Pre-commit hook: ruff lint on staged `.py` files (`scripts/pre-commit-hook.sh` + `install-hooks.sh`)
- Dependency freshness checker: `scripts/check-deps.sh` + `code_quality_agent` integration
- RAG smart embed: `scripts/rag-smart-embed.sh` with staleness detection (skips unchanged docs/code)
- Service resilience: `RestartSec=10`, `RestartMax=5`, `service-canary.timer` (every 15m)
- Deploy safety: `--dry-run` flag, blanket `restorecon`, auto-verify on deploy

---

## Phase 8 — Clean Slate

**Bug fixes:**
- Fixed `smartctl` not found WARNING in health checks (added path resolution)
- Fixed `findmnt` composefs false alarm (filtered immutable OS overlay)
- Fixed log/tlog quiet mode crash (graceful handling of empty output)
- Fixed `pkg_intel` license field parsing error
- `ai/rag/ingest_code.py`: Filter empty/whitespace chunks before Gemini embedding

**Cleanup:**
- AgentDB formally deprecated — removed from AGENT.md known issues,
  cleaned 64+ legacy references from `.claude/` skills/agents/rules
- `auto-memory-store.json` cleaned: 97 outdated tool counts fixed,
  488 AgentDB references stripped, stale SSD paths updated
- SELinux relabeling: 14 scripts in `scripts/` restored to correct context
- Eicar test files removed from quarantine (chattr -i + rm)
- npm audit reduced from 7 to 3 vulnerabilities (remaining are upstream)

**RAG & indexing:**
- Full RAG re-ingestion: docs, code index, and logs refreshed
- Code search index built for `code.rag_query` (354 files, 1046 chunks)

**Documentation:**
- USER-GUIDE.md: system.* tool count corrected (13 → 15)
- `.opencode/AGENTS.md`: removed stale file reference
- AGENT.md: Known Active Issues updated to reflect current state

**Final metrics:**
- Tests: 1111 passed, 57 skipped, 0 failures
- MCP tools: 43 (+ 1 health)
- Systemd timers: 12
- Cloud providers: 6
- Threat intel APIs: 16

---

## Phase 7 — Stabilization, OpenCode Integration, GPU Optimization

**Phase 7A — Emergency Stabilization:**
- Added systemd unit files for memory freeze prevention: `btrfs-readahead-tune.service`,
  `configs/earlyoom`, `configs/90-bazzite-oomd.conf`, `configs/90-oomd-protect-user-slice.conf`
- Added `configs/90-bazzite-vm.conf` to reduce dirty_ratio from 20% to 10%
- Added `configs/kwin-nvidia.sh` to mitigate KDE/NVIDIA fd-leak (NVIDIA bug 5556719)
- Capped `bazzite-llm-proxy.service` and `bazzite-mcp-bridge.service` at MemoryMax=150M
- Updated external SSD path from `/run/media/lch/SteamLibrary` to `/var/mnt/ext-ssd`

**Phase 7A.3 — Cloud Embeddings Migration:**
- Rewrote `ai/rag/embedder.py`: Gemini Embedding 001 primary → Cohere fallback → Ollama emergency
- Gemini Embedding 001 (768-dim Matryoshka, free 10M TPM) — permanently frees ~300MB VRAM
- Added `gemini_embed` rate limit config to `configs/ai-rate-limits.json` (1500 rpm, 10K rpd, 10M tpm)
- Added `scripts/migrate-embeddings.sh` for one-time re-ingestion of all LanceDB tables
- Ollama `keep_alive=60` added — model unloads after 60s idle (emergency fallback only)

**Phase 7A.4 — Active Task Priority:**
- Updated "Gaming ALWAYS takes priority" to "active workload takes priority" in all docs
- Resource control now managed via systemd slices and GameMode hooks (Phase B manual step)

**Phase 7B.1 — LLM Proxy Multi-Turn Fix:**
- Added `route_chat(task_type, messages)` to `ai/router.py` — passes full message array
- Fixed non-streaming path in `ai/llm_proxy.py` to use `route_chat` (was sending only last message)

**Phase 7B.2-3 — OpenCode Integration:**
- Created `opencode.json` pointing at local LLM proxy (http://127.0.0.1:8767/v1, streaming:false)
- Added `scripts/mcp-stdio-bridge.sh` — stdio-to-HTTP shim for OpenCode → bazzite MCP bridge
- Created `.opencode/plugins/guard-destructive.js` — blocks rm -rf, git reset --hard, systemctl, rpm-ostree
- Updated `.opencode/dcp.json` with plan strategy settings and protectedSystemMessages:true
- Updated `.opencode/vibeguard.json` with clean pattern names (deterministic:true)

**Phase 7B.4 — LiteLLM Disk Cache:**
- Extended `ai/router.py` disk cache: prefer `/var/mnt/ext-ssd/bazzite-ai/llm-cache` over internal SSD
- Added per-task-type TTL: fast=5m, reason=30m, code=1h, batch=24h

**Phase 7B.5 — RuFlo Sidecar:**
- Created `configs/ruflo-sidecar.json` for manual dev session configuration
- Added RuFlo MCP entry to `opencode.json` (on-demand only, never auto-start via systemd)

**Phase 7C.2 — GPU Health MCP Tools (43 tools total):**
- Added `system.gpu_perf` — GPU perf snapshot via nvidia-smi
- Added `system.gpu_health` — throttle bit decoding + thermal headroom warning (notify-send at 8°C)
- Updated MCP bridge tool count to 43 in server.py, all tests, all docs

---

## Phase 6 Amendment — Package Intelligence + Release Watching + Fedora Updates

**Modules added:**
- `ai/system/release_watch.py` — GitHub Releases + GHSA watcher for tracked
  dependencies; writes `~/security/release-watch.json`
- `ai/system/fedora_updates.py` — Fedora Bodhi polling for pending security
  and package updates; writes `~/security/fedora-updates.json`
- `ai/system/pkg_intel.py` — deps.dev package intelligence (advisories,
  provenance, version status) exposed as `system.pkg_intel` MCP tool

**Timers added:**
- `systemd/release-watch.timer` — daily release watch check
- `systemd/fedora-updates.timer` — daily Fedora Bodhi update check

**MCP tools added:** `system.release_watch`, `system.fedora_updates`,
`system.pkg_intel`

**APIs integrated (no-signup):** GitHub Releases, GitHub GHSA, Fedora Bodhi,
deps.dev

**Total after this phase:** 41 MCP tools, 12 timers

---

## Phase 6 — Advanced Threat Intelligence

**Modules added:**
- `ai/threat_intel/ip_lookup.py` — IP reputation via AbuseIPDB + GreyNoise +
  Shodan InternetDB; exposes `security.ip_lookup`
- `ai/threat_intel/ioc_lookup.py` — URL/IOC lookup via URLhaus + ThreatFox +
  CIRCL Hashlookup; exposes `security.url_lookup`
- `ai/threat_intel/cve_scanner.py` — CVE scanner for installed packages using
  NVD + OSV (Google) + CISA KEV overlay; exposes `security.cve_check`
- `ai/threat_intel/sandbox.py` — Hybrid Analysis sandbox file submission;
  exposes `security.sandbox_submit`
- `ai/threat_intel/summary.py` — compiles threat summary across all agent/scan
  report directories; exposes `security.threat_summary`

**RAG enhancement:** Cohere rerank integrated into `ai/rag/embedder.py` for
improved RAG QA relevance; falls back gracefully when Cohere key is absent.

**Timers added:**
- `systemd/cve-scanner.timer` — weekly CVE scan of installed packages

**MCP tools added:** `security.ip_lookup`, `security.url_lookup`,
`security.cve_check`, `security.sandbox_submit`, `security.threat_summary`

**APIs integrated:** AbuseIPDB, GreyNoise, Shodan InternetDB, NVD/NIST,
OSV (Google), CISA KEV feed, Hybrid Analysis, URLhaus, ThreatFox,
CIRCL Hashlookup

**Rate limits added** to `configs/ai-rate-limits.json`: all Phase 6 providers

---

## Phase 5 — Storage Optimization, Caching, Key Management, and Polish

**Storage & performance:**
- LanceDB symlinked to external SSD (`~/security/vector-db/` → SteamLibrary
  partition) to reduce internal SSD I/O contention with ZRAM swap
- LiteLLM disk cache added to `ai/router.py` (exact-match, zero overhead on
  miss); requires `diskcache` package
- R2 log archiving: `scripts/archive-logs-r2.py` + `systemd/log-archive.timer`
  (weekly Sunday 01:00, compresses and uploads logs >7 days old to Cloudflare R2)

**Key management:**
- `ai/key_manager.py` — checks API key presence, writes
  `~/security/key-status.json` (never exposes values)
- `tray/keys_tab.py` — read-only Keys tab added to the PySide6 dashboard
- `system.key_status` MCP tool (json_file source, reads key-status.json)

**LLM observability:**
- Token usage tracking added to `ai/router.py`
- `system.llm_status` MCP tool — provider health, token usage, active models
- `auth_broken` flag added to `ai/health.py` for permanent auth failures

**Conversation memory (opt-in):**
- `ai/rag/memory.py` — LanceDB conversation memory table
- Enabled via `ENABLE_CONVERSATION_MEMORY=true`; off by default

**MCP tools added:** `system.llm_status`, `system.key_status`, `system.mcp_manifest`,
`knowledge.rag_qa`, `code.search`, `code.rag_query`

**Configs added:** `configs/r2-config.yaml`

**Bug fixes:**
- `health-latest.log` symlink: `_read_file_tail` now skips empty and symlinked
  files after logrotate
- MCP manifest truncation: increased output limit to 8192 for `system.mcp_manifest`
- `security_logs` 0 rows: `ingest_scans` connected to RAG store

---

## Phase 4 — Agents, Timers, and Newelle Integration

**Agents subsystem (`ai/agents/`):**
- `security_audit.py` — automated scan + health + ingest + RAG summary
- `performance_tuning.py` — temps, memory, disk, gaming profile analysis
- `knowledge_storage.py` — vector DB health, ingestion freshness, disk
- `code_quality_agent.py` — ruff + bandit + git status report

**MCP tools added:** `agents.security_audit`, `agents.performance_tuning`,
`agents.knowledge_storage`, `agents.code_quality`

**Timers added:**
- `systemd/security-audit.timer` — scheduled security audit
- `systemd/performance-tuning.timer` — scheduled performance check
- `systemd/knowledge-storage.timer` — scheduled knowledge base health check

**Newelle integration:**
- `docs/newelle-system-prompt.md` — system prompt for Newelle with full tool
  routing table and safety rules
- `docs/morning-briefing-prompt.md` — daily morning briefing prompt
- `docs/newelle-skills/` — skill definitions for Newelle (security, dev,
  gaming, system)
- Token optimization: removed claude-flow tools from Newelle MCP config
  (~12k tokens/turn saved); health check batching protocol

---

## Phase 3 — Log Intelligence and Code Quality

**Log intelligence (`ai/log_intel/`):**
- `ingest.py` — log ingestion pipeline (ClamAV + health logs → LanceDB)
- `queries.py` — health trend, scan history, anomaly detection, semantic search,
  pipeline stats
- `anomalies.py` — anomaly detection with threshold tuning
- `chunker.py` — log line chunking for embedding

**Code quality (`ai/code_quality/`):**
- `runner.py` — ruff + bandit orchestration
- `analyzer.py` — AI-assisted code fix suggestions
- `formatter.py`, `models.py` — data models and output formatting

**MCP tools added:** `logs.health_trend`, `logs.scan_history`, `logs.anomalies`,
`logs.search`, `logs.stats`

**Timers added:**
- `systemd/rag-embed.timer` — periodic re-ingestion of logs into LanceDB

---

## Phase 2.5 — Cleanup and Consolidation

- Removed `ai/g4f_manager.py` (GPL v3, privacy risk)
- Removed `ai/mcp_bridge/claude_flow_proxy.py` and `:8768` proxy service
- Removed `systemd/claude-flow.service` and `systemd/agentdb-sleep-cycle.*`
- Removed 13 RuFlo plugins (~450 MB) — domain-specific, redundant orchestration
- Reduced MCP tool count from inflated estimate to actual verified count
- Documented `~/projects/Setup/` workspace removal; authoritative docs in `docs/`

---

## Phase 2 — RAG Pipeline

**RAG pipeline (`ai/rag/`):**
- `embedder.py` — `embed_texts()`, Ollama primary + Cohere fallback (768-dim
  vectors locked per ingestion run to avoid dimension mismatches)
- `store.py` — `VectorStore`: LanceDB tables `security_logs`, `threat_intel`,
  `docs`, `health_records`, `scan_records`
- `query.py` — `rag_query()`, `QueryResult` dataclass; `use_llm=False` for
  bridge calls (no cloud API from bridge process)
- `ingest_docs.py` — incremental chunking with dedup state file;
  `--force` clears stale entries
- `code_query.py` — code-specific RAG over indexed Python source

**MCP tools added:** `knowledge.rag_query`, `knowledge.ingest_docs`

**Infrastructure:**
- LanceDB at `~/security/vector-db/` (not in repo, backed up by backup.sh)
- Ollama `nomic-embed-text` (768-dim, ~300 MB VRAM) as primary embedding provider
- Mistral embedding as fallback when Ollama is down

---

## Phase 1 — Threat Intelligence

**Threat intel (`ai/threat_intel/`):**
- `lookup.py` — hash enrichment via VirusTotal, AlienVault OTX, MalwareBazaar
- `models.py` — `ThreatResult` dataclass, risk level enum
- `formatters.py` — human-readable threat report formatting
- `__main__.py` — CLI entry point (`python -m ai.threat_intel.lookup --hash`)

**MCP tools added:** `security.threat_lookup`

**Rate limits:** per-provider limits added to `configs/ai-rate-limits.json`
(VT: 4 rpm/500 rpd, OTX: 166 rpm, MalwareBazaar: unlimited)

---

## Phase 0 — Foundation

**Core infrastructure:**
- `ai/config.py` — paths, `APP_NAME`, scoped `load_keys()` (never loads all keys)
- `ai/router.py` — LiteLLM V2 Router with health-weighted provider selection;
  task types: `fast`, `reason`, `batch`, `code`, `embed`
- `ai/health.py` — provider health scoring (0.0–1.0); 5 consecutive failures →
  2 min cooldown with exponential backoff (max 10 min)
- `ai/llm_proxy.py` — Starlette/uvicorn OpenAI-compatible proxy on :8767 for
  Newelle; model name → task type mapping
- `ai/rate_limiter.py` — cross-script rate limiting with file locking + atomic
  writes; reads `configs/ai-rate-limits.json`
- `ai/mcp_bridge/server.py` — FastMCP streamable-http server on :8766;
  allowlist-driven, never imports `ai.router`
- `ai/mcp_bridge/tools.py` — `execute_tool()` dispatcher; sources: `command`,
  `file_tail`, `json_file`, `python`; 4 KB output cap; path redaction

**Secrets management:**
- `configs/keys.env.enc` — sops-encrypted API keys (in git, safe)
- `~/.config/bazzite-ai/keys.env` — plaintext keys (chmod 600, never in git)
- `~/.config/bazzite-ai/.sops.yaml` — sops encryption config

**Systemd user services:**
- `systemd/bazzite-mcp-bridge.service` — MCP bridge auto-start on login
- `systemd/bazzite-llm-proxy.service` — LLM proxy auto-start on login

**Cloud providers configured:** Gemini, Groq, Mistral, OpenRouter, z.ai,
Cerebras (health-weighted, hot-swappable via `configs/litellm-config.yaml`)

**Python venv:** `.venv/` managed by `uv`; never global pip installs

## Final Metrics (Phase 18 complete)

| Metric | Value |
|--------|-------|
| MCP tools | **48** (+ 1 built-in health endpoint) |
| Systemd timers | **15** |
| Cloud providers | **6** (Gemini, Groq, Mistral, OpenRouter, z.ai, Cerebras) |
| Threat intel APIs | **16** |
| Unit tests | **~1611** (1611 passed, 185 skipped) |
| AI layer LOC | **~10,000+** |
| Python packages | **125** in .venv/ (via requirements-ai.txt) |
| Embedding provider | Gemini Embedding 001 (cloud, free 10M TPM) |
| VRAM usage (normal) | **0 MB** (cloud embeddings, Ollama emergency only) |
| RAM overhead | **~275 MB** (services + burst) |
