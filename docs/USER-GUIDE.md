# Bazzite AI Layer — User Guide
<!-- System: Acer Predator G3-571 | Bazzite 43 | Last updated: 2026-04-04 -->

Complete reference for operating, maintaining, and troubleshooting the AI
enhancement layer on this Bazzite gaming laptop.

---

## 1. System Overview

The Bazzite AI Layer adds cloud-powered threat intelligence, RAG-based
knowledge search, LLM routing, and system monitoring to the base Bazzite
security/gaming setup. Everything routes through **Newelle** (Flatpak GTK4
AI chat/voice assistant) as the primary interface.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Newelle (Flatpak GTK4)                  │
│                AI chat / voice assistant                 │
│       LLM: localhost:8767    MCP: localhost:8766         │
└─────────┬──────────────────────┬────────────────────────┘
          │                      │
    ┌─────▼──────┐        ┌──────▼──────────────┐
    │ LLM Proxy  │        │  MCP Bridge         │
    │ :8767      │        │  :8766 (FastMCP)    │
      │ Starlette  │        │  96 tools           │
    └─────┬──────┘        └──────┬──────────────┘
          │                      │
    ┌─────▼──────┐        ┌──────▼──────────────┐
    │ ai/router  │        │  ai/mcp_bridge/     │
    │ LiteLLM V2 │        │  tools.py           │
    │ health.py  │        │  (subprocess/python) │
    └─────┬──────┘        └──────┬──────────────┘
          │                      │
    ┌─────▼──────────────────────▼──────────────┐
    │         Cloud LLM Providers               │
    │  Gemini → Groq → Mistral → OpenRouter     │
    │  → z.ai → Cerebras                        │
    └───────────────────────────────────────────┘

    ┌───────────────────────────────────────────┐
    │         Local Infrastructure              │
    │  Ollama (emergency embed fallback, :11434)│
    │  LanceDB (~/security/vector-db/)          │
    │  ClamAV (scans via systemd timers)        │
    │  PySide6 tray app (4 tabs)                │
    │  ~/security/.status (shared JSON)         │
    └───────────────────────────────────────────┘
```

### Service Ports

| Port  | Service    | Protocol              | Binds to      |
|-------|------------|-----------------------|---------------|
| 8766  | MCP Bridge | FastMCP streamable-http | 127.0.0.1 only |
| 8767  | LLM Proxy  | OpenAI-compatible REST  | 127.0.0.1 only |
| 11434 | Ollama     | Ollama API (embed only) | 127.0.0.1 only |

---

## 2. Quick Start

### Start services

Both services auto-start on login. If they stopped:

```bash
systemctl --user start bazzite-llm-proxy.service bazzite-mcp-bridge.service
```

### Verify

```bash
# MCP bridge health
curl -s http://127.0.0.1:8766/health
# Expected: {"status": "ok", "tools": 96}

# LLM proxy health
curl -s http://127.0.0.1:8767/health
# Expected: {"status": "ok"}

# LLM models
curl -s http://127.0.0.1:8767/v1/models | python3 -m json.tool
```

### First interaction

Open Newelle and type:

> "Run a health check"

Newelle will call 5 system tools in parallel and return a concise summary
covering disk, CPU temps, GPU, memory, and security status.

---

## 3. Daily Operations

### Automatic timer schedule

All timers run unattended. This is the current scheduled timeline from `systemd/*.timer`:

| Time          | Timer                    | What it does                          |
|---------------|--------------------------|---------------------------------------|
| Daily 06:00     | `code-index.timer`         | Rebuild code intelligence index         |
| Daily 07:00     | `bazzite-intel-scrape.timer` | Run intelligence scraper              |
| Daily 08:00     | `system-health.timer`      | Hardware health snapshot                |
| Daily 08:15     | `performance-tuning.timer` | Performance analysis agent              |
| Daily 08:30     | `security-audit.timer`     | Automated security audit agent          |
| Daily 08:45     | `security-briefing.timer`  | Generate daily security briefing        |
| Daily 09:00     | `rag-embed.timer`          | Re-ingest logs into LanceDB             |
| Daily 09:15     | `knowledge-storage.timer`  | Knowledge base health check + auto-repair |
| Daily 09:45     | `release-watch.timer`      | Upstream release + GHSA check           |
| Daily 12:00     | `clamav-quick.timer`       | ClamAV quick scan                       |
| Daily 19:00     | `bazzite-intel-scrape.timer` | Run intelligence scraper              |
| Every 6h        | `security-alert.timer`     | Evaluate active security alerts         |
| Every 6h        | `ai-workflow-health.timer` | Run workflow health check               |
| Every 15m       | `service-canary.timer`     | AI service health check + auto-restart  |
| Every 15m       | `phase-control.timer`      | Notion/Slack phase control tick         |
| Wed 14:00       | `clamav-healthcheck.timer` | ClamAV daemon health check              |
| Fri 23:00       | `clamav-deep.timer`        | ClamAV full deep scan                   |
| Sat 00:00       | `cve-scanner.timer`        | CVE scan of installed packages          |
| Sun 00:30       | `log-ingest.timer`         | Weekly log ingestion before archive     |
| Sun 01:00       | `log-archive.timer`        | Compress + upload old logs to R2        |
| Sun 02:00       | `lancedb-optimize.timer`   | Compact and optimize LanceDB tables     |
| Sun 03:00       | `dep-audit.timer`          | Weekly pip-audit vulnerability scan     |
| Sun 03:00       | `metrics-compact.timer`    | Compact and prune metrics data          |
| Sun 03:00       | `weekly-insights.timer`    | Generate weekly AI insights             |
| Mon 03:00       | `fedora-updates.timer`     | Fedora Bodhi security update check      |

Check timer status:

```bash
systemctl list-timers --all | grep -E "clamav|system-health|rag-embed|security-audit|performance|knowledge|cve|release|fedora|log-|service-canary|lancedb-optimize"
```

### Morning briefing

Paste the prompt from `docs/morning-briefing-prompt.md` into Newelle as a
scheduled task at ~08:30 AM. It calls 7 tools in a single batch and returns
a structured briefing covering security, health, updates, and action items.

### Tray app

The PySide6/Qt6 tray app runs in the system tray with 4 dashboard tabs:

| Tab      | Shows                                                    |
|----------|----------------------------------------------------------|
| Security | ClamAV scan state, last scan time, threat count          |
| Health   | System health status, open issues, last snapshot time     |
| Keys     | API key presence by category (set/missing, never values)  |
| About    | System info, service status, version                      |

Launch manually if needed:

```bash
bash scripts/start-security-tray-qt.sh
```

### Common Newelle commands

| Say this                          | Newelle calls              |
|-----------------------------------|----------------------------|
| "Check my health"                 | 5 system tools → summary   |
| "What's my pipeline status"      | `system.pipeline_status`  |
| "Scan for threats"                | `security.run_scan`        |
| "Look up this hash: abc123..."    | `security.threat_lookup`   |
| "Is this IP malicious: 1.2.3.4"  | `security.ip_lookup`       |
| "Check this URL for threats"      | `security.url_lookup`      |
| "What CVEs affect my system"      | `security.cve_check`       |
| "Check for updates"               | `system.fedora_updates`    |
| "Any new releases for my tools"   | `system.release_watch`     |
| "What's my disk usage"            | `system.disk_usage`        |
| "Run a full security audit"       | `agents.security_audit`    |
| "Search docs for ZRAM"            | `knowledge.rag_query`      |
| "What game profiles do I have"    | `gaming.profiles`          |

---

## 4. MCP Tools Reference (96 tools)

All tools are accessible through Newelle via the MCP bridge. They are read-only
(no system mutations). Output is truncated to 4 KB and paths are redacted.

> **Input Validation**: The MCP bridge validates all tool arguments before execution.
> Malicious inputs (SQL injection, command injection, path traversal) are blocked.
> If you see "Input validation failed", adjust your query to avoid risky patterns.
> API keys and tokens are automatically redacted from logs.

### system.* (33 tools)

| Tool                       | Args                         | What it returns                                    |
|----------------------------|------------------------------|----------------------------------------------------|
| `system.disk_usage`        | —                            | `df -h` output                                     |
| `system.cpu_temps`         | —                            | `sensors -j` JSON thermal data                     |
| `system.gpu_status`        | —                            | nvidia-smi: temp, VRAM, power draw                 |
| `system.gpu_perf`          | —                            | GPU perf snapshot: pstate, clocks, throttle reasons |
| `system.gpu_health`        | —                            | GPU health diagnostic with throttle bit interpretation |
| `system.memory_usage`      | —                            | `free -h` output (RAM + ZRAM)                      |
| `system.uptime`            | —                            | System uptime and load average                     |
| `system.service_status`    | —                            | Status of clamav-freshclam, system-health.timer, mcp-bridge, llm-proxy |
| `system.llm_models`        | —                            | Available modes (fast/reason/batch/code/embed), provider chains, proxy URL |
| `system.mcp_manifest`      | —                            | All 96 tools with descriptions and args (8 KB limit) |
| `system.llm_status`        | —                            | Provider health scores, token usage, active models |
| `system.key_status`        | —                            | API key presence: "set" or "missing" per key (never values) |
| `system.release_watch`     | —                            | Upstream dependency release updates (GitHub Releases, GHSA) |
| `system.fedora_updates`    | —                            | Fedora/Bazzite pending security and package updates (Bodhi) |
| `system.pkg_intel`         | —                            | Package advisories, provenance, version status (deps.dev) |
| `system.cache_stats`       | —                            | LLM cache statistics: entries, size, hit rate |
| `system.token_report`      | —                            | Token usage and cost report from LLM proxy |
| `system.pipeline_status`   | —                            | Log pipeline ingest/archive/retention status, pending files, table row counts |
| `system.budget_status`     | —                            | Daily token budget usage and warnings across priority tiers |
| `system.metrics_summary`   | `hours`, `metric_type`       | Aggregate metrics for last 24h |
| `system.provider_status`   | —                            | Per-provider health, latency, error rates, and routing scores |
| `system.weekly_insights`   | `limit`                      | Cached AI-generated weekly insights and recommendations |
| `system.insights`          | —                            | Generate on-demand AI layer insights |
| `system.dep_audit`         | —                            | Run pip-audit vulnerability scan and return findings |
| `system.dep_audit_history` | `limit`                      | Retrieve historical dep-audit scan results |
| `system.create_tool`       | `name`, `description`, `handler_code` | Create a dynamic tool with safety validation |
| `system.list_dynamic_tools`| —                            | List all persisted dynamic tools |
| `system.alert_history`     | `limit`                      | Recent desktop alert dispatch history |
| `system.alert_rules`       | —                            | List all alert rules with enabled/cooldown status |
| `system.dep_scan`          | —                            | Scan .venv dependencies for vulnerabilities via OSV API |
| `system.test_analysis`     | `input`                      | Analyze pytest output for failure patterns and fix hints |
| `system.perf_profile`      | `skip`                       | Run performance profiler (LLM, MCP, file I/O, LanceDB, system) |
| `system.mcp_audit`         | `tool_name`                  | Audit MCP bridge allowlist for missing handlers |

### security.* (15 tools)

| Tool                         | Args                    | What it returns                             |
|------------------------------|-------------------------|---------------------------------------------|
| `security.last_scan`         | —                       | Last 20 lines of latest ClamAV scan log     |
| `security.health_snapshot`   | —                       | Last 30 lines of latest health snapshot     |
| `security.status`            | —                       | Filtered `.status` JSON (6 keys: state, scan_type, last_scan_time, result, health_status, health_issues) |
| `security.threat_lookup`     | `hash` (MD5/SHA256)     | VT + OTX + MalwareBazaar enrichment         |
| `security.ip_lookup`         | `ip` (IPv4/IPv6)        | AbuseIPDB abuse score + GreyNoise classification + Shodan InternetDB ports/vulns |
| `security.url_lookup`        | `url`                   | URLhaus + ThreatFox + CIRCL Hashlookup      |
| `security.cve_check`         | —                       | CVE scan of installed packages (NVD + OSV + CISA KEV overlay) |
| `security.sandbox_submit`    | `file_path` (quarantine/) | Submit quarantine file to Hybrid Analysis sandbox |
| `security.threat_summary`    | —                       | Compiled summary from all agent/scan report dirs |
| `security.run_scan`          | `scan_type` (quick\|deep) | Triggers ClamAV scan via systemctl         |
| `security.run_health`        | —                       | Triggers health snapshot via systemctl      |
| `security.run_ingest`        | —                       | Triggers log pipeline re-ingestion          |
| `security.correlate`         | `ioc`, `ioc_type`       | Correlate IOC across VT/OTX/AbuseIPDB/GreyNoise/URLhaus |
| `security.recommend_action`  | `finding_type`, `finding_id` | Response playbook for threat findings  |

### knowledge.* (6 tools)

| Tool                        | Args                 | What it returns                              |
|-----------------------------|----------------------|----------------------------------------------|
| `knowledge.rag_query`       | `query` (max 500ch)  | Semantic search — raw context chunks (no LLM) |
| `knowledge.rag_qa`          | `question` (max 500ch) | LLM-synthesized answer from knowledge base |
| `knowledge.ingest_docs`     | —                    | Re-embeds docs/ into LanceDB                 |
| `knowledge.pattern_search`  | `query`, `language`, `domain` | Semantic search over curated code patterns |
| `knowledge.task_patterns`   | `query`, `top_k`     | Retrieve similar past successful tasks       |
| `knowledge.session_history` | `query`, `limit`     | Search session history from HANDOFF.md entries |

### memory.* (1 tool)

| Tool            | Args           | What it returns                              |
|-----------------|----------------|----------------------------------------------|
| `memory.search` | `query`, `top_k` | Search conversation memories by semantic similarity |

### gaming.* (2 tools)

| Tool                   | Args               | What it returns                               |
|------------------------|---------------------|-----------------------------------------------|
| `gaming.profiles`      | —                   | List of configured game profiles               |
| `gaming.mangohud_preset` | `game`            | MangoHud overlay preset for a specific game    |

### logs.* (5 tools)

| Tool               | Args                 | What it returns                              |
|--------------------|----------------------|----------------------------------------------|
| `logs.health_trend`| —                    | Last 7 health snapshots with delta trends     |
| `logs.scan_history`| —                    | Last 10 ClamAV scan results                   |
| `logs.anomalies`   | —                    | Unacknowledged anomalies (threats, temp spikes, disk) |
| `logs.search`      | `query` (max 500ch)  | Semantic search across system logs             |
| `logs.stats`       | —                    | Log pipeline stats: row counts, last ingest, DB size |

### code.* (9 tools)

| Tool                      | Args                    | What it returns                          |
|---------------------------|--------------------------|------------------------------------------|
| `code.search`             | `query` (max 128ch)      | ripgrep pattern search across Python code |
| `code.rag_query`          | `question` (max 500ch)   | Semantic search over indexed Python code  |
| `code.impact_analysis`    | `changed_files`          | Impact of code changes on dependent modules |
| `code.dependency_graph`   | `module`, `direction`    | Dependency graph for a module             |
| `code.blast_radius`       | `changed_files`, `max_depth` | Blast radius with hop depth            |
| `code.find_callers`       | `function_name`          | All functions that call a given function  |
| `code.suggest_tests`      | `changed_files`          | Tests that cover the changed files        |
| `code.complexity_report`  | `target`, `threshold`    | Complexity report for code files          |
| `code.class_hierarchy`    | `class_name`             | Class hierarchy for a given class         |

### collab.* (3 tools)

| Tool                    | Args                              | What it returns                      |
|-------------------------|-----------------------------------|--------------------------------------|
| `collab.queue_status`   | —                                 | Task queue status summary             |
| `collab.add_task`       | `title`, `task_type`, `description`, `priority` | Add a task to the queue |
| `collab.search_knowledge` | `query`, `top_k`               | Search the agent knowledge base       |

### workflow.* (8 tools)

| Tool                 | Args                                  | What it returns                                    |
|----------------------|---------------------------------------|----------------------------------------------------|
| `workflow.list`      | —                                     | List all registered workflow definitions           |
| `workflow.run`       | `name`, `triggered_by`                | Trigger a named workflow, logs to LanceDB          |
| `workflow.status`    | `name`                                | Get last run result for a workflow                 |
| `workflow.agents`    | —                                     | List all registered agents and task types          |
| `workflow.handoff`   | `agent`, `task_type`, `payload`, `priority` | Manually dispatch a task to an agent |
| `workflow.history`   | `workflow_name`, `limit`             | Query workflow_runs table                          |
| `workflow.history_steps` | `limit`                           | List recent runs with step-level summaries         |
| `workflow.cancel`    | `run_id`                              | Cancel pending or running steps for a run          |

### intel.* (2 tools)

| Tool                  | Args       | What it returns                                        |
|-----------------------|------------|--------------------------------------------------------|
| `intel.scrape_now`    | —          | Trigger intelligence scrape (GitHub, CISA KEV, NVD, Fedora) |
| `intel.ingest_pending`| `intel_dir`| Ingest pending scraped intelligence into LanceDB RAG   |

### agents.* (5 tools)

| Tool                       | Args | What it returns                                    |
|----------------------------|------|----------------------------------------------------|
| `agents.security_audit`    | —    | Full audit: scan + health + ingest + RAG summary    |
| `agents.performance_tuning`| —    | Temps, memory, disk, gaming profile analysis         |
| `agents.knowledge_storage` | —    | Vector DB health, ingestion freshness, Ollama status |
| `agents.code_quality`      | —    | ruff + bandit + git status report                    |
| `agents.timer_health`      | —    | Validate all 24 systemd timers; returns per-timer status and overall health |

### Built-in

| Tool     | Returns                           |
|----------|-----------------------------------|
| `health` | `{"status": "ok", "tools": 96}`   |

---

## 5. LLM Provider Chain

### Task types

| Type    | Use case            | Provider chain (health-weighted)                          |
|---------|---------------------|----------------------------------------------------------|
| `fast`  | Interactive, speed  | Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras  |
| `reason`| Deep analysis       | Gemini → Groq → Mistral → OpenRouter(Claude) → z.ai     |
| `batch` | Volume processing   | Gemini → Groq → Mistral → OpenRouter → Cerebras         |
| `code`  | Code-specialized    | Gemini → Groq → Mistral(Codestral) → OpenRouter → z.ai  |
| `embed` | Embeddings          | Gemini Embedding 001 → Cohere → Ollama (emergency)       |

Newelle sends a model name (e.g., `fast`, `reason`) in the request body.
The LLM proxy maps it to a task type and routes through the provider chain.

### Switching models in Newelle

In Newelle: Settings → API → Model field. Change from `fast` to any task
type name. The proxy maps common model names too:

| Newelle model               | Maps to   |
|-----------------------------|-----------|
| `fast`, `auto`, `gpt-4o-mini` | `fast`  |
| `reason`, `gpt-4o`           | `reason`|
| `batch`                       | `batch` |
| `code`                        | `code`  |
| anything else                 | `fast`  |

### Switching models via Newelle Profiles

Newelle's Profile Manager (Settings → Profile Manager) lets you create
isolated profiles with different model names. Each profile remembers its
own settings and model preference, so you can switch task types per-chat
without changing the global API setting.

Suggested profiles to create:

| Profile name   | Model field | Use case                                  |
|----------------|-------------|-------------------------------------------|
| General        | `fast`      | Default — interactive queries, speed      |
| Code Review    | `code`      | Code-specialized providers (Codestral)    |
| Deep Analysis  | `reason`    | Multi-step reasoning, architecture review |
| Batch          | `batch`     | High-volume or bulk processing tasks      |

All profiles use the same API endpoint (`http://127.0.0.1:8767/v1`) and the
same API key. Only the model name changes — the proxy maps it to the
appropriate provider chain automatically.

The system prompt instructs Newelle to suggest profile switches when a query
would benefit from deeper reasoning (e.g., "For deeper analysis, switch to
your 'reason' profile in Settings → Profile Manager").

### Health tracking

Each provider gets a health score (0.0–1.0) based on success rate and
latency. 5 consecutive failures trigger auto-demotion with exponential
backoff: 2 min → 4 min → 10 min max. Recovery is automatic.

### Check status

```bash
# Via Newelle
# Ask: "What's my LLM status?"  → calls system.llm_status

# Via CLI
cat ~/security/llm-status.json | python3 -m json.tool

# Via Python
python3 -c "
from ai.config import load_keys
from ai.router import route_query
load_keys()
print(route_query('fast', 'Say hello'))
"
```

---

## 6. API Keys Management

### Where keys live

| Location                             | Purpose                        | In git? |
|--------------------------------------|--------------------------------|---------|
| `~/.config/bazzite-ai/keys.env`     | Plaintext keys (chmod 600)     | NO      |
| `configs/keys.env.enc`              | sops-encrypted copy            | YES     |
| `~/security/key-status.json`        | Presence map (set/missing)     | NO      |

### Key categories

| Category       | Count | Keys                                                                 |
|----------------|-------|----------------------------------------------------------------------|
| LLM Providers  | 12    | GEMINI, GROQ, MISTRAL, OPENROUTER, CEREBRAS, ZAI, ANTHROPIC, COHERE, HF_TOKEN, GITHUB_TOKEN, CLOUDFLARE, DEEPSEEK |
| Threat Intel   | 6     | VT, ABUSEIPDB, OTX, NVD, GREYNOISE, HYBRID_ANALYSIS                 |
| Storage        | 2     | R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY                               |
| Monitoring     | 1     | SENTRY_DSN                                                           |
| Code Quality   | 1     | SEMGREP_APP_TOKEN                                                    |

### Add or update a key

```bash
# 1. Edit the plaintext file
nano ~/.config/bazzite-ai/keys.env
# Add: NEW_KEY=sk-abc123...

# 2. Re-encrypt for git
cd ~/projects/bazzite-laptop
SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml \
  sops -e --input-type dotenv --output-type dotenv \
  ~/.config/bazzite-ai/keys.env > configs/keys.env.enc

# 3. Commit the encrypted version
git add configs/keys.env.enc && git commit -m "keys: update encrypted keys"

# 4. Verify presence
python3 -m ai.key_manager status
```

### Check key status

```bash
# CLI (exit code 1 if any keys missing)
source .venv/bin/activate
python3 -m ai.key_manager status

# Via Newelle
# Ask: "What's my key status?"  → calls system.key_status

# Via tray app
# Open dashboard → Keys tab
```

### Decrypt keys (read-only check)

```bash
SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml \
  sops -d --input-type dotenv --output-type dotenv configs/keys.env.enc
```

---

## 7. Security Features

### ClamAV scanning

| Schedule       | Timer                  | What it does                    |
|----------------|------------------------|---------------------------------|
| Daily 12:00    | `clamav-quick.timer`   | Quick scan of home + downloads  |
| Fri 23:00      | `clamav-deep.timer`    | Full deep scan                  |
| Wed 14:00      | `clamav-healthcheck.timer` | Daemon health check         |

Trigger manually via Newelle: "Run a scan" → `security.run_scan`

View results: "Show last scan" → `security.last_scan`

### Threat intel enrichment

When you look up a file hash, the system cascades through:

1. **VirusTotal** — detection ratio, family, tags
2. **AlienVault OTX** — pulse references, indicators
3. **MalwareBazaar** — malware family, first seen

Use via Newelle: "Look up hash abc123..." → `security.threat_lookup`

### IP reputation

When you check an IP address:

1. **AbuseIPDB** — abuse confidence score (0-100), ISP, country
2. **GreyNoise** — classification (benign/malicious/unknown), noise context
3. **Shodan InternetDB** — open ports, known vulnerabilities

Use via Newelle: "Is 1.2.3.4 malicious?" → `security.ip_lookup`

### URL/IOC lookup

When you check a URL or indicator:

1. **URLhaus** — malware distribution URLs, threat type
2. **ThreatFox** — IOC database, malware family mapping
3. **CIRCL Hashlookup** — known-good/known-bad hash database

Use via Newelle: "Check this URL for threats" → `security.url_lookup`

### CVE scanning

Weekly automated scan (Saturday midnight) of installed packages against:

1. **NVD (NIST)** — comprehensive CVE database
2. **OSV (Google)** — open-source vulnerability database
3. **CISA KEV** — Known Exploited Vulnerabilities overlay (highest priority)

Use via Newelle: "What CVEs affect my system?" → `security.cve_check`

Any CVE flagged in CISA KEV should be patched immediately.

### Sandbox analysis

For suspicious files in quarantine:

```bash
# Via Newelle: "Submit quarantine/suspicious-file to sandbox"
# → security.sandbox_submit
```

Files are submitted to **Hybrid Analysis** using a hash-first approach:
if the hash is already known, results are returned without re-submission.

### Quarantine workflow

1. ClamAV detects threat → file moved to `~/security/quarantine/`
2. Check threat details: `security.threat_lookup` with the file hash
3. If suspicious: `security.sandbox_submit` for deeper analysis
4. To release (if false positive):
   ```bash
   sudo bash scripts/quarantine-release.sh <filename>
   ```

---

## 8. RAG & Knowledge Base

### What's indexed

| LanceDB Table     | Contents                        | Source               |
|--------------------|---------------------------------|----------------------|
| `security_logs`    | ClamAV scan logs, health logs   | `ai/log_intel/`      |
| `threat_intel`     | Threat lookup results           | `ai/threat_intel/`   |
| `docs`             | Markdown docs from `docs/`      | `ai/rag/ingest_docs` |
| `health_records`   | Health snapshot data            | `ai/log_intel/`      |
| `scan_records`     | ClamAV scan records             | `ai/log_intel/`      |

LanceDB lives at `~/security/vector-db/` (symlinked to external SSD).

### Embedding

| Provider  | Model                   | Dimension | When used                             |
|-----------|-------------------------|-----------|---------------------------------------|
| Gemini    | `gemini-embedding-001`  | 768       | Primary — free 10M TPM                |
| Cohere    | `embed-english-v3.0`    | 768       | Fallback when Gemini down/rate-limited |
| Ollama    | `nomic-embed-text`      | 768       | Emergency fallback only — not loaded by default |

The provider is locked per ingestion batch to avoid dimension mismatches.
Gemini requests 768-dim via Matryoshka (pass `dimensions=768` explicitly).

### Query the knowledge base

```bash
# Via Newelle (context chunks, no LLM)
# Ask: "Search docs for ZRAM"  → knowledge.rag_query

# Via Newelle (LLM-synthesized answer)
# Ask: "Explain how the health monitoring works"  → knowledge.rag_qa

# Via CLI
source .venv/bin/activate
python3 -m ai.rag.query "What GPU errors happened last week?"
```

### Re-ingest

```bash
# Via Newelle
# Ask: "Re-ingest the knowledge base"  → knowledge.ingest_docs

# Re-ingest all logs
source .venv/bin/activate
python3 -m ai.log_intel --all

# Re-ingest docs only (incremental)
bash scripts/ingest-docs.sh

# Re-ingest docs (force, ignores state file)
bash scripts/ingest-docs.sh --force
```

### LanceDB Health Check & Auto-Repair

The `knowledge-storage.timer` (daily 09:15) runs a comprehensive health check
that includes:

- **Corruption Detection**: Scans all LanceDB tables for malformed vectors,
  missing `.lance` directories, schema corruption, and NaN/Inf values
- **Automatic Repair**: If corruption is detected, automatically:
  1. Creates timestamped backup (`~/security/vector-db-backup-YYYYMMDD-HHMMSS/`)
  2. Preserves uncorrupted rows, drops and recreates corrupted tables
  3. Auto-prunes oldest backups (keeps last 3)
- **Permission Handling**: Gracefully handles read-only filesystem errors

Run manually:
```bash
# Health check only (no auto-repair)
python -m ai.agents.knowledge_storage

# With auto-repair enabled (default)
python -c "from ai.agents.knowledge_storage import run_storage_check; run_storage_check(auto_repair=True)"
```

View latest report:
```bash
ls -lt ~/security/storage-reports/storage-*.json | head -1
```

### Conversation memory (opt-in)

`ai/rag/memory.py` provides LanceDB-backed conversation memory. Off by default.

To enable, add to `~/.config/bazzite-ai/keys.env`:
```
ENABLE_CONVERSATION_MEMORY=true
```

Then restart the LLM proxy:
```bash
systemctl --user restart bazzite-llm-proxy.service
```

When enabled, each chat turn is embedded and stored. Relevant past context
is retrieved and prepended to new requests. Disable if Newelle's built-in
semantic memory already covers this need.

---

## 8b. Workflow Orchestration

The AI layer includes a workflow engine for orchestrating multi-agent tasks.
Workflows are defined in `ai/workflows/definitions.py` and executed via the
`workflow.*` MCP tools.

### Available Workflows

| Workflow | Description |
|----------|-------------|
| `security_deep_scan` | Full security audit: scan → health → ingest → RAG summary |
| `code_health_check` | Code quality → performance → knowledge storage |
| `morning_briefing_enriched` | Timer-triggered security briefing with knowledge context |

### Using Workflow Tools

**List available workflows:**
```
workflow.list
```

**Run a workflow:**
```
workflow.run {name: "security_deep_scan", triggered_by: "user"}
```

**Check workflow status:**
```
workflow.status {name: "security_deep_scan"}
```

**Query workflow history:**
```
workflow.history {workflow_name: "security_deep_scan", limit: 10}
```

**List recent step summaries:**
```
workflow.history_steps {limit: 10}
```

### Agent Handoff

You can manually dispatch tasks to specific agents:

```
workflow.handoff {
  agent: "security",
  task_type: "run_audit",
  payload: {target: "/home/lch/projects"},
  priority: 5
}
```

Available agents: `security`, `code_quality`, `performance`, `knowledge`, `timer_sentinel`

### Automated Health Check

The `ai-workflow-health.timer` runs every 6 hours to execute `security_deep_scan`
automatically. To enable after installation:

```bash
systemctl --user enable --now ai-workflow-health.timer
```

---

## 9. System Monitoring

### Release watch (daily 09:45)

Checks GitHub Releases and GHSA advisories for tracked upstream dependencies.
Results written to `~/security/release-watch.json`.

Check via Newelle: "Any new releases for my tools?" → `system.release_watch`

### Fedora/Bodhi updates (weekly Monday 03:00)

Polls Fedora Bodhi for pending security and package updates relevant to
the Bazzite base system. Results written to `~/security/fedora-updates.json`.

Check via Newelle: "Check for Fedora updates" → `system.fedora_updates`

### Package intelligence (on-demand)

Queries deps.dev for package advisories, provenance information, and version
status. Not scheduled — available on demand.

Check via Newelle: "Check package intelligence" → `system.pkg_intel`

### Health snapshots (daily 08:00)

Collects SMART disk health, GPU state, CPU thermals, storage/ZRAM stats.
Logs written to `/var/log/system-health/health-*.log`.

Check via Newelle: "Show health snapshot" → `security.health_snapshot`

Trigger manually: "Run a health snapshot" → `security.run_health`

### Agent reports

| Agent                    | Schedule     | What it does                              |
|--------------------------|--------------|-------------------------------------------|
| `security-audit`         | Daily 08:30  | Full scan + health + ingest + RAG summary |
| `performance-tuning`     | Daily 08:15  | Temps, memory, disk, gaming analysis      |
| `knowledge-storage`      | Daily 09:15  | Vector DB health, Ollama status, disk     |

Check via Newelle: "Run a security audit" → `agents.security_audit`

---

## 10. Maintenance

### Backup

```bash
# Mount flash drive, then:
sudo bash /mnt/backup/backup.sh
```

Backs up: `~/security/`, project configs, `.config/bazzite-ai/`, LanceDB.

### Deploy after code changes

```bash
# Deploys user + system services, prompts for sudo internally
bash scripts/deploy-services.sh
```

After deploy, fix SELinux context:

```bash
sudo restorecon -v /etc/systemd/system/system-health.* /etc/systemd/system/clamav-*
sudo systemctl daemon-reload
```

### Update Python dependencies

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Re-encrypt API keys

After editing `~/.config/bazzite-ai/keys.env`:

```bash
cd ~/projects/bazzite-laptop
SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml \
  sops -e --input-type dotenv --output-type dotenv \
  ~/.config/bazzite-ai/keys.env > configs/keys.env.enc
git add configs/keys.env.enc && git commit -m "keys: update encrypted keys"
```

### Log archiving

Weekly (Sunday 00:30 → 01:00 → 02:00) via `log-ingest.timer` → `log-archive.timer` → `lancedb-optimize.timer`. The pipeline:
1. **Ingest** (Sun 00:30): LanceDB ingestion of health/scan logs
2. **Archive** (Sun 01:00): Compress logs older than 7 days and upload to Cloudflare R2
3. **Prune** (Sun 02:00): Delete rows older than retention (90d logs, 180d threats)

Check pipeline state:
```bash
cat ~/security/vector-db/.archive-state.json | python3 -m json.tool
```

Configuration: `configs/r2-config.yaml`

### Restart services

```bash
# User services (no sudo)
systemctl --user restart bazzite-mcp-bridge.service
systemctl --user restart bazzite-llm-proxy.service

# Check status
systemctl --user status bazzite-mcp-bridge.service
systemctl --user status bazzite-llm-proxy.service
```

### Check all timers

```bash
systemctl list-timers --all | grep -E "clamav|system-health|rag-embed|security-audit|performance|knowledge|cve|release|fedora|log-archive|service-canary|lancedb-optimize"
```

---

## 11. Troubleshooting

### Service won't start

```bash
# Check logs
journalctl --user -u bazzite-llm-proxy.service --since "5 minutes ago"
journalctl --user -u bazzite-mcp-bridge.service --since "5 minutes ago"

# Common causes:
# - Port already in use: another instance running
# - Missing keys.env: scoped key load fails
# - Missing Python deps: run uv pip install -r requirements.txt
```

### MCP tools not responding

```bash
# Check bridge health
curl -s http://127.0.0.1:8766/health

# If no response: restart the bridge
systemctl --user restart bazzite-mcp-bridge.service

# Check if port is bound
ss -tlnp | grep 8766
```

### Provider auth errors

```bash
# Check LLM status for auth_broken flags
cat ~/security/llm-status.json | python3 -m json.tool

# Look for:  "auth_broken": true
# Fix: update the key in ~/.config/bazzite-ai/keys.env, then:
systemctl --user restart bazzite-llm-proxy.service
```

### LanceDB errors in VS Code terminal

Known issue: LanceDB can segfault inside the VS Code integrated terminal
due to Flatpak sandbox interactions. Use a standalone terminal instead.

### SELinux context after deploy

After copying unit files to `/etc/systemd/system/`:

```bash
sudo restorecon -v /etc/systemd/system/system-health.*
sudo restorecon -v /etc/systemd/system/clamav-*
sudo systemctl daemon-reload
```

### Orphaned claude-flow processes

If RuFlo dev sessions leave zombie processes:

```bash
pkill -f "claude-flow"
```

### Rate limit exhausted

```bash
# Check which provider is limited
cat configs/ai-rate-limits.json | python3 -m json.tool

# Common resets:
# - Groq: per-minute (wait 60s)
# - VirusTotal: per-day (wait until midnight UTC)
# - GreyNoise: 7/day (wait 24h)

# The router automatically falls back to the next healthy provider.
```

### Timer not firing

```bash
# Check timer status
systemctl list-timers --all | grep <timer-name>

# If NEXT/LAST shows "---":
sudo systemctl cat <service-name>     # Verify unit exists
sudo restorecon -v /etc/systemd/system/<unit>.*
sudo systemctl daemon-reload
sudo systemctl enable --now <timer-name>
```

### Stale health-latest.log symlink

After logrotate, `health-latest.log` may point to an empty file. The MCP
bridge `_read_file_tail()` automatically skips empty and symlinked files
and falls back to the next non-empty log. No action needed.

### Ollama not responding

```bash
# Check if running
systemctl status ollama

# Restart
sudo systemctl restart ollama

# Pull embedding model if missing
ollama pull nomic-embed-text
```

---

## 12. Key Paths Reference

### Project files

| Path                                      | Purpose                                    |
|-------------------------------------------|--------------------------------------------|
| `~/projects/bazzite-laptop/`              | Project root (git repo)                    |
| `ai/config.py`                            | Paths, constants, scoped key loading       |
| `ai/router.py`                            | LiteLLM V2 router, health-weighted        |
| `ai/health.py`                            | Provider health scoring, auto-demotion     |
| `ai/llm_proxy.py`                         | OpenAI-compat proxy on :8767               |
| `ai/rate_limiter.py`                      | Cross-script rate limiting                 |
| `ai/key_manager.py`                       | API key presence checker                   |
| `ai/mcp_bridge/server.py`                 | FastMCP server on :8766                    |
| `ai/mcp_bridge/tools.py`                  | All 48 tool dispatch handlers              |
| `ai/threat_intel/lookup.py`               | VT + OTX + MalwareBazaar hash enrichment   |
| `ai/threat_intel/ip_lookup.py`            | AbuseIPDB + GreyNoise + Shodan             |
| `ai/threat_intel/ioc_lookup.py`           | URLhaus + ThreatFox + CIRCL                |
| `ai/threat_intel/cve_scanner.py`          | NVD + OSV + CISA KEV                       |
| `ai/threat_intel/sandbox.py`              | Hybrid Analysis submission                 |
| `ai/threat_intel/summary.py`              | Threat summary compiler                    |
| `ai/system/release_watch.py`              | GitHub Releases + GHSA watcher             |
| `ai/system/fedora_updates.py`             | Fedora Bodhi polling                       |
| `ai/system/pkg_intel.py`                  | deps.dev package intelligence              |
| `ai/rag/embedder.py`                      | Gemini Embed primary + Cohere fallback + Ollama emergency |
| `ai/rag/store.py`                         | LanceDB VectorStore                        |
| `ai/rag/query.py`                         | RAG query engine                           |
| `ai/rag/ingest_docs.py`                   | Document ingestion + dedup                 |
| `ai/rag/memory.py`                        | Opt-in conversation memory                 |
| `ai/log_intel/ingest.py`                  | Log ingestion pipeline                     |
| `ai/log_intel/queries.py`                 | Health trend, anomalies, search            |
| `ai/agents/security_audit.py`             | Automated security audit agent             |
| `ai/agents/performance_tuning.py`         | Performance analysis agent                 |
| `ai/agents/knowledge_storage.py`          | Knowledge base health agent                |
| `ai/agents/code_quality_agent.py`         | Code quality agent                         |
| `ai/gaming/scopebuddy.py`                 | Game profiles + MangoHud presets           |
| `ai/gaming/mangohud.py`                   | MangoHud analysis                          |

### Configuration

| Path                                      | Purpose                                    |
|-------------------------------------------|--------------------------------------------|
| `configs/mcp-bridge-allowlist.yaml`       | 48 MCP tool definitions + arg validation   |
| `configs/litellm-config.yaml`             | LiteLLM provider routing (23 models)       |
| `configs/ai-rate-limits.json`             | Per-provider rate limits                   |
| `configs/r2-config.yaml`                  | Cloudflare R2 log archive settings         |
| `configs/keys.env.enc`                    | sops-encrypted API keys (in git)           |

### Integrations (P52)

| Integration | Env Vars | Description |
|-------------|----------|-------------|
| Slack | `SLACK_BOT_TOKEN` | List channels, users, history, post messages |
| Notion | `NOTION_API_KEY` | Search pages, get page content, query databases |

To enable: Add keys to `~/.config/bazzite-ai/keys.env`, then run:
```bash
sops --input-type dotenv --output-type dotenv --encrypt ~/.config/bazzite-ai/keys.env > configs/keys.env.enc
git add configs/keys.env.enc && git commit -m "keys: add Slack/Notion"
```

### Runtime (NOT in git)

| Path                                      | Purpose                                    |
|-------------------------------------------|--------------------------------------------|
| `~/.config/bazzite-ai/keys.env`          | Plaintext API keys (chmod 600)             |
| `~/.config/bazzite-ai/.sops.yaml`        | sops encryption config                     |
| `~/security/vector-db/`                   | LanceDB data (embeddings, log intel)       |
| `~/security/.status`                      | Shared JSON: ClamAV + health state         |
| `~/security/llm-status.json`             | LLM provider health + token usage          |
| `~/security/key-status.json`             | API key presence map                       |
| `~/security/release-watch.json`          | Release watch results                      |
| `~/security/fedora-updates.json`         | Fedora update check results                |
| `/var/log/system-health/`                | Health snapshot logs (90-day rotation)      |
| `/var/log/clamav-scans/`                 | ClamAV scan logs                           |

---

## 13. CLI Command Reference

### Python modules

```bash
source .venv/bin/activate

# Threat intel
python3 -m ai.threat_intel.lookup --hash <sha256>

# RAG
python3 -m ai.rag.query "question here"

# Log intel
python3 -m ai.log_intel --all

# Key manager
python3 -m ai.key_manager           # list all keys (JSON)
python3 -m ai.key_manager status    # categorized summary (exit 1 if missing)
python3 -m ai.key_manager list      # per-key presence

# LLM proxy (foreground)
python3 -m ai.llm_proxy

# MCP bridge (foreground)
python3 -m ai.mcp_bridge
```

### Shell scripts

| Script                          | Purpose                                  | Requires sudo? |
|---------------------------------|------------------------------------------|----------------|
| `scripts/deploy-services.sh`    | Deploy all systemd services              | Yes (internally) |
| `scripts/clamav-scan.sh`        | Run ClamAV scan (quick\|deep)            | Yes            |
| `scripts/system-health-snapshot.sh` | Run health snapshot                  | Yes            |
| `scripts/system-health-test.sh` | 16-test health validation suite          | Yes            |
| `scripts/start-mcp-bridge.sh`   | Start MCP bridge (foreground)            | No             |
| `scripts/start-llm-proxy.sh`    | Start LLM proxy (foreground)             | No             |
| `scripts/manage-keys.sh`        | Interactive key management               | No             |
| `scripts/verify-services.sh`    | Verify all services healthy              | No             |
| `scripts/ingest-docs.sh`        | Ingest docs into LanceDB                | No             |
| `scripts/ingest-code.sh`        | Ingest code into LanceDB                | No             |
| `scripts/rag-query.sh`          | Run RAG query from CLI                   | No             |
| `scripts/rag-embed.sh`          | Run embedding pipeline                   | No             |
| `scripts/threat-lookup.sh`      | Threat intel lookup wrapper              | No             |
| `scripts/code-quality.sh`       | Run ruff + bandit + shellcheck           | No             |
| `scripts/gaming-analyze.sh`     | MangoHud log analysis                    | No             |
| `scripts/gaming-profile.sh`     | Game profile management                  | No             |
| `scripts/backup.sh`             | Full system backup                       | Yes            |
| `scripts/restore.sh`            | Restore from backup                      | Yes            |
| `scripts/integration-test.sh`   | Full integration test suite              | Yes            |
| `scripts/quarantine-release.sh` | Release file from quarantine             | Yes            |
| `scripts/clamav-healthcheck.sh` | ClamAV daemon health check               | No             |
| `scripts/clamav-alert.sh`       | ClamAV email alert handler               | No             |
| `scripts/setup-security-folder.sh` | Initialize ~/security/ structure      | No             |
| `scripts/setup-ai-env.sh`       | Set up Python venv + deps                | No             |
| `scripts/start-security-tray-qt.sh` | Launch PySide6 tray app              | No             |
| `scripts/sentry-test.sh`        | Sentry integration test                  | No             |
| `scripts/usbguard-setup.sh`     | USBGuard configuration                   | Yes            |
| `scripts/luks-upgrade.sh`       | LUKS encryption upgrade                  | Yes            |
| `scripts/update-backup.sh`      | Update backup scripts on flash drive     | Yes            |
| `scripts/deploy.sh`             | Legacy deploy script                     | Yes            |
| `scripts/optimize.sh`           | System optimization                      | No             |
| `scripts/archive-logs-r2.py`    | Upload old logs to Cloudflare R2         | No             |
| `scripts/thermal-protection.py` | Thermal throttle protection              | No             |

### Service management

```bash
# User services (no sudo)
systemctl --user start bazzite-mcp-bridge.service
systemctl --user start bazzite-llm-proxy.service
systemctl --user restart bazzite-mcp-bridge.service
systemctl --user restart bazzite-llm-proxy.service
systemctl --user status bazzite-mcp-bridge.service
systemctl --user status bazzite-llm-proxy.service

# System services (sudo required)
sudo systemctl start system-health.service
sudo systemctl start clamav-quick.service
sudo systemctl enable --now system-health.timer
```

### Testing

```bash
source .venv/bin/activate
python3 -m pytest tests/ -v              # ~1611 tests
python3 -m pytest tests/ -v -k "mcp"     # MCP-related tests only
python3 -m pytest tests/ -v -k "router"  # Router tests only
ruff check ai/ tests/                     # Lint
bandit -r ai/ -c pyproject.toml           # Security scan
```

---

## 14. Resource Budget

The active workload takes priority. When gaming, AI services are throttled. When coding, AI gets normal priority. Resource control is managed via systemd slices and GameMode hooks. The AI layer is designed to stay within a small resource envelope.

| Component                   | RAM     | VRAM   | When active          |
|-----------------------------|---------|--------|----------------------|
| LLM Proxy (llm_proxy.py)   | ~20 MB  | 0      | Always (user service) |
| MCP Bridge (mcp_bridge)     | ~60 MB  | 0      | Always (user service) |
| LanceDB                     | ~10 MB  | 0      | On query only (mmap)  |
| Gemini Embed API            | ~5 MB   | 0      | During embed batches  |
| Ollama + nomic-embed-text   | 0 MB    | 0      | Emergency embed fallback — not loaded by default |
| Threat intel modules         | ~30 MB  | 0      | Per-scan only         |
| PySide6 tray app             | ~80 MB  | 0      | Always (user session) |
| **Total AI overhead**       | **~275 MB** | **0** | **Services + burst** |

The GPU has 6 GB VRAM. Embeddings now use Gemini Embedding 001 (cloud, free),
so VRAM usage is 0 in normal operation. Ollama `nomic-embed-text` is available
as emergency fallback only — not loaded by default. Never run local LLM
generation models on this hardware.

---

## 15. References

### Bazzite / Fedora Atomic

- [Bazzite documentation](https://docs.bazzite.gg/)
- [ujust commands](https://docs.bazzite.gg/Installing_and_Managing_Software/ujust/)
- [Game launch options & env variables](https://docs.bazzite.gg/Gaming/launch-options-env-variables/)
- [Common issues & resolutions](https://docs.bazzite.gg/General/issues_and_resolutions/)
- [FAQ](https://docs.bazzite.gg/General/FAQ/)
- [Package layering (rpm-ostree)](https://docs.bazzite.gg/Installing_and_Managing_Software/rpm-ostree/)
- [Updates, rollbacks & rebasing](https://docs.bazzite.gg/Installing_and_Managing_Software/Updates_Rollbacks_and_Rebasing/)
- [Bazzite vs SteamOS comparison](https://docs.bazzite.gg/General/SteamOS_Comparison/)
- [Bazzite CLI tools](https://docs.bazzite.gg/Advanced/bazzite-cli/)
- [ScopeBuddy (advanced game launch management)](https://docs.bazzite.gg/Advanced/scopebuddy/)

### Gaming

- [ProtonDB (game compatibility)](https://www.protondb.com/)
- [MangoHud GitHub](https://github.com/flightlessmango/MangoHud)
- [GameMode GitHub](https://github.com/FeralInteractive/gamemode)
- [Proton GitHub](https://github.com/ValveSoftware/Proton)

### Security & Privacy

- [ClamAV documentation](https://docs.clamav.net/)
- [ClamAV scanning usage](https://docs.clamav.net/manual/Usage/Scanning.html)
- [Firewalld documentation](https://firewalld.org/documentation/)
- [USBGuard documentation](https://usbguard.github.io/)
- [USBGuard ArchWiki](https://wiki.archlinux.org/title/USBGuard)
- [arkenfox user.js (Firefox hardening)](https://github.com/arkenfox/user.js)
- [EICAR test file info](https://www.eicar.org/download-anti-malware-testfile/)

### Hardware & Monitoring

- [NVIDIA SMI reference](https://developer.nvidia.com/nvidia-system-management-interface)
- [lm-sensors wiki](https://hwmon.wiki.kernel.org/)
- [ArchWiki SMART monitoring](https://wiki.archlinux.org/title/S.M.A.R.T.)
- [smartmontools documentation](https://www.smartmontools.org/wiki/TocDoc)
- [supergfxctl manual](https://asus-linux.org/manual/supergfxctl-manual/)
- [Mission Center](https://missioncenter.io/)

### AI / Development

- [Claude Code documentation](https://code.claude.com/docs/en/)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
- [LiteLLM documentation](https://docs.litellm.ai/)
- [PySide6/Qt6 documentation](https://doc.qt.io/qtforpython-6/)
- [AppIndicator3 (system tray)](https://wiki.ubuntu.com/DesktopExperienceTeam/ApplicationIndicators)

### Notifications & Email

- [msmtp documentation](https://marlam.de/msmtp/)
- [Moonshine STT](https://github.com/moonshine-ai/moonshine)
- [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx)
