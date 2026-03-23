# Changelog — Bazzite AI Enhancement Layer
<!-- System: Acer Predator G3-571 | Bazzite 43 | Last updated: 2026-03-22 -->

All notable changes are recorded here. Phases correspond to the original
implementation plan for the AI enhancement layer built on top of the base
Bazzite security/gaming system.

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
- `ai/health.py` — provider health scoring (0.0–1.0); 3 consecutive failures →
  5 min cooldown with exponential backoff (max 30 min)
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

---

## Final Metrics (Phase 6 Amendment complete)

| Metric | Value |
|--------|-------|
| MCP tools | **43** (+ 1 built-in health endpoint) |
| Systemd timers | **12** |
| Cloud providers | **6** (Gemini, Groq, Mistral, OpenRouter, z.ai, Cerebras) |
| Threat intel APIs | **16** |
| Unit tests | **998** (1 pre-existing failure in formatters — fix pending) |
| AI layer LOC | **~9,000+** |
| Python packages | **~34** in .venv/ |
| Embedding provider | Gemini Embedding 001 (cloud, free 10M TPM) |
| VRAM usage (normal) | **0 MB** (cloud embeddings, Ollama emergency only) |
| RAM overhead | **~275 MB** (services + burst) |
