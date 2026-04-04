# Bazzite AI Layer — Agent Reference
<!-- System: Acer Predator G3-571 | Bazzite 43 | Updated: 2026-04-03 -->

## Session Start

> **Before doing any work**, read `HANDOFF.md` in the project root for recent
> session context, open tasks, and what the last agent was working on.
>
> When ending a session, run `/save-handoff` to record what you did.

### OpenCode Autonomous Mode

> If you are OpenCode executing a P24–P28 phase prompt from `docs/phase-playbook-p24-p28.md`:
> 1. Read `HANDOFF.md` first — check which phase was last completed
> 2. Run the pre-flight prompt (OC-01, OC-10, OC-15, OC-19, or OC-23)
> 3. Execute prompts sequentially — do NOT skip ahead
> 4. After each file creation: run `ruff check` on the file immediately
> 5. If ruff reports E111/E117 indentation errors, fix with the Python replace
>    script documented in the playbook header
> 6. After each phase: run the full test suite and commit
> 7. End with `/save-handoff --tool opencode --summary "P2X complete: [details]"`
>
> **OpenCode constraints:**
> - You frequently introduce 5-space indentation — always verify with ruff
> - Use `.venv/bin/python`, never system Python 3.14
> - TUI mode only — `opencode run` fails with custom providers
> - No /feature-dev or /code-review plugins — prompts are self-contained
> - Manual handoff only — no SessionEnd hook

---

## System Identity

- **Machine**: Acer Predator G3-571 | Bazzite 43 (KDE6/Wayland)
- **User**: lch
- **CPU**: Intel i7-7700HQ (4c/8t) | **RAM**: 16 GB + ZRAM 7.7 GB (zstd, swappiness=180)
- **GPUs**: NVIDIA GTX 1060 Mobile 6 GB + Intel HD 630 (Hybrid mode)
- **Internal SSD**: 256 GB SK hynix (LUKS/btrfs)
- **External SSD**: 1.8 TB SanDisk at `/var/mnt/ext-ssd` (ext4, fstab)
- **NVIDIA Driver**: 580.95.05 | **CUDA**: 13.0
- **OS**: Immutable (Fedora Atomic). rpm-ostree for system, Flatpak for apps, Homebrew for user tools
- **Repo**: github.com:violentwave/bazzite-laptop.git (private, SSH)
- **AI code**: `~/projects/bazzite-laptop/ai/`
- **VRAM budget**: 0 MB normal operation (cloud embeddings). Ollama `nomic-embed-text` is emergency-only.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Newelle        │
                    │ (Flatpak GTK4)  │
                    │ AI Chat + Voice │
                    └────┬──────┬─────┘
                         │      │
              MCP tools  │      │  LLM calls
                         │      │
          ┌──────────────▼──┐ ┌─▼──────────────────┐
           │  MCP Bridge     │ │  LLM Proxy          │
            │  :8766 FastMCP  │ │  :8767 OpenAI-compat│
            │  52 tools       │ │  6 cloud providers  │
          └──┬──┬──┬──┬─────┘ └──┬──────────────────┘
             │  │  │  │          │
    ┌────────┘  │  │  └───┐     │  Health-weighted routing
    │           │  │      │     │
    ▼           ▼  ▼      ▼     ▼
┌────────┐ ┌─────┐┌────┐┌─────┐┌───────────────────────┐
│Threat  │ │ RAG ││Logs││Agent││ Gemini  Groq  Mistral  │
│Intel   │ │     ││    ││  s  ││ OpenRouter  z.ai       │
│6 mods  │ │Lance││    ││    ││ Cerebras                │
│        │ │DB   ││    ││    │└───────────────────────┘
└────────┘ └─────┘└────┘└─────┘

System Layer:
  ClamAV (3 timers) | Health (1 timer) | Agents (3 timers)
  RAG embed (1 timer) | CVE/Release/Fedora (3 timers) | R2 archive (1 timer) | Canary (1 timer)
  LanceDB → ext-ssd | Disk cache → ext-ssd | Tray app (PySide6)
```

| Port  | Service    | Protocol               | Binds to       |
|-------|------------|------------------------|----------------|
| 8766  | MCP Bridge | FastMCP streamable-http | 127.0.0.1 only |
| 8767  | LLM Proxy  | OpenAI-compatible REST  | 127.0.0.1 only |
| 11434 | Ollama     | Ollama API (embed only) | 127.0.0.1 only |

Both MCP Bridge and LLM Proxy auto-start on login as systemd user services.
Key constraints:
- Bridge **NEVER** imports `ai.router` (scoped key loading)
- Both services refuse to bind to 0.0.0.0
- All subprocess commands are static lists (no `shell=True`)
- Output truncated to 4 KB, paths redacted

---

## MCP Tools (53 + health)

Source: `configs/mcp-bridge-allowlist.yaml` (53 entries).

> **Phase 12:** PingMiddleware (25s keepalive) active. All 50 tools carry MCP annotations (readOnly/destructive/openWorld hints).
> **Phase 20:** Added `agents.timer_health` — validates all 16 systemd timers.
> **Phase 21:** Added `knowledge.pattern_search` — semantic search over curated code patterns.
> **Phase 22:** Added `knowledge.task_patterns` — retrieve similar past successful tasks.
> **Phase 23:** Added `system.budget_status` — token budget usage across tiers.
> **Phase 24:** Added `system.metrics_summary` — aggregate metrics for last 24h.

### system.* (20 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `system.disk_usage` | command: `df -h` | — | Disk usage for all mounted filesystems |
| `system.cpu_temps` | command: `sensors -j` | — | CPU core and sensor temperatures (JSON) |
| `system.gpu_status` | command: `nvidia-smi` | — | GPU temp, VRAM, power, fan speed |
| `system.gpu_perf` | python | — | GPU perf snapshot: pstate, clocks, throttle reasons, headroom |
| `system.gpu_health` | python | — | GPU health diagnostic with throttle bit interpretation |
| `system.memory_usage` | command: `free -h` | — | System RAM + ZRAM usage |
| `system.uptime` | command: `uptime` | — | System uptime and load average |
| `system.service_status` | command: `systemctl show` | — | Status of 4 key services |
| `system.llm_status` | json_file: `~/security/llm-status.json` | — | Provider health, token usage, active models |
| `system.key_status` | json_file: `~/security/key-status.json` | — | API key presence (never values) |
| `system.llm_models` | python | — | Available LLM task types + provider chains |
| `system.mcp_manifest` | python | — | All tools with descriptions and args |
| `system.release_watch` | json_file: `~/security/release-watch.json` | — | Upstream release updates (GitHub, GHSA) |
| `system.fedora_updates` | json_file: `~/security/fedora-updates.json` | — | Fedora/Bazzite pending updates (Bodhi) |
| `system.pkg_intel` | python: `ai.system.pkg_intel` | — | Package advisories via deps.dev |
| `system.cache_stats` | python: `ai.cache` | — | LLM cache statistics: entries, size, hit rate |
| `system.token_report` | python: `ai.mcp_bridge.tools` | — | Token usage and cost report from LLM proxy |
| `system.pipeline_status` | python: `ai.system.pipeline_status` | — | Log pipeline ingest/archive/retention status, pending files, table row counts |
| `system.budget_status` | python: `ai.mcp_bridge.server` | — | Daily token budget usage and warnings across priority tiers |
| `system.metrics_summary` | python: `ai.metrics` | `hours`, `metric_type` | Aggregate metrics for last 24h: cache hit rates, provider latencies, budget usage, tool errors |

### security.* (14 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `security.status` | json_file: `~/security/.status` | — | Filtered status JSON (6 keys) |
| `security.last_scan` | file_tail: `/var/log/clamav-scans/` | — | Last 20 lines of latest ClamAV log |
| `security.health_snapshot` | file_tail: `/var/log/system-health/` | — | Last 30 lines of latest health log |
| `security.threat_lookup` | python: `ai.threat_intel.lookup` | `hash` (hex, 32-64 chars, required) | Hash lookup (VT + OTX + MalwareBazaar) |
| `security.ip_lookup` | python: `ai.threat_intel.ip_lookup` | `ip` (IPv4/IPv6, required) | IP reputation (AbuseIPDB + GreyNoise + Shodan) |
| `security.url_lookup` | python: `ai.threat_intel.ioc_lookup` | `url` (string, required) | URL/IOC lookup (URLhaus + ThreatFox + CIRCL) |
| `security.cve_check` | python: `ai.threat_intel.cve_scanner` | — | CVE scan (NVD + OSV + CISA KEV) |
| `security.sandbox_submit` | python: `ai.threat_intel.sandbox` | `file_path` (under `quarantine/`, required) | Submit quarantine file to Hybrid Analysis |
| `security.threat_summary` | python: `ai.threat_intel.summary` | — | Compile summary from all report dirs |
| `security.run_scan` | python | `scan_type` (`"quick"` or `"deep"`, optional) | Trigger ClamAV scan via systemctl |
| `security.run_health` | python | — | Trigger health snapshot via systemctl |
| `security.run_ingest` | python | — | Trigger log pipeline re-ingestion |
| `security.correlate` | python: `ai.threat_intel.correlator` | `ioc`, `ioc_type` (required) | Correlate IOC across VT/OTX/AbuseIPDB/GreyNoise/URLhaus |
| `security.recommend_action` | python: `ai.threat_intel.playbooks` | `finding_type`, `finding_id` (required) | Response playbook for threat findings |

### knowledge.* (5 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `knowledge.rag_query` | python: `ai.rag.query` | `query` (string, max 500, required) | Semantic search — raw context chunks (no LLM) |
| `knowledge.rag_qa` | python: `ai.rag.query` | `question` (string, max 500, required) | LLM-synthesized answer from knowledge base |
| `knowledge.ingest_docs` | python: `ai.rag.ingest_docs` | — | Re-embed docs/ into LanceDB |
| `knowledge.pattern_search` | python: `ai.rag.pattern_query` | `query` (string, max 500, required), `language` (optional), `domain` (optional) | Semantic search over curated code patterns with language/domain filtering |
| `knowledge.task_patterns` | python: `ai.mcp_bridge.server` | `query` (string, max 500, required), `top_k` (int, default 3) | Retrieve similar past successful tasks by semantic similarity |

### gaming.* (2 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `gaming.profiles` | python: `ai.gaming.scopebuddy` | — | List configured game profiles |
| `gaming.mangohud_preset` | python: `ai.gaming.scopebuddy` | `game` (string, required) | MangoHud preset for a game |

### logs.* (5 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `logs.health_trend` | python: `ai.log_intel` | — | Last 7 health snapshots with deltas |
| `logs.scan_history` | python: `ai.log_intel` | — | Last 10 ClamAV scan results |
| `logs.anomalies` | python: `ai.log_intel` | — | Unacknowledged anomalies |
| `logs.search` | python: `ai.log_intel` | `query` (string, max 500, required) | Semantic search across system logs |
| `logs.stats` | python: `ai.log_intel` | — | Log pipeline statistics |

### code.* (2 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `code.search` | python: ripgrep | `query` (string, max 128, required) | Pattern search across Python source |
| `code.rag_query` | python: `ai.rag.code_query` | `question` (string, max 500, required) | Semantic search over indexed code |

### agents.* (5 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `agents.security_audit` | python: `ai.agents.security_audit` | — | Scan + health + ingest + RAG summary |
| `agents.performance_tuning` | python: `ai.agents.performance_tuning` | — | Temps, memory, disk, gaming profiles |
| `agents.knowledge_storage` | python: `ai.agents.knowledge_storage` | — | Vector DB health + embedding provider status |
| `agents.code_quality` | python: `ai.agents.code_quality_agent` | — | ruff + bandit + git status |
| `agents.timer_health` | python: `ai.agents.timer_sentinel` | — | Validate all 16 systemd timers fired within expected windows. Returns per-timer status, stale list, and overall health (healthy/warning/critical). |

### Built-in

| Tool | Description |
|------|-------------|
| `health` | Returns `{"status": "ok", "tools": 52}` |

---

## P24–P28 Roadmap (Active Development)

> **Execution agent:** OpenCode (z.ai GLM models, TUI mode)
> **Playbook:** `docs/phase-playbook-p24-p28.md` (30 numbered prompts: OC-01 through OC-30)
> **Execution order:** P24 → P25 → P26 → P27 → P28 (sequential, P24 is foundational)

| Phase | Name | New Tool | New Timer | New LanceDB Table | Key Module |
|-------|------|----------|-----------|-------------------|------------|
| **P24** | Observability & Metrics | `system.metrics_summary` | `metrics-compact.timer` (Sun 03:00) | `metrics` | `ai/metrics.py` |
| **P25** | Conversation Memory | `memory.search` | — | `conversation_memory` | `ai/memory.py` |
| **P25** | Conversation Memory | `memory.search` | — | `conversation_memory` | `ai/memory.py` |
| **P26** | Provider Intelligence | `system.provider_status` | — | — | `ai/provider_intel.py` |
| **P27** | Security Alerting | `security.alert_summary` | `security-alert.timer` (every 6h) | — | `ai/security/alerts.py` |
| **P28** | Self-Improvement Loop | `system.weekly_insights` | `weekly-insights.timer` (Mon 09:00) | `system_insights` | `ai/insights.py` |

### Target State After P28

| Metric | Current (P23) | Target (P24) | Target (P28) |
|--------|---------------|--------------|--------------|
| MCP tools | 52 | 53 (+1) | 57 (+5) |
| Timers | 16 | 17 (+1) | 19 (+3) |
| LanceDB tables | 10 | 11 (+1) | 13 (+3) |
| Tests | ~1604 | ~1610 | ~1650+ |

### Dependency Graph

```
P24 (Observability) ← foundational — P26 and P28 read its data
P25 (Memory) ← independent, extends RAG embeddings
P26 (Provider Intel) ← requires P24 metrics
P27 (Security Alerts) ← independent, uses existing threat intel
P28 (Self-Improvement) ← aggregates P24 + P25 + P26 + P27
```

### Phase Implementation Rules (OpenCode)

1. **One phase at a time** — complete and commit before starting the next
2. **Pre-flight every phase** — verify git clean, tests passing, ruff clean
3. **Context7 before LanceDB code** — API patterns change between versions
4. **ruff check after every file** — catch 5-space indentation immediately
5. **Never modify ai/router.py and ai/mcp_bridge/ in the same prompt**
6. **Always run full test suite** at end of phase, not just new tests
7. **Update AGENT.md + CHANGELOG.md** counts at the end of every phase
8. **Wrap metric/memory calls in try/except** — observability must never break core flow
9. **Atomic writes** for all JSON output files (tmp + os.rename)
10. **Secret redaction** via ai.security.inputvalidator before storing user text

---

## LLM Provider Chain

| Type | Use Case | Provider Chain |
|------|----------|----------------|
| `fast` | Interactive chat | Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras |
| `reason` | Deep analysis | Gemini → Groq → Mistral → OpenRouter(Claude) → z.ai |
| `batch` | Volume processing | Gemini → Groq → Mistral → OpenRouter → Cerebras |
| `code` | Code-specialized | Gemini → Groq → Mistral(Codestral) → OpenRouter(Claude) → z.ai |
| `embed` | Embeddings | Gemini Embedding 001 → Cohere → Ollama (emergency) |

**Model name mapping** (what Newelle sends → task type): `model="fast"` → `fast` chain, `model="reason"` → `reason` chain, etc.

**Health tracking**: 5 consecutive failures → 2 min cooldown → exponential backoff → 10 min max. Providers auto-recover when health improves.

**Stream recovery**: 2 KB commit threshold. Pre-commit failure → retry next provider. Post-commit → fatal (partial output already sent).

**Cloud providers (6)**:

| Provider | Key Var | Task Types |
|----------|---------|-----------|
| Google Gemini | `GEMINI_API_KEY` | fast, reason, batch, code, embed |
| Groq | `GROQ_API_KEY` | fast, reason, batch, code |
| Mistral | `MISTRAL_API_KEY` | fast, reason, batch, code, embed |
| OpenRouter | `OPENROUTER_API_KEY` | fast, reason, batch, code |
| z.ai | `ZAI_API_KEY` | fast, reason, code |
| Cerebras | `CEREBRAS_API_KEY` | fast, batch |
| Ollama (local) | — | embed emergency fallback only |

---

## Systemd Timers (17)

| Timer | Schedule | Purpose |
|-------|----------|---------|
| `log-ingest.timer` | Sun 0:30 | Weekly log ingestion before archive |
| `system-health.timer` | Daily 8:00 | Hardware health snapshot |
| `security-briefing.timer` | Daily 8:45 | Headless daily security briefing → ~/security/briefings/ |
| `clamav-quick.timer` | Daily 12:00 | ClamAV quick scan |
| `clamav-deep.timer` | Fri 23:00 | ClamAV full scan |
| `clamav-healthcheck.timer` | Wed 14:00 | ClamAV daemon check |
| `rag-embed.timer` | Daily 9:00 | Re-ingest logs into LanceDB |
| `security-audit.timer` | Daily 8:30 | Automated security audit |
| `performance-tuning.timer` | Daily 8:15 | Performance analysis |
| `knowledge-storage.timer` | Daily 9:15 | Knowledge base health check |
| `cve-scanner.timer` | Sat 0:00 | CVE scan of installed packages |
| `release-watch.timer` | Daily 9:45 | GitHub Releases + GHSA watcher |
| `fedora-updates.timer` | Mon 3:00 | Fedora Bodhi update check |
| `log-archive.timer` | Sun 1:00 | Upload old logs to Cloudflare R2 |
| `service-canary.timer` | Every 15m | AI service health check + auto-restart |
| `lancedb-optimize.timer` | Sun 2:00 | Compact and optimize LanceDB tables |
| `metrics-compact.timer` | Sun 3:00 | Compact and prune old metrics data |

---

## Critical Rules — NEVER Violate

1. **No PRIME offload env vars** (`__NV_PRIME_RENDER_OFFLOAD`, `__GLX_VENDOR_LIBRARY_NAME`, `prime-run`) — crashes Proton/Vulkan on GTX 1060 + Intel HD 630 with `nvidia-drm.modeset=1`
2. **No lowering `vm.swappiness`** below 180 — required for ZRAM (intentionally high)
3. **No `nvidia-xconfig`** — doesn't exist on immutable filesystem
4. **No `supergfxctl -m Dedicated`** — only Integrated and Hybrid modes exist on this hardware
5. **No ProtonUp-Qt** — use ProtonPlus (or `ujust`) instead
6. **No local LLM generation** — Ollama `nomic-embed-text` is emergency embed fallback only; Gemini Embedding 001 is primary
7. **No API keys in code, scripts, or git** — runtime-only via `keys.env`
8. **No `ai.router` import inside `ai/mcp_bridge/`** — bridge must use scoped key loading
9. **No `shell=True` in subprocess** — all commands are static argument lists
10. **No writes to `~/security/.status` without read-modify-write + atomic rename** — shared by ClamAV, health, and tray
11. **No global pip installs** — `uv` + `.venv/` only
12. **No `/usr` modifications** — immutable OS (Fedora Atomic); use `rpm-ostree install`
13. **No `--break-system-packages`** — Python packages go in `.venv/` only
14. **All LLM calls through `ai/router.py`** — all API calls through `ai/rate_limiter.py`
15. **`restorecon` after every systemd unit install** — SELinux label restoration required

---

## Key Paths

### Repository paths

| Path | Purpose |
|------|---------|
| `ai/config.py` | Paths, constants, scoped key loading |
| `ai/router.py` | LiteLLM V2 router, health-weighted provider selection |
| `ai/health.py` | Provider health scoring + auto-demotion |
| `ai/llm_proxy.py` | OpenAI-compatible proxy on :8767 |
| `ai/rate_limiter.py` | Cross-script rate limiting with file locking |
| `ai/key_manager.py` | API key presence checker |
| `ai/mcp_bridge/server.py` | FastMCP server on :8766, tool registration |
| `ai/mcp_bridge/tools.py` | Tool dispatch handlers for all 52 tools |
| `ai/threat_intel/` | VT, OTX, AbuseIPDB, GreyNoise, NVD, URLhaus, etc. (6 API modules) |
| `ai/rag/` | LanceDB store, embedder, query engine, code query |
| `ai/log_intel/` | Log ingestion, anomaly detection, semantic search |
| `ai/agents/` | Automated agents (5): security, perf, knowledge, code quality, timer sentinel |
| `ai/gaming/` | MangoHud analysis, ScopeBuddy profiles |
| `ai/cache_semantic.py` | SemanticCache: LanceDB-backed similarity cache with TTL (P23) |
| `ai/budget.py` | TokenBudget: daily token limits with priority tiers (P23) |
| `ai/metrics.py` | MetricsRecorder: time-series observability with buffered writes (P24) |
| `ai/security/inputvalidator.py` | Pre-dispatch input validation + secret redaction |
| `ai/system/` | release_watch, fedora_updates, pkg_intel |
| `configs/mcp-bridge-allowlist.yaml` | 53 tool definitions + argument validation |
| `configs/safety-rules.json` | Input validation rules (max length, patterns, path allowlists) |
| `configs/litellm-config.yaml` | LiteLLM provider routing config |
| `configs/ai-rate-limits.json` | Per-provider rate limits |
| `configs/keys.env.enc` | sops-encrypted API keys (in git, safe) |
| `scripts/` | 42 shell/Python scripts (deploy, scan, backup, etc.) |
| `scripts/lancedb-prune.py` | LanceDB retention pruning (90d logs, 180d threats) + cache cleanup |
| `scripts/metrics-compact.py` | Metrics compaction (P24) |
| `scripts/r2-set-lifecycle.py` | One-time R2 bucket lifecycle rule setup (180d auto-expiration) |
| `scripts/log-task-success.py` | CLI for logging successful task patterns to LanceDB (P22) |
| `systemd/` | 16 timers + associated services |
| `tests/` | 1604 pytest tests |
| `tray/` | PySide6 system tray app |
| `docs/phase-playbook-p24-p28.md` | OpenCode autonomous execution playbook (OC-01 through OC-30) |

### Runtime paths (not in repo)

| Path | Purpose |
|------|---------|
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys (chmod 600, never in git) |
| `~/security/` | Canonical root for all runtime security data |
| `~/security/.status` | Shared JSON: ClamAV + health state (tray + MCP read this) |
| `~/security/vector-db/` | LanceDB root (→ `/var/mnt/ext-ssd/bazzite-ai/vector-db`). Tables: `documents` (RAG docs), `code_index` (code embeddings), `log_entries` (system logs), `code_patterns` (curated code patterns — P21), `task_patterns` (task outcomes — P22), `semantic_cache` (LLM response cache — P23), `metrics` (observability time-series — P24) |
| `~/security/vector-db/.archive-state.json` | R2 archive state (upload records with key, timestamp, size) |
| `~/security/llm-status.json` | LLM provider health + token usage |
| `~/security/key-status.json` | API key presence map |
| `~/security/release-watch.json` | Release watch results |
| `~/security/fedora-updates.json` | Fedora update check results |
| `~/security/quarantine/` | ClamAV quarantine directory |
| `/var/log/system-health/` | Health snapshot logs |
| `/var/log/clamav-scans/` | ClamAV scan logs |
| `/var/mnt/ext-ssd/bazzite-ai/llm-cache` | LiteLLM disk cache |

### P24–P28 planned paths (created during implementation)

| Path | Phase | Purpose |
|------|-------|---------|
| `ai/metrics.py` | P24 | MetricsRecorder with buffered LanceDB writes |
| `ai/memory.py` | P25 | ConversationMemory with semantic retrieval |
| `ai/provider_intel.py` | P26 | ProviderIntel scoring for dynamic routing |
| `ai/security/alerts.py` | P27 | SecurityAlertEvaluator for proactive alerting |
| `ai/insights.py` | P28 | InsightGenerator for weekly self-assessment |
| `scripts/metrics-compact.py` | P24 | Weekly metrics compaction |
| `scripts/security-alert-eval.py` | P27 | Security alert evaluation |
| `scripts/generate-weekly-insights.py` | P28 | Weekly insights generation |
| `~/security/alerts.json` | P27 | Active security alerts (runtime) |
| `~/security/.alert-dedup.json` | P27 | Alert deduplication state (runtime) |

---

## Build & Test

```bash
source .venv/bin/activate
python -m pytest tests/ -v          # 1604 tests
ruff check ai/ tests/               # Lint
bandit -r ai/ -c pyproject.toml     # Security scan
uv pip install -r requirements.txt  # Install/update deps
```

---

## Dependencies

> Full version details: see `docs/verified-deps.md`

**Python 3.12** in `.venv/` managed by `uv`. Key packages: litellm (multi-provider routing), lancedb (vector DB), fastmcp (MCP server), pydantic, httpx, requests, cohere (rerank), boto3 (R2 archiving), pillow. LLM response cache: `ai/cache.py` (JsonFileCache, zero-dep, no pickle).

**Node.js v25** for RuFlo orchestration CLI (`@claude-flow/cli` v3.5.15) + 2 plugins (code-intelligence, test-intelligence).

**System tools** (rpm-ostree): ruff, bandit, shellcheck, gpg, sops, ollama.

---

## Dual-Agent Workflow

### Claude Code (primary implementation)

- Sandbox mode always on (bubblewrap)
- Settings: `~/.claude/settings.json`
- **Can**: edit files, git, pytest, ruff, bandit, curl/wget, uv, gpg, sops, `python -m ai.*`
- **Cannot**: sudo, systemctl, rpm-ostree, `rm -rf`, read `*.env`/`*.key`/`*.pem`, write to `/usr` or `/etc`
- Plugins: code-review, context7, code-simplifier, coderabbit, huggingface-skills
- RuFlo MCP: global scope in `~/.claude/settings.json`

### OpenCode (audits, targeted edits, P24–P28 autonomous execution)

- Provider: z.ai GLM models (direct, not through local proxy)
- Config: `~/.config/opencode/opencode.jsonc` (not in git)
- Instructions: `.opencode/AGENTS.md`
- RuFlo MCP: global scope, `/home/linuxbrew/.linuxbrew/bin/ruflo`
- **P24–P28 playbook**: `docs/phase-playbook-p24-p28.md`
- **Known issue**: 5-space indentation in multi-line Python edits — always run `ruff check` after edits
- **Known issue**: May install to system Python 3.14 — always use `.venv/bin/python`

### Two-phase workflow (system-level changes only)

- **Phase A**: Agent creates/edits files + runs approved tools (most work happens here)
- **Phase B**: User manually runs `sudo`/`systemctl` commands in terminal (deploy, integration tests)

---

## Cross-Tool Handoff System

Agents working on this project share context via `HANDOFF.md` in the project root.

- **`~/.local/bin/save-handoff.sh`** — project-aware, creates/updates `$PROJECT_ROOT/HANDOFF.md`
  - `--tool <claude-code|opencode|gemini>` — identifies the writing agent
  - `--summary "text"` — records what was done
  - `--task "desc"` — adds an open task
  - `--done "desc"` — marks a task as complete
- **`/save-handoff`** slash command in both Claude Code and OpenCode
- **Claude Code auto-saves** on session end via `SessionEnd` hook in `~/.claude/settings.json`
- **OpenCode requires manual** `/save-handoff` — no hook support
- **`~/.local/bin/handoff-status.sh`** — viewer (aliases: `handoff`, `handoff-all`)
- **Global index**: `~/.local/share/handoff/recent-projects.json`
- Each project gets its own `HANDOFF.md` — no cross-project bleed

---

## Newelle Integration

Newelle (Flatpak GTK4) is the AI chat/voice UI for this system.

- **LLM**: `http://127.0.0.1:8767/v1/` (`model="fast"`)
- **MCP**: `http://127.0.0.1:8766/mcp` (49 tools)
- **System prompt**: `docs/newelle-system-prompt.md`
- **Skills**: `docs/newelle-skills/` — 5 bundles: security, system, dev, gaming, agents
- **Morning briefing**: `docs/morning-briefing-prompt.md` (scheduled 9:30 AM)
- **Wrapper scripts**: `scripts/newelle-exec.sh` (venv activation), `scripts/newelle-sudo.sh` (allowlisted sudo)

---

## What This Project Does NOT Cover

The base security/gaming system is managed in the "Bazzite Laptop" Claude.ai project:
- ClamAV scanning, quarantine, email alerts (base behavior)
- USBGuard, firewalld, SELinux configuration
- System health monitoring scripts (base behavior)
- GPU/display configuration, gaming setup, launch options
- Systemd service hardening, KDE Security menu structure
- Backup/restore procedures, LUKS encryption
- Browser hardening, service optimization

---

## Software NOT to Use

| Software | Why Skip |
|----------|----------|
| **Local LLM generation** (Qwen, DeepSeek, etc.) | 3-8 tok/s on GTX 1060 is unusable. Monopolizes VRAM. |
| **ChromaDB** | HNSW index lives in RAM. LanceDB (disk-based) is better for 16 GB. |
| **g4f** | GPL v3, routes through unknown third-party proxies, privacy risk. |
| **Puter.js** | Third-party proxy, no SLA. |
| **DuckDuckGo AI wrappers** | Reverse-engineered unofficial APIs. |
| **SonarQube** | 2-4 GB RAM + Elasticsearch. Too heavy. |
| **Wazuh** | Full SIEM needing 4-8 GB RAM. |
| **n8n** | Docker overhead on gaming laptop; systemd timers handle all scheduling. |
| **Qdrant** | Already have LanceDB; third data store increases maintenance. |
| **LangChain/LangGraph** | 50MB deps for patterns implementable in 100 LOC. |

---

## Known Active Issues

1. **Eicar test files stuck in quarantine** — chattr +i set, needs `sudo chattr -i` + `rm` to clean up
2. **npm audit: 30 remaining vulns** — path-to-regexp (high), brace-expansion (moderate) in RuFlo orchestrator deps (not fixable without upstream changes)
3. **CPU 87°C idle** — needs repaste with Kryonaut Extreme (thermal compound degradation)
4. **Legacy AgentDB skill dirs** — `.claude/skills/agentdb-*` and `.claude/skills/reasoningbank-agentdb` are read-only in sandbox; delete manually outside Claude Code
5. **requirements.txt contains system packages** — Brlapi, cockpit, etc. break venv rebuilds; use `requirements-ai.txt` instead (`uv pip install -r requirements-ai.txt`)
