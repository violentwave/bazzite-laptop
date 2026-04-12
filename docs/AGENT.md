# Bazzite AI Layer — Agent Reference
<!-- System: Acer Predator G3-571 | Bazzite 43 | Updated: 2026-04-09 -->

## Session Start

> **Before doing any work**, read `HANDOFF.md` in the project root for recent
> session context, open tasks, and what the last agent was working on.
>
> When ending a session, run `/save-handoff` to record what you did.

### OpenCode Autonomous Mode

> If you are OpenCode executing a phase prompt:
> 1. Read `HANDOFF.md` first — check which phase was last completed
> 2. Run the pre-flight (verify git clean, tests pass, ruff clean) before any work
> 3. Execute prompts sequentially — do NOT skip ahead
> 4. After each file creation: run `ruff check` on the file immediately
> 5. If ruff reports E111/E117 indentation errors, fix with the Python replace script
> 6. After each phase: run the full test suite and commit
> 7. End with `/save-handoff --tool opencode --summary "PXX complete: [details]"`
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
            ┌───────────▼──┐ ┌─▼──────────────────┐
              │  MCP Bridge  │ │  LLM Proxy          │
              │  :8766 FastMCP  │ │  :8767 OpenAI-compat│
               │  96 tools       │ │  6 cloud providers  │
            └──┬──┬──┬──┬─────┘ └──┬──────────────────┘
             │  │  │  │          │
    ┌────────┘  │  │  └───┐     │  Health-weighted routing
    │           │  │      │     │
    ▼           ▼  ▼      ▼     ▼
┌────────┐ ┌─────┐┌────┐┌──────────┐┌───────────────────────┐
│Threat  │ │ RAG ││Logs││Agents +  ││ Gemini  Groq  Mistral  │
│Intel   │ │     ││    ││Orchestra-││ OpenRouter  z.ai       │
│6 mods  │ │Lance││    ││tion Bus  ││ Cerebras                │
│        │ │DB   ││    ││5 agents  │└───────────────────────┘
└────────┘ └─────┘└────┘└──────────┘

System Layer:
  ClamAV (3 timers) | Health (1 timer) | Agents (3 timers)
  RAG embed (1 timer) | CVE/Release/Fedora (3 timers) | R2 archive (1 timer) | Canary (1 timer)
  Dep audit (1 timer) | Insights (1 timer) | Code index (1 timer) | Workflow health (1 timer)
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
- `ai/orchestration/` **NEVER** imports `ai.router`
- Both services refuse to bind to 0.0.0.0
- All subprocess commands are static lists (no `shell=True`)
- Output truncated to 4 KB, paths redacted

---

## MCP Tools (96)

Source: `configs/mcp-bridge-allowlist.yaml` + tools registered directly in server.py.

> **Phase 12:** PingMiddleware (25s keepalive) active. All tools carry MCP annotations (readOnly/destructive/openWorld hints).
> **Phase 52:** Added Slack (4 tools) and Notion (4 tools) integrations with scoped secret loading.
> **Phase 20:** Added `agents.timer_health` — validates all 21 systemd timers.
> **Phase 21:** Added `knowledge.pattern_search` — semantic search over curated code patterns.
> **Phase 22:** Added `knowledge.task_patterns` — retrieve similar past successful tasks.
> **Phase 23:** Added `system.budget_status` — token budget usage across tiers.
> **Phase 24:** Added `system.metrics_summary` — aggregate metrics for last 24h.
> **Phase 25:** Added `memory.search` — cross-session conversation memory retrieval.
> **Phase 26:** Added `system.provider_status` — per-provider health, latency, error rates.
> **Phase 27:** Added `security.alert_summary` — proactive security alerts (CVEs, stale scans, release advisories).
> **Phase 28:** Added `system.weekly_insights` — AI-generated weekly insights.
> **Phase 29:** Added `code.impact_analysis`, `code.dependency_graph`, `code.find_callers`, `code.suggest_tests`, `code.complexity_report`, `code.class_hierarchy` — structural code intelligence with AST parsing and grimp import graphs.
> **Phase 30:** Added `workflow.run`, `workflow.list` — workflow engine with ReAct loop and event triggers.
> **Phase 31:** Added `collab.queue_status`, `collab.add_task`, `collab.search_knowledge` — agent collaboration with task queue and knowledge base.
> **Phase 32:** Added test intelligence with flaky detection, selective execution (testmon), and test traceability.
> **Phase 33:** Added `system.create_tool`, `system.list_dynamic_tools` — dynamic tool creation with safety validation.
> **Phase 39:** Added `system.dep_audit`, `system.dep_audit_history` — pip-audit vulnerability scanning + SBOM generation.
> **Phase 40:** Added `system.perf_metrics` — real-time performance metrics snapshot.
> **Phase 52:** Added `slack.*` (4 tools) and `notion.*` (4 tools) with scoped secret loading.
> **Phase 53:** Expanded `workflow.*` with `workflow.status`, `workflow.agents`, `workflow.handoff`, and `workflow.history` (6 total) + `workflow_runs` LanceDB table.
> **Phase 65:** Added a frontend runtime harness and browser evidence loop so external React/Tailwind projects can be previewed locally and closed out with stable QA artifacts.

### system.* (33 tools)

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
| `system.pipeline_status` | python: `ai.system.pipeline_status` | — | Log pipeline ingest/archive/retention status |
| `system.budget_status` | python: `ai.budget` | — | Daily token budget usage and warnings across priority tiers |
| `system.metrics_summary` | python: `ai.metrics` | `hours`, `metric_type` | Aggregate metrics for last 24h |
| `system.weekly_insights` | python: `ai.insights` | `limit` (int, default 4) | Cached AI-generated weekly insights |
| `system.insights` | python: `ai.insights` | — | Generate on-demand AI layer insights |
| `system.provider_status` | python: `ai.provider_intel` | — | Per-provider health, latency, error rates, routing scores |
| `system.dep_audit` | python: `ai.system.depaudit` | — | Run pip-audit vulnerability scan |
| `system.dep_audit_history` | python: `ai.system.depaudit` | `limit` (int, default 30) | Historical dep-audit scan results |
| `system.create_tool` | python: `ai.tools.builder` | `name`, `description`, `handler_code`, `parameters`, `created_by` | Create a dynamic tool with safety validation |
| `system.list_dynamic_tools` | python: `ai.tools.builder` | — | List all persisted dynamic tools |
| `system.alert_history` | python: `ai.alerts.history` | `limit` (int, default 20) | Recent desktop alert dispatch history |
| `system.alert_rules` | python: `ai.alerts.rules` | — | List all alert rules with enabled/cooldown status |
| `system.dep_scan` | python: `ai.system.dep_scanner` | — | Scan .venv Python dependencies for known vulnerabilities via OSV API |
| `system.test_analysis` | python: `ai.system.test_analyzer` | `input` | Analyze pytest output for failure patterns |
| `system.perf_profile` | python: `ai.system.perf_profiler` | `skip` | Run performance profiler |
| `system.mcp_audit` | python: `ai.system.mcp_generator` | `tool_name` (optional) | Audit MCP bridge allowlist for missing handlers |

### security.* (15 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `security.status` | json_file: `~/security/.status` | — | Filtered status JSON (6 keys) |
| `security.last_scan` | file_tail: `/var/log/clamav-scans/` | — | Last 20 lines of latest ClamAV log |
| `security.health_snapshot` | file_tail: `/var/log/system-health/` | — | Last 30 lines of latest health log |
| `security.threat_lookup` | python: `ai.threat_intel.lookup` | `hash` (hex, 32-64 chars, required) | Hash lookup (VT + OTX + MalwareBazaar) |
| `security.ip_lookup` | python: `ai.threat_intel.ip_lookup` | `ip` (IPv4/IPv6, required) | IP reputation (AbuseIPDB + GreyNoise + Shodan) |
| `security.url_lookup` | python: `ai.threat_intel.ioc_lookup` | `url` (string, required) | URL/IOC lookup (URLhaus + ThreatFox + CIRCL) |
| `security.cve_check` | python: `ai.threat_intel.cve_scanner` | — | CVE scan (NVD + OSV + CISA KEV) |
| `security.sandbox_submit` | python: `ai.threat_intel.sandbox` | `file_path` | Submit quarantine file to Hybrid Analysis |
| `security.threat_summary` | python: `ai.threat_intel.summary` | — | Compile summary from all report dirs |
| `security.run_scan` | python | `scan_type` | Trigger ClamAV scan via systemctl |
| `security.run_health` | python | — | Trigger health snapshot via systemctl |
| `security.run_ingest` | python | — | Trigger log pipeline re-ingestion |
| `security.correlate` | python: `ai.threat_intel.correlator` | `ioc`, `ioc_type` | Correlate IOC across VT/OTX/AbuseIPDB/GreyNoise/URLhaus |
| `security.recommend_action` | python: `ai.threat_intel.playbooks` | `finding_type`, `finding_id` | Response playbook for threat findings |
| `security.alert_summary` | json_file: `~/security/alerts.json` | — | Proactive security alerts: active CVEs, stale scans, release advisories |

### knowledge.* (6 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `knowledge.rag_query` | python: `ai.rag.query` | `query` (string, max 500, required) | Semantic search — raw context chunks (no LLM) |
| `knowledge.rag_qa` | python: `ai.rag.query` | `question` (string, max 500, required) | LLM-synthesized answer from knowledge base |
| `knowledge.ingest_docs` | python: `ai.rag.ingest_docs` | — | Re-embed docs/ into LanceDB |
| `knowledge.pattern_search` | python: `ai.rag.pattern_query` | `query`, `language`, `domain` | Semantic search over curated code patterns |
| `knowledge.task_patterns` | python: `ai.learning.task_retriever` | `query`, `top_k` | Retrieve similar past successful tasks |
| `knowledge.session_history` | python: `ai.learning.handoff_parser` | `query`, `limit` | Search session history from HANDOFF.md entries |

### memory.* (1 tool)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `memory.search` | python: `ai.memory` | `query` (string, max 500, required), `top_k` (int, default 5) | Search conversation memories by semantic similarity |

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

### code.* (8 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `code.search` | python: ripgrep | `query` (string, max 128, required) | Pattern search across Python source |
| `code.rag_query` | python: `ai.rag.code_query` | `question` (string, max 500, required) | Semantic search over indexed code |
| `code.impact_analysis` | python: `ai.code_intel.store` | `changed_files`, `include_tests`, `max_depth` | Analyze impact of code changes |
| `code.dependency_graph` | python: `ai.code_intel.store` | `module`, `direction` | Get dependency graph for a module |
| `code.find_callers` | python: `ai.code_intel.store` | `function_name`, `include_indirect` | Find all callers of a function |
| `code.suggest_tests` | python: `ai.code_intel.store` | `changed_files` | Suggest tests covering changed files |
| `code.complexity_report` | python: `ai.code_intel.store` | `target`, `threshold` | Get complexity report for code |
| `code.class_hierarchy` | python: `ai.code_intel.store` | `class_name` | Get class hierarchy |

### collab.* (3 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `collab.queue_status` | python: `ai.collab.task_queue` | — | Get task queue status summary |
| `collab.add_task` | python: `ai.collab.task_queue` | `title`, `task_type`, `description`, `priority` | Add a task to the collaborative queue |
| `collab.search_knowledge` | python: `ai.collab.knowledge_base` | `query`, `top_k` | Search the agent knowledge base |

### workflow.* (8 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `workflow.list` | python: `ai.mcp_bridge.handlers.workflow_tools` | — | List all registered workflow definitions |
| `workflow.run` | python: `ai.mcp_bridge.handlers.workflow_tools` | `name`, `triggered_by` | Trigger a named workflow. Logs run to workflow_runs table |
| `workflow.status` | python: `ai.mcp_bridge.handlers.workflow_tools` | `name` | Get the most recent workflow_runs result for a workflow name |
| `workflow.agents` | python: `ai.mcp_bridge.handlers.workflow_tools` | — | List all registered agents and their supported task types |
| `workflow.handoff` | python: `ai.mcp_bridge.handlers.workflow_tools` | `agent`, `task_type`, `payload`, `priority` | Manually dispatch a task message to a named agent |
| `workflow.history` | python: `ai.mcp_bridge.handlers.workflow_tools` | `workflow_name`, `limit` | Query workflow_runs history |
| `workflow.history_steps` | python: `ai.mcp_bridge.handlers.workflow_tools` | `limit` | List recent runs with step-level summaries |
| `workflow.cancel` | python: `ai.mcp_bridge.handlers.workflow_tools` | `run_id` | Cancel pending/running steps for a run (marks workflow_steps as cancelled) |

### agents.* (5 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `agents.security_audit` | python: `ai.agents.security_audit` | — | Scan + health + ingest + RAG summary |
| `agents.performance_tuning` | python: `ai.agents.performance_tuning` | — | Temps, memory, disk, gaming profiles |
| `agents.knowledge_storage` | python: `ai.agents.knowledge_storage` | — | Vector DB health + embedding provider status |
| `agents.code_quality` | python: `ai.agents.code_quality_agent` | — | ruff + bandit + git status |
| `agents.timer_health` | python: `ai.agents.timer_sentinel` | — | Validate all 24 systemd timers. Returns per-timer status, stale list, and overall health. |

### intel.* (2 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `intel.scrape_now` | python: `ai.intel_scraper` | — | Trigger intelligence scrape: GitHub releases, CISA KEV, NVD CVEs, Fedora RSS |
| `intel.ingest_pending` | python: `ai.system.ingest_pipeline` | `intel_dir` (optional) | Ingest pending scraped intelligence into LanceDB |

### slack.* (4 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `slack.list_channels` | python: `ai.slack.handlers` | `limit` (int, default 100) | List Slack channels in the workspace |
| `slack.list_users` | python: `ai.slack.handlers` | — | List Slack workspace users |
| `slack.get_history` | python: `ai.slack.handlers` | `channel` (str, required), `limit` (int, default 100) | Get message history from a Slack channel |
| `slack.post_message` | python: `ai.slack.handlers` | `channel` (str, required), `text` (str, required), `thread_ts` (optional) | Post a message to a Slack channel |

### notion.* (4 tools)

| Tool | Source | Args | Description |
|------|--------|------|-------------|
| `notion.search` | python: `ai.notion.handlers` | `query` (str), `filter_type` (page\|database), `limit` (int, default 10) | Search pages and databases in Notion |
| `notion.get_page` | python: `ai.notion.handlers` | `page_id` (str, UUID, required) | Get a Notion page by ID |
| `notion.get_page_content` | python: `ai.notion.handlers` | `page_id` (str, UUID, required) | Get content blocks from a Notion page |
| `notion.query_database` | python: `ai.notion.handlers` | `database_id` (str, UUID, required), `filter` (JSON), `limit` (int, default 100) | Query a Notion database |

### Built-in

| Tool | Description |
|------|-------------|
| `health` | Returns `{"status": "ok", "tools": 96}` |

---

## Agent Orchestration (P53)

Module: `ai/orchestration/`

| Phase | Name | New Tools | New Timer | New LanceDB Table | Key Module |
|-------|------|-----------|-----------|-------------------|------------|
| **Prereq** | MCP Tool Filtering | — | — | `tool_metadata` | `ai/mcp_bridge/tool_filter.py` |
| **P32** | Testing Intelligence | — | — | `test_mappings` | `ai/testing/` |
| **P29** | Structural Code Intel | +6 | `code-index.timer` (Daily 6:00) | `code_nodes`, `relationships`, `import_graph`, `change_history` | `ai/code_intel/` |
| **P31** | Agent Collaboration | +3 | — | `shared_context`, `agent_knowledge` | `ai/collab/` |
| **P30** | Workflow Engine | +2 | — | `workflows` | `ai/workflows/` |
| **P33** | Plugin Factory | +2 | — | `persisted_tools` | `ai/tools/` |
| **P39** | Dependency Audit | +2 | `dep-audit.timer` (Weekly) | — | `ai/system/dep_audit.py` |
| **P40** | Performance Round 2 + Observability | +1 | `metrics-compact.timer` | — | `ai/metrics.py` |
| **P53** | Agent Orchestration Expansion | +6 | `ai-workflow-health.timer` (Every 6h) | `workflow_runs` | `ai/orchestration/`, `ai/workflows/` |
| **P54** | Workflow Hardening + Observability | +3 | — | `workflow_steps` | `ai/orchestration/observer.py`, `ai/workflows/` |
| **P55** | Notion/Slack Autonomous Control Plane | — | `phase-control.timer` (Every 15m) | — | `ai/phase_control/` |

Read-only live probe:
`./.venv/bin/python scripts/run-phase-control.py --smoke-test --database-id "$NOTION_PHASE_DATABASE_ID"`
This validates Notion config, queries the phase database, and resolves the next eligible phase without mutating any rows.

### Current State (Post-P55)

| Metric | Value |
|--------|-------|
| MCP tools | 96 (+ 1 health endpoint) |
| Systemd timers | 24 |
| LanceDB tables | 28 |
| Tests | 2236+ |
| Cloud LLM providers | 6 |
| Threat intel APIs | 16 |
| P44-P55 status | complete (2026-04-09) |

### Dependency Graph

```
P44 (Input Validation) ← foundational security layer
P45 (Semantic Cache) ← LanceDB-backed similarity cache
P46 (Token Budget) ← priority-tiered budget enforcement
P47 (Code Patterns) ← multi-language pattern RAG
P48 (Headless Briefing) ← autonomous security briefing + timer sentinel
P49 (Conversation Memory) ← persistent Newelle memory
P50 (Integration Tests) ← E2E validation
P51 (TBD) ←
```

## Frontend Capability Pack (P61)

Module: `docs/frontend-capability-pack/`

A documentation-and-prompt capability layer for generating React/Tailwind websites via OpenCode for **external projects**.

| Resource | Purpose |
|----------|---------|
| [System Profile](bazzite-ai-system-profile.md) | Repo identity and constraints |
| [Prompt Pack](frontend-capability-pack/prompt-pack.md) | Reusable prompt templates |
| [Scaffolds](frontend-capability-pack/scaffolds.md) | File organization patterns |
| [Accessibility](frontend-capability-pack/accessibility-guardrails.md) | WCAG-aligned practical rules |
| [Motion](frontend-capability-pack/motion-guidance.md) | Animation decision framework |
| [Runtime Harness](frontend-capability-pack/runtime-harness.md) | Preview + browser evidence workflow |
| [Validation](frontend-capability-pack/validation-flow.md) | Post-generation checklist |

### Site Archetypes

- [Landing Pages](frontend-capability-pack/site-archetypes/landing-pages.md)
- [Service Sites](frontend-capability-pack/site-archetypes/service-sites.md)
- [Dashboards](frontend-capability-pack/site-archetypes/dashboards.md)
- [Portfolios](frontend-capability-pack/site-archetypes/portfolios.md)
- [Lead-Gen Sites](frontend-capability-pack/site-archetypes/lead-gen.md)

### Key Principles

- **This repo is NOT a React app** — capability pack is for external projects only
- **No detached tool stack** — integrate with existing Bazzite/RuFlo/Notion workflows
- **Phase-scoped work** — frontend generation follows same phase rules as backend work

---

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

**Health tracking**: 5 consecutive failures → 2 min cooldown → exponential backoff → 10 min max.
**Stream recovery**: 2 KB commit threshold. Pre-commit failure → retry next provider.
**Sentry**: `traces_sample_rate=0.05`, `send_default_pii=False`. DSN from `SENTRY_DSN` env var.

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

## Systemd Timers (24)

| Timer | Schedule | Purpose |
|-------|----------|---------|
| `log-ingest.timer` | Sun 0:30 | Weekly log ingestion before archive |
| `system-health.timer` | Daily 8:00 | Hardware health snapshot |
| `security-briefing.timer` | Daily 8:45 | Headless daily security briefing |
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
| `security-alert.timer` | Every 6h | Security alert evaluation |
| `code-index.timer` | Daily 6:00 | Code intelligence index rebuild |
| `dep-audit.timer` | Weekly | pip-audit vulnerability scan + SBOM |
| `weekly-insights.timer` | Weekly | AI-generated weekly system insights |
| `ai-workflow-health.timer` | Every 6h | Workflow health check (security_deep_scan) |
| `phase-control.timer` | Every 15m | Notion/Slack autonomous control-plane tick |

---

## Critical Rules — NEVER Violate

1. **No PRIME offload env vars** — crashes Proton/Vulkan on GTX 1060 + Intel HD 630
2. **No lowering `vm.swappiness`** below 180 — required for ZRAM
3. **No `nvidia-xconfig`** — doesn't exist on immutable filesystem
4. **No `supergfxctl -m Dedicated`** — only Integrated and Hybrid modes exist
5. **No ProtonUp-Qt** — use ProtonPlus (or `ujust`) instead
6. **No local LLM generation** — Ollama `nomic-embed-text` is emergency embed fallback only
7. **No API keys in code, scripts, or git** — runtime-only via `keys.env`
8. **No `ai.router` import inside `ai/mcp_bridge/` or `ai/orchestration/`**
9. **No `shell=True` in subprocess** — all commands are static argument lists
10. **No writes to `~/security/.status` without read-modify-write + atomic rename**
11. **No global pip installs** — `uv` + `.venv/` only
12. **No `/usr` modifications** — immutable OS; use `rpm-ostree install`
13. **No `--break-system-packages`** — Python packages go in `.venv/` only
14. **All LLM calls through `ai/router.py`** — all API calls through `ai/rate_limiter.py`
15. **`restorecon` after every systemd unit install** — SELinux label restoration required

---

## Key Paths

### Repository paths

| Path | Purpose |
|------|---------|
| `ai/config.py` | Paths, constants, scoped key loading |
| `ai/router.py` | LiteLLM V2 router, health-weighted provider selection + Sentry init |
| `ai/health.py` | Provider health scoring + auto-demotion |
| `ai/llm_proxy.py` | OpenAI-compatible proxy on :8767 |
| `ai/rate_limiter.py` | Cross-script rate limiting with file locking |
| `ai/key_manager.py` | API key presence checker |
| `ai/mcp_bridge/server.py` | FastMCP server on :8766, tool registration |
| `ai/mcp_bridge/tools.py` | Tool dispatch handlers for all 96 tools |
| `ai/mcp_bridge/tool_filter.py` | Server-side namespace/semantic tool filtering (P29-Prereq) |
| `ai/threat_intel/` | VT, OTX, AbuseIPDB, GreyNoise, NVD, URLhaus, etc. (6 API modules) |
| `ai/rag/` | LanceDB store, embedder, query engine, code query |
| `ai/log_intel/` | Log ingestion, anomaly detection, semantic search |
| `ai/agents/` | 5 agent modules + 5 adapter wrappers (P53) |
| `ai/gaming/` | MangoHud analysis, ScopeBuddy profiles |
| `ai/cache_semantic.py` | SemanticCache: LanceDB-backed similarity cache with TTL |
| `ai/budget.py` | TokenBudget: daily token limits with priority tiers |
| `ai/metrics.py` | MetricsRecorder: time-series observability with buffered writes |
| `ai/memory.py` | ConversationMemory: persistent memory with semantic retrieval |
| `ai/provider_intel.py` | ProviderIntel: dynamic routing based on latency/error/cost |
| `ai/security/alerts.py` | SecurityAlertEvaluator: CVE matching, scan freshness, deduplication |
| `ai/security/inputvalidator.py` | Pre-dispatch input validation + secret redaction |
| `ai/system/` | release_watch, fedora_updates, pkg_intel, dep_audit |
| `ai/testing/` | TestStabilityTracker, pytest_plugin, traceability (P32) |
| `ai/code_intel/` | AST parser, grimp import graph, code knowledge graph (P29) |
| `ai/collab/` | Task queue, shared context, knowledge base, file claims (P31) |
| `ai/workflows/` | ReAct runner, workflow store, event triggers (P30) |
| `ai/tools/` | Dynamic tool builder with safety validation (P33) |
| `ai/skills/` | Pluggable skill loading (P30) |
| `ai/orchestration/` | OrchestrationBus, AgentMessage, AgentRegistry, BaseAgent (P53) |
| `ai/insights.py` | InsightGenerator for weekly self-assessment (P28) |
| `scripts/index-code.py` | Rebuild code intelligence index (P29) |
| `scripts/test-smart.sh` | Smart/full/flaky test runner wrapper (P32) |
| `scripts/security-alert-eval.py` | Security alert evaluation script (P27) |
| `scripts/parse-handoff.py` | Parse HANDOFF.md to task_patterns table (P38) |
| `configs/mcp-bridge-allowlist.yaml` | Tool definitions + argument validation |
| `configs/safety-rules.json` | Input validation rules |
| `configs/litellm-config.yaml` | LiteLLM provider routing config |
| `configs/ai-rate-limits.json` | Per-provider rate limits |
| `configs/keys.env.enc` | sops-encrypted API keys (in git, safe) |
| `scripts/` | Shell/Python scripts (deploy, scan, backup, etc.) |
| `scripts/lancedb-prune.py` | LanceDB retention pruning (90d logs, 180d threats) + cache cleanup |
| `scripts/metrics-compact.py` | Metrics compaction (P24) |
| `scripts/r2-set-lifecycle.py` | One-time R2 bucket lifecycle rule setup (180d auto-expiration) |
| `scripts/log-task-success.py` | CLI for logging successful task patterns to LanceDB (P22) |
| `systemd/` | 24 timers + associated services |
| `tests/` | ~1951 pytest tests |
| `tray/` | PySide6 system tray app |

### Runtime paths (not in repo)

| Path | Purpose |
|------|---------|
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys (chmod 600, never in git) |
| `~/.config/environment.d/bazzite-ai.conf` | Systemd user env vars (SENTRY_DSN, SENTRY_ENV) |
| `~/security/` | Canonical root for all runtime security data |
| `~/security/.status` | Shared JSON: ClamAV + health state (tray + MCP read this) |
| `~/security/vector-db/` | LanceDB root (→ `/var/mnt/ext-ssd/bazzite-ai/vector-db`). Tables: `documents` (RAG docs), `code_index` (code embeddings), `log_entries` (system logs), `code_patterns` (curated code patterns — P21), `task_patterns` (task outcomes — P22), `semantic_cache` (LLM response cache — P23), `metrics` (observability time-series — P24), `conversation_memory` (cross-session memory — P25), `system_insights` (weekly insight snapshots — P28), `tool_metadata` (P29-Prereq), `test_mappings` (P32), `code_nodes`, `relationships`, `import_graph`, `change_history` (P29), `shared_context`, `agent_knowledge` (P31), `workflows` (P30), `persisted_tools` (P33), `workflow_runs` (P53), `workflow_steps` (P54 step-level observability) |
| `~/security/vector-db/.archive-state.json` | R2 archive state (upload records with key, timestamp, size) |
| `~/security/llm-status.json` | LLM provider health + token usage |
| `~/security/key-status.json` | API key presence map |
| `~/security/release-watch.json` | Release watch results |
| `~/security/fedora-updates.json` | Fedora update check results |
| `~/security/alerts.json` | Active security alerts |
| `~/security/quarantine/` | ClamAV quarantine directory |
| `/var/log/system-health/` | Health snapshot logs |
| `/var/log/clamav-scans/` | ClamAV scan logs |
| `/var/mnt/ext-ssd/bazzite-ai/llm-cache` | LiteLLM disk cache |

---

## Build & Test

```bash
source .venv/bin/activate
python -m pytest tests/ -v          # 2193 tests
ruff check ai/ tests/               # Lint
bandit -r ai/ -c pyproject.toml     # Security scan
uv pip install -r requirements-ai.txt  # Install/update deps
```

---

## Dependencies

> Full version details: see `docs/verified-deps.md`

**Python 3.12** in `.venv/` managed by `uv`. Key packages: litellm, lancedb, fastmcp, pydantic, httpx, requests, cohere, boto3, pillow, sentry-sdk. LLM response cache: `ai/cache.py` (JsonFileCache, zero-dep, no pickle).

**Optional Desktop Dependencies**: Install with `uv pip install -e ".[tray]"`
- **PySide6>=6.6**: Required for security tray application (`tray/security_tray_qt.py`)

**Node.js v25** for RuFlo orchestration CLI (`@claude-flow/cli` v3.5.15) + 2 plugins (code-intelligence, test-intelligence).

**System tools** (rpm-ostree): ruff, bandit, shellcheck, gpg, sops, ollama.

---

## Dual-Agent Workflow

### Claude Code (primary implementation)

- Sandbox mode always on (bubblewrap)
- **Can**: edit files, git, pytest, ruff, bandit, curl/wget, uv, gpg, sops, `python -m ai.*`
- **Cannot**: sudo, systemctl, rpm-ostree, `rm -rf`, read `*.env`/`*.key`/`*.pem`, write to `/usr` or `/etc`
- Plugins: code-review, context7, code-simplifier, coderabbit, huggingface-skills

### OpenCode (audits, targeted edits)

- Provider: z.ai GLM models
- Config: `~/.config/opencode/opencode.jsonc` (not in git)
- Instructions: `.opencode/AGENTS.md`
- **Known issue**: 5-space indentation — always run `ruff check` after edits
- **Known issue**: May install to system Python 3.14 — always use `.venv/bin/python`

### Two-phase workflow (system-level changes only)

- **Phase A**: Agent creates/edits files + runs approved tools
- **Phase B**: User manually runs `sudo`/`systemctl` commands in terminal

---

## Cross-Tool Handoff System

Agents share context via `HANDOFF.md` in the project root.

- **`~/.local/bin/save-handoff.sh`** — project-aware, creates/updates `$PROJECT_ROOT/HANDOFF.md`
- **`/save-handoff`** slash command in both Claude Code and OpenCode
- **Claude Code auto-saves** on session end via `SessionEnd` hook
- **OpenCode requires manual** `/save-handoff` — no hook support

---

## Newelle Integration

Newelle (Flatpak GTK4) is the AI chat/voice UI.

- **LLM**: `http://127.0.0.1:8767/v1/` (`model="fast"`)
- **MCP**: `http://127.0.0.1:8766/mcp` (96 tools)
- **System prompt**: `docs/newelle-system-prompt.md`
- **Skills**: `docs/newelle-skills/` — 9 bundles
- **Morning briefing**: `docs/morning-briefing-prompt.md` (scheduled 9:30 AM)

---

## Known Active Issues

1. **`test_mcp_drift.py` failure** — `system.dep_scan` and `system.test_analysis` not in allowlist (pre-existing, not P53)
2. **Eicar test files stuck in quarantine** — needs `sudo chattr -i` + `rm` outside sandbox
3. **npm audit: 30 remaining vulns** — path-to-regexp, brace-expansion in RuFlo deps (not fixable without upstream)
4. **CPU 87°C idle** — needs repaste with Kryonaut Extreme
5. **Workflow/timer state can drift from docs** — verify with `systemctl list-timers --all` before assuming a timer is missing

---

## Software NOT to Use

| Software | Why Skip |
|----------|----------|
| **Local LLM generation** | 3-8 tok/s on GTX 1060 unusable. Monopolizes VRAM. |
| **ChromaDB** | HNSW index lives in RAM. LanceDB (disk-based) is better. |
| **g4f** | GPL v3, unknown third-party proxies, privacy risk. |
| **SonarQube** | 2-4 GB RAM + Elasticsearch. Too heavy. |
| **Wazuh** | Full SIEM needing 4-8 GB RAM. |
| **n8n** | Docker overhead; systemd timers handle all scheduling. |
| **LangChain/LangGraph** | 50 MB deps for patterns implementable in 100 LOC. |
