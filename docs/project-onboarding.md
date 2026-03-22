# Bazzite Gaming Laptop — Project Onboarding

> Single reference document for AI assistants working on this codebase.
> Hardware: Acer Predator G3-571 | Bazzite 43 (Fedora Atomic) | NVIDIA GTX 1060 + Intel HD 630

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Newelle (Flatpak GTK4)                │
│                  AI chat/voice assistant                 │
│        LLM: localhost:8767    MCP: localhost:8766        │
└─────────┬──────────────────────┬────────────────────────┘
          │                      │
    ┌─────▼──────┐        ┌──────▼──────────────┐
    │ LLM Proxy  │        │  MCP Bridge         │
    │ :8767      │        │  :8766 (FastMCP)    │
    │ Starlette  │        │  33 tools           │
    └─────┬──────┘        └──────┬──────────────┘
          │                      │
    ┌─────▼──────┐        ┌──────▼──────────────┐
    │ ai/router  │        │  ai/mcp_bridge/     │
    │ LiteLLM V2 │        │  tools.py           │
    │ health.py  │        │  (subprocess/python) │
    └─────┬──────┘        └──────┬──────────────┘
          │                      │
    ┌─────▼──────────────────────▼──────────────┐
    │         Cloud LLM Providers                │
    │  Gemini → Groq → Mistral → OpenRouter     │
    │  → z.ai → Cerebras                        │
    └───────────────────────────────────────────┘

    ┌───────────────────────────────────────────┐
    │         System Layer                       │
    │  ClamAV (scans) ← systemd timers          │
    │  Health snapshots ← daily 8AM             │
    │  LanceDB (~/security/vector-db/)          │
    │  Tray app (PySide6/Qt6)                   │
    │  ~/security/.status (shared JSON)         │
    └───────────────────────────────────────────┘
```

### Service Ports

| Port | Service | Process | Protocol |
|------|---------|---------|----------|
| 8766 | MCP Bridge | `python -m ai.mcp_bridge` | FastMCP streamable-http |
| 8767 | LLM Proxy | `python -m ai.llm_proxy` | OpenAI-compatible REST |
| 11434 | Ollama | system service | Ollama API (embeddings only) |

All bind to **127.0.0.1 only** — enforced at startup, never 0.0.0.0.

---

## Critical Constraints (NEVER Violate)

### AI Layer Rules
1. **NEVER run local LLM generation models.** Only `nomic-embed-text` (~300MB VRAM) via Ollama.
2. **NEVER store API keys in code, scripts, or git.** Keys: `~/.config/bazzite-ai/keys.env` (chmod 600).
3. **NEVER install Python packages globally.** Use `uv` + project venv at `.venv/`.
4. **NEVER run AI as persistent daemons** except: bazzite-mcp-bridge and bazzite-llm-proxy (user systemd services).
5. **NEVER call cloud APIs without `ai/rate_limiter.py`.** All calls are rate-limited.
6. **NEVER hardcode API providers.** All LLM calls go through `ai/router.py`.

### MCP Bridge Security
- NEVER import `ai/router.py` in the bridge process (loads all keys unscoped)
- NEVER use `shell=True` in subprocess calls
- All tools are read-only — no system mutations
- Static command lists, no user argument interpolation
- Output truncated to 4KB, paths redacted

### System Rules
- Immutable OS: NEVER modify `/usr` — use `rpm-ostree` for packages, `flatpak` for apps
- NEVER use PRIME offload env vars in game launch options (crashes games)
- NEVER lower `vm.swappiness` — 180 is correct for ZRAM
- `~/security/.status` is shared JSON: ClamAV owns scan keys, health owns health keys — atomic writes only

### Claude Code Sandbox
- Runs as user `lch` in bubblewrap, no root
- **CAN**: edit project files, git, pytest, ruff, bandit, uv, ollama, curl
- **CANNOT**: sudo, systemctl, rpm-ostree, write to /usr or /etc, read .env/.key files
- Two-phase workflow: Phase A (Claude Code edits), Phase B (user runs sudo commands)

---

## Component Inventory

### AI Core (`ai/`)

| File | Purpose | Status |
|------|---------|--------|
| `config.py` | Paths, constants, scoped key loading | Working |
| `router.py` | LiteLLM V2 router, health-weighted provider selection | Working |
| `health.py` | Provider health scoring, auto-demotion (3 failures → 5min cooldown) | Working |
| `llm_proxy.py` | OpenAI-compatible proxy on :8767 for Newelle, opt-in conversation memory | Working |
| `rate_limiter.py` | Cross-script rate limiting with file locking + atomic writes | Working |
| `key_manager.py` | API key presence checker, writes `~/security/key-status.json` | Working |
| `mcp_bridge/server.py` | FastMCP server on :8766, 33 allowlisted tools | Working |
| `mcp_bridge/tools.py` | Tool implementations (subprocess, file_tail, python) | Working |
| `mcp_bridge/__main__.py` | Entry point, SIGTERM handler, key guard | Working |

### AI Subsystems

| Module | Purpose | Status |
|--------|---------|--------|
| `threat_intel/` | VT, OTX, MalwareBazaar hash enrichment | Working |
| `rag/` | LanceDB vector search, Ollama embeddings, opt-in conversation memory | Working |
| `log_intel/` | Log ingestion pipeline, anomaly detection, semantic search | Working |
| `gaming/` | MangoHud analysis, ScopeBuddy game profiles | Working |
| `code_quality/` | Linter orchestration (ruff, bandit) + AI fixes | Working |
| `agents/` | security_audit, performance_tuning, knowledge_storage, code_quality agents | Working |

### Tray App (`tray/` — 1855 LOC)
PySide6/Qt6 system tray + dashboard. 3 tabs: Security, Health, About. 9-state FSM.

### Tests (`tests/` — 733 tests)
All passing. Covers: MCP server/tools, router V2, health tracking, rate limiter, threat intel, RAG, log intel, gaming, code quality, key manager, conversation memory, dashboard/tray.

### Scripts (`scripts/` — 29 shell scripts)
Key scripts: `deploy-services.sh`, `clamav-scan.sh`, `system-health-snapshot.sh`, `start-mcp-bridge.sh`, `start-llm-proxy.sh`, `manage-keys.sh`

### Systemd Units

**User services** (auto-start on login):

| Unit | Purpose |
|------|---------|
| `bazzite-llm-proxy.service` | LLM router proxy (:8767) |
| `bazzite-mcp-bridge.service` | MCP bridge for Newelle (:8766) |

**System services** (require sudo):

| Timer | Service | Schedule |
|-------|---------|----------|
| `system-health.timer` | `system-health.service` | Daily 8AM |
| `clamav-quick.timer` | `clamav-quick.service` | Hourly |
| `clamav-deep.timer` | `clamav-deep.service` | Weekly |
| `log-archive.timer` | `log-archive.service` | Weekly Sunday 01:00 — upload logs to R2 |

Claude-flow (`npx claude-flow`) is available for manual dev sessions but does not auto-start.

### Configs (`configs/`)

| File | Purpose |
|------|---------|
| `litellm-config.yaml` | 23 LLM models across 5 task types (fast/reason/batch/code/embed) |
| `mcp-bridge-allowlist.yaml` | 33 MCP tool definitions with arg validation |
| `ai-rate-limits.json` | Per-provider rate limits (rpm/rpd/tokens) |
| `keys.env.enc` | sops-encrypted API keys (IN git) |
| `logrotate-system-health` | 90-day log rotation |
| `r2-config.yaml` | Cloudflare R2 endpoint, bucket, dirs, retention settings |

### Plugins (2 RuFlo v3 plugins)
Installed via `file:` refs in `package.json`: code-intelligence (semantic search, refactor impact), test-intelligence (predictive test selection, flaky detection).

---

## LLM Provider Chain

**Router V2** (`ai/router.py`): health-weighted selection with auto-demotion.

| Task Type | Use Case | Provider Chain |
|-----------|----------|----------------|
| `fast` | Interactive, speed-first | Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras |
| `reason` | Deep analysis | Gemini → Groq → Mistral → OpenRouter → z.ai |
| `batch` | Volume processing | Gemini → Groq → Mistral → OpenRouter → Cerebras |
| `code` | Code-specialized | Gemini → Groq → Mistral → OpenRouter → z.ai (GLM-4-32B) |
| `embed` | Embeddings (local-first) | Ollama nomic-embed-text → Mistral |

**Health tracking**: success rate + latency → score 0.0-1.0. 3 consecutive failures → auto-demotion with exponential backoff (5min → 10min → 30min max).

**Stream recovery**: 2KB commit threshold. Pre-commit failure → retry next provider. Post-commit → fatal (partial output already sent).

---

## MCP Bridge Tools (33 total)

| Tool | Source | Args |
|------|--------|------|
| `system.disk_usage` | subprocess: `df -h` | none |
| `system.cpu_temps` | subprocess: `sensors -j` | none |
| `system.gpu_status` | subprocess: `nvidia-smi` | none |
| `system.memory_usage` | subprocess: `free -h` | none |
| `system.uptime` | subprocess: `uptime` | none |
| `system.service_status` | subprocess: `systemctl show` | none |
| `system.llm_models` | python: read litellm-config.yaml | none |
| `system.mcp_manifest` | python: list all tools | none |
| `system.llm_status` | json_file: ~/security/llm-status.json | none |
| `system.key_status` | json_file: ~/security/key-status.json | none |
| `security.last_scan` | file_tail: /var/log/clamav-scans/ | none |
| `security.health_snapshot` | file_tail: /var/log/system-health/ | none |
| `security.status` | json_file: ~/security/.status | none |
| `security.threat_lookup` | python: ai.threat_intel.lookup | hash (regex-validated) |
| `security.run_scan` | python: systemctl start clamav-quick | scan_type (quick\|deep) |
| `security.run_health` | python: systemctl start system-health | none |
| `security.run_ingest` | python: ai.log_intel --all | none |
| `knowledge.rag_query` | python: ai.rag.query (context chunks) | query (max 500 chars) |
| `knowledge.rag_qa` | python: ai.rag.query (LLM synthesis) | question (max 500 chars) |
| `knowledge.ingest_docs` | python: ai.rag.ingest_docs | none |
| `gaming.profiles` | python: ai.gaming.scopebuddy | none |
| `gaming.mangohud_preset` | python: ai.gaming.scopebuddy | game |
| `logs.health_trend` | python: ai.log_intel.queries | none |
| `logs.scan_history` | python: ai.log_intel.queries | none |
| `logs.anomalies` | python: ai.log_intel.queries | none |
| `logs.search` | python: ai.log_intel.queries | query (max 500 chars) |
| `logs.stats` | python: ai.log_intel.queries | none |
| `code.search` | python: ripgrep over repo | query (max 128 chars) |
| `code.rag_query` | python: ai.rag.code_query | question (max 500 chars) |
| `agents.security_audit` | python: ai.agents.security_audit | none |
| `agents.performance_tuning` | python: ai.agents.performance_tuning | none |
| `agents.knowledge_storage` | python: ai.agents.knowledge_storage | none |
| `agents.code_quality` | python: ai.agents.code_quality_agent | none |
| `health` | built-in | none |

---

## Newelle Integration

**Newelle** = Flatpak GTK4 AI chat/voice assistant (replaces Jarvis).

**Config location**: `~/.var/app/io.github.qwersyk.Newelle/config/glib-2.0/settings/keyfile`

**Connection**:
- LLM: `http://127.0.0.1:8767/v1/` (OpenAI-compat, model="fast")
- MCP: `http://127.0.0.1:8766/mcp` (Bazzite System Tools, 33 tools)

**System prompt** instructs Newelle to:
1. Call MCP tools FIRST for system queries, then explain
2. Keep responses concise (2-3 sentences or bullet points)
3. Never guess stats when a tool can answer
4. composefs 100% is normal (immutable OS layer)
5. Health check protocol: batch 5 core tools, then summarize

---

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.config/bazzite-ai/keys.env` | API keys (chmod 600, NOT in git) |
| `~/security/vector-db/` | LanceDB data (embeddings, log intel) |
| `~/security/.status` | Shared JSON (ClamAV + health state) |
| `/var/log/system-health/` | Health snapshot logs (90-day rotation) |
| `/var/log/clamav-scans/` | ClamAV scan logs |
| `.claude-flow/memory.db` | HNSW session memory (claude-flow dev sessions) |

---

## Known Issues & Pending Work

### Active Issues (as of 2026-03-21)
1. **Security status shows WARNING** — 2 warnings: smartctl not found, system-health.timer was inactive (now fixed)
2. **Scan result=error** — Eicar test files stuck in quarantine with chattr +i (need sudo cleanup)
3. **Log DB slightly stale** — Ingestion ran but only caught 1 new record; needs periodic re-run
4. **health-latest.log symlink** — Can point to empty rotated file; `_read_file_tail` now skips empty files (fixed in tools.py)

### Token Optimization Done
- Removed 219 claude-flow tools from Newelle's MCP config (~12k tokens/turn saved)
- Removed dead claude-flow tool references from Newelle system prompt
- Added health check batching protocol (5 tools → 1 summary instead of 18 sequential calls)

---

## Build & Test

```bash
source .venv/bin/activate
python -m pytest tests/ -v          # 733 tests
ruff check ai/ tests/               # Lint
bandit -r ai/ -c pyproject.toml     # Security scan
uv pip install -r requirements.txt  # Install deps
```

## Deploy

```bash
# No sudo — deploys user services + system services (prompts for sudo internally)
bash scripts/deploy-services.sh
```

## Key Commands

| Task | Command |
|------|---------|
| Test LLM router | `python -c "from ai.config import load_keys; from ai.router import route_query; load_keys(); print(route_query('fast', 'Say hello'))"` |
| Run threat lookup | `python -m ai.threat_intel.lookup --hash <sha256>` |
| Run RAG query | `python -m ai.rag.query "question"` |
| Ingest logs to DB | `python -m ai.log_intel --all` |
| Start MCP bridge | `bash scripts/start-mcp-bridge.sh` |
| Start LLM proxy | `bash scripts/start-llm-proxy.sh` |
| Encrypt keys | `SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml sops -e --input-type dotenv --output-type dotenv ~/.config/bazzite-ai/keys.env > configs/keys.env.enc` |

---

## Dependencies

### Python (requirements.txt — 32 packages)
Core: litellm, lancedb, fastmcp, python-dotenv, pyyaml, rich, tenacity
Threat: vt-py, requests
RAG: pyarrow, ollama
Tray: PySide6
Dev: ruff, bandit, pytest, sentry-sdk

### Node.js (package.json)
Core: @claude-flow/cli, agentic-flow
Plugins: code-intelligence, test-intelligence

### Python 3.12+, Node.js 18+
