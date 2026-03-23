# Project Instructions — Bazzite AI Layer
## For use by Claude (claude.ai chats), Claude Code (VS Code), and Gemini Pro sessions

### About This Project
This is the **AI enhancement layer** for the bazzite-laptop security/gaming system.
It lives in the SAME git repo (`github.com:violentwave/bazzite-laptop.git`) under the `ai/` directory.
The base security/gaming system is managed in a SEPARATE Claude.ai project called "Bazzite Laptop."

**Both Claude and Gemini work on this project.** Follow all rules regardless of which AI is responding.

---

### System Identity
- **Machine**: Acer Predator G3-571 | Bazzite 43 (KDE6/Wayland)
- **User**: lch
- **GPUs**: NVIDIA GTX 1060 Mobile 6GB + Intel HD 630 (Hybrid mode via supergfxctl)
- **CPU**: Intel i7-7700HQ | **RAM**: 16GB | **ZRAM**: 7.7GB zstd, swappiness=180
- **Internal SSD**: 256GB SK hynix (LUKS encrypted, btrfs)
- **External SSD**: 1.8TB SanDisk Extreme at /run/media/lch/SteamLibrary (ext4)
- **NVIDIA Driver**: 580.95.05 | **CUDA**: 13.0
- **OS type**: Immutable (Fedora Atomic). Use rpm-ostree for system packages, Flatpak for apps, Distrobox for dev environments.
- **Repo**: github.com:violentwave/bazzite-laptop.git (private, SSH key auth)
- **Editor**: VS Code with Claude Code
- **AI code lives in**: `~/projects/bazzite-laptop/ai/`
- **Planning docs**: `docs/` within the repo (authoritative; Setup/ workspace no longer used)

---

### Project State (2026-03-21)

All AI subsystems are implemented and working. 510 tests passing, ruff/bandit clean.

**Newelle-centric architecture**: Everything routes through Newelle (Flatpak GTK4 AI assistant) as the single AI interface. Two user systemd services auto-start on login:
- `bazzite-llm-proxy.service` — OpenAI-compatible LLM router on :8767
- `bazzite-mcp-bridge.service` — FastMCP bridge with 23 tools on :8766

**Claude-flow/RuFlo** is available for manual dev swarm sessions (`npx claude-flow`) but does NOT auto-start. Only 2 plugins installed: code-intelligence, test-intelligence.

**Shell scripts** are retained as CLI fallback for when Newelle or services are unavailable.

---

### Critical Rules — ALWAYS Follow (Both Claude and Gemini)

#### System Rules (Inherited — NEVER violate)
1. **NEVER suggest PRIME offload variables** (`__NV_PRIME_RENDER_OFFLOAD`, `__GLX_VENDOR_LIBRARY_NAME`, `__VK_LAYER_NV_optimus`). They crash Proton games on this hardware.
2. **NEVER lower vm.swappiness** below 180. Bazzite uses ZRAM — high swappiness is required.
3. **NEVER suggest `nvidia-xconfig`** — doesn't exist on Bazzite's immutable filesystem.
4. **NEVER suggest `supergfxctl -m Dedicated`** — only Integrated and Hybrid modes exist.
5. **NEVER suggest ProtonUp-Qt** — this system uses ProtonPlus.
6. **Prefer Flatpak → Homebrew → Distrobox → rpm-ostree** for installing software.

#### AI Layer Rules (NEVER violate)
7. **NEVER run local LLM generation models.** The GTX 1060 has 6GB VRAM — reserved for gaming and Wayland. The ONLY local model allowed is `nomic-embed-text` (~300MB VRAM) for embeddings via Ollama.
8. **NEVER store API keys in code, scripts, or git.** Keys live in `~/.config/bazzite-ai/keys.env` (chmod 600). The sops-encrypted version (`configs/keys.env.enc`) is the only key-related file in git.
9. **NEVER install Python packages globally or with `--break-system-packages`.** Use `uv` and the project venv at `~/projects/bazzite-laptop/.venv/`. This is an immutable OS.
10. **NEVER call cloud APIs without going through `ai/rate_limiter.py`.** Every provider has different limits.
11. **NEVER hardcode API provider choices.** All LLM calls go through `ai/router.py` (LiteLLM wrapper) so providers can be hot-swapped via config.
12. **All shell wrappers go in `scripts/`.** All Python logic goes in `ai/`. Shell scripts are thin wrappers that activate the venv and call Python modules.
13. **LanceDB data lives at `~/security/vector-db/`.** Not in the repo. Not in /tmp. Must be backed up by backup.sh.
14. **The `~/security/.status` JSON file is shared between ClamAV scans, health monitoring, and the tray app.** AI scripts that update it MUST use read-modify-write + atomic rename (tmp + `mv`). NEVER overwrite the entire file. Only update AI-specific keys.

---

### Architecture: Newelle-Centric

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
    │ Starlette  │        │  22 tools           │
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
    │  Shell scripts (CLI fallback)             │
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

### Component Inventory

#### AI Core (`ai/` — ~1620 LOC)

| File | LOC | Purpose | Status |
|------|-----|---------|--------|
| `config.py` | 125 | Paths, constants, scoped key loading | Working |
| `router.py` | 445 | LiteLLM V2 router, health-weighted provider selection | Working |
| `health.py` | 98 | Provider health scoring, auto-demotion (3 failures → 5min cooldown) | Working |
| `llm_proxy.py` | 172 | OpenAI-compatible proxy on :8767 for Newelle | Working |
| `rate_limiter.py` | 256 | Cross-script rate limiting with file locking + atomic writes | Working |
| `mcp_bridge/server.py` | 111 | FastMCP server on :8766, 22 allowlisted tools | Working |
| `mcp_bridge/tools.py` | 351 | Tool implementations (subprocess, file_tail, python) | Working |
| `mcp_bridge/__main__.py` | 63 | Entry point, SIGTERM handler, key guard | Working |

#### AI Subsystems (~5157 LOC total)

| Module | LOC | Purpose | Status |
|--------|-----|---------|--------|
| `threat_intel/` | 657 | VT, OTX, MalwareBazaar hash enrichment | Working |
| `rag/` | 923 | LanceDB vector search, Ollama embeddings | Working |
| `log_intel/` | 1449 | Log ingestion pipeline, anomaly detection, semantic search | Working |
| `gaming/` | 1500 | MangoHud analysis, ScopeBuddy game profiles | Working |
| `code_quality/` | 628 | Linter orchestration (ruff, bandit) + AI fixes | Working |

#### Tray App (`tray/` — 1855 LOC)
PySide6/Qt6 system tray + dashboard. 3 tabs: Security, Health, About. 9-state FSM.

#### Tests (`tests/` — 510 tests)
All passing. Covers: MCP server/tools, router V2, health tracking, rate limiter, threat intel, RAG, log intel, gaming, code quality.

#### Scripts (`scripts/` — 29 shell scripts)
Key scripts: `deploy-services.sh`, `clamav-scan.sh`, `system-health-snapshot.sh`, `start-mcp-bridge.sh`, `start-llm-proxy.sh`, `manage-keys.sh`

---

### Systemd Services

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

Claude-flow (`npx claude-flow`) is available for manual dev sessions but does not auto-start.

---

### Claude Code Constraints (VS Code)

**Claude Code runs sandboxed — it has NO root privileges, but CAN run the approved AI toolchain.**

- Claude Code is installed at `~/.local/bin/claude`
- Settings at `~/.claude/settings.json`
- **Sandbox mode is ALWAYS enabled** (bubblewrap)
- Launch from `~/projects/bazzite-laptop/` — NEVER from $HOME
- Review `git diff` after every session

**What Claude Code CANNOT do (hard-blocked, requires manual terminal):**
- `sudo` anything — no root commands
- `systemctl enable/start/stop` — no service management
- `rpm-ostree` — no system package management
- `rm -rf` — destructive deletion blocked
- Read `*.env`, `*.key`, `*.pem` files — secrets are runtime-only
- Write to `/usr/local/bin/` — no script deployment
- Write to `/etc/` — no system config changes
- Run `deploy-services.sh` — requires sudo
- Run `integration-test.sh` — requires sudo

**What Claude Code CAN do (sandbox-safe + approved toolchain):**
- Create/edit files in `~/projects/bazzite-laptop/`
- Run `git add`, `git commit`, `git push`
- Run Python scripts and `pytest` in the .venv
- Run Ruff, Bandit, ShellCheck on project files
- Create directories under the project root
- Read files anywhere (read-only access outside project)
- `curl`, `wget`, `brew install` (no sudo)
- `uv venv`, `uv pip install`, `source .venv/bin/activate`
- `gpg`, `sops --encrypt`, `sops --decrypt`
- `ollama pull nomic-embed-text` (emergency fallback only — Gemini Embedding 001 is primary)
- `python -m ai.threat_intel.lookup`, `python -m ai.rag.query`, etc.

**Two-phase workflow (only for system-level changes):**
- **Phase A**: Claude Code creates/edits files + runs approved tools (most work)
- **Phase B**: User manually runs sudo commands in terminal (deploy, systemctl, integration tests)

#### Claude Code Plugins in Use
- **`superpowers`** — Enhanced capabilities and multi-step task execution
- **`code-review`** — Automated code review with security focus
- **`feature-dev`** — Feature development workflow with planning and implementation
- **`frontend-design`** — UI/UX design for any web or desktop interfaces

---

### Newelle Integration

**Newelle** = Flatpak GTK4 AI chat/voice assistant.

**Config location**: `~/.var/app/io.github.qwersyk.Newelle/config/glib-2.0/settings/keyfile`

**Connection**:
- LLM: `http://127.0.0.1:8767/v1/` (OpenAI-compat, model="fast")
- MCP: `http://127.0.0.1:8766/mcp` (Bazzite System Tools, 22 tools)

**System prompt** instructs Newelle to:
1. Call MCP tools FIRST for system queries, then explain
2. Keep responses concise (2-3 sentences or bullet points)
3. Never guess stats when a tool can answer
4. composefs 100% is normal (immutable OS layer)
5. Health check protocol: batch 5 core tools, then summarize

---

### MCP Bridge Tools (22 total)

| Tool | Source | Args |
|------|--------|------|
| `system.disk_usage` | subprocess: `df -h` | none |
| `system.cpu_temps` | subprocess: `sensors -j` | none |
| `system.gpu_status` | subprocess: `nvidia-smi` | none |
| `system.memory_usage` | subprocess: `free -h` | none |
| `system.uptime` | subprocess: `uptime` | none |
| `system.service_status` | subprocess: `systemctl show` | none |
| `system.llm_models` | python: read litellm-config.yaml | none |
| `security.last_scan` | file_tail: /var/log/clamav-scans/ | none |
| `security.health_snapshot` | file_tail: /var/log/system-health/ | none |
| `security.status` | json_file: ~/security/.status | none |
| `security.threat_lookup` | python: ai.threat_intel.lookup | hash (regex-validated) |
| `security.run_scan` | python: systemctl start clamav-quick | scan_type (quick\|deep) |
| `security.run_health` | python: systemctl start system-health | none |
| `security.run_ingest` | python: ai.log_intel --all | none |
| `knowledge.rag_query` | python: ai.rag.query (no LLM) | question (max 500 chars) |
| `knowledge.ingest_docs` | python: ai.rag.ingest_docs | none |
| `gaming.profiles` | python: ai.gaming.scopebuddy | none |
| `gaming.mangohud_preset` | python: ai.gaming.scopebuddy | game |
| `logs.health_trend` | python: ai.log_intel.queries | none |
| `logs.scan_history` | python: ai.log_intel.queries | none |
| `logs.anomalies` | python: ai.log_intel.queries | none |
| `logs.search` | python: ai.log_intel.queries | query (max 500 chars) |
| `logs.stats` | python: ai.log_intel.queries | none |
| `health` | built-in | none |

---

### LLM Provider Chain

**Router V2** (`ai/router.py`): health-weighted selection with auto-demotion.

| Task Type | Use Case | Provider Chain |
|-----------|----------|----------------|
| `fast` | Interactive, speed-first | Gemini → Groq → Mistral → OpenRouter → z.ai → Cerebras |
| `reason` | Deep analysis | Gemini → Groq → Mistral → OpenRouter → z.ai |
| `batch` | Volume processing | Gemini → Groq → Mistral → OpenRouter → Cerebras |
| `code` | Code-specialized | Gemini → Groq → Mistral → OpenRouter → z.ai (GLM-4-32B) |
| `embed` | Embeddings (local-first) | Ollama nomic-embed-text → Mistral |

**Health tracking**: success rate + latency → score 0.0-1.0. 3 consecutive failures → auto-demotion with exponential backoff (5min → 10min → 30min max).

---

### Key Paths

| Path | Purpose |
|------|---------|
| `~/projects/bazzite-laptop/ai/` | All AI Python modules |
| `~/projects/bazzite-laptop/.venv/` | Python virtual environment (managed by uv) |
| `~/projects/bazzite-laptop/tests/` | Python unit tests |
| `~/projects/bazzite-laptop/configs/litellm-config.yaml` | LiteLLM provider routing |
| `~/projects/bazzite-laptop/configs/ai-rate-limits.json` | Per-provider rate limit definitions |
| `~/projects/bazzite-laptop/configs/mcp-bridge-allowlist.yaml` | MCP tool definitions |
| `~/projects/bazzite-laptop/configs/keys.env.enc` | sops-encrypted API keys (IN git) |
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys (chmod 600, NOT in git) |
| `~/.config/bazzite-ai/.sops.yaml` | sops encryption rules |
| `~/security/vector-db/` | LanceDB data (disk-based, backed up) |
| `~/security/.status` | Shared JSON: ClamAV + health + AI (atomic writes only) |
| `/var/log/system-health/` | Health snapshot logs (90-day rotation) |
| `/var/log/clamav-scans/` | ClamAV scan logs |
| `.claude-flow/memory.db` | HNSW session memory (claude-flow dev sessions) |

---

### Repo Layout
```
~/projects/bazzite-laptop/
├── ai/                          # All AI Python modules
│   ├── config.py                # Paths, constants, key loading
│   ├── router.py                # LiteLLM V2 wrapper (health-weighted)
│   ├── health.py                # Provider health scoring
│   ├── llm_proxy.py             # OpenAI-compatible proxy (:8767)
│   ├── rate_limiter.py          # Cross-script rate limit coordinator
│   ├── mcp_bridge/              # FastMCP server + tools (:8766)
│   ├── threat_intel/            # VT, OTX, MalwareBazaar
│   ├── rag/                     # LanceDB, embeddings, queries
│   ├── log_intel/               # Log ingestion, anomaly detection
│   ├── code_quality/            # Linter orchestration, AI fixes
│   └── gaming/                  # MangoHud analysis, ScopeBuddy
├── tray/                        # PySide6/Qt6 tray app + dashboard
├── tests/                       # Python unit tests (510)
├── configs/
│   ├── litellm-config.yaml      # 23 models across 5 task types
│   ├── mcp-bridge-allowlist.yaml # 22 MCP tool definitions
│   ├── ai-rate-limits.json      # Rate limit definitions
│   └── keys.env.enc             # sops-encrypted keys
├── scripts/                     # Shell wrappers (29 scripts)
├── systemd/                     # Service + timer units
├── plugins/                     # 2 RuFlo plugins (code-intelligence, test-intelligence)
├── pyproject.toml               # Ruff, Bandit, pytest config
├── requirements.txt             # Python dependencies (32 packages)
└── package.json                 # Node.js deps (claude-flow + 2 plugins)
```

---

### Testing

```bash
source ~/projects/bazzite-laptop/.venv/bin/activate

# Run all tests
python -m pytest tests/ -v              # 510 tests

# Linting
ruff check ai/ tests/
bandit -r ai/ -c pyproject.toml

# Manual AI commands
python -m ai.threat_intel.lookup --hash <sha256>
python -m ai.rag.query "What GPU errors happened last week?"
python -m ai.log_intel --all

# Service health
systemctl --user status bazzite-llm-proxy
systemctl --user status bazzite-mcp-bridge
curl -s http://127.0.0.1:8767/v1/models
```

---

### Gemini Pro Usage Notes

Gemini Pro is used alongside Claude for this project via Google AI Studio / Gemini API.

**Gemini's strengths**: 2M token context window for full codebase analysis, multimodal input (MangoHud screenshots), fast embeddings.

**Gemini must follow the same rules as Claude.** Copy the Critical Rules section into any Gemini conversation.

**When to use Gemini vs Claude:**
- Gemini: massive context analysis (full log dumps, codebase review), multimodal tasks
- Claude: complex reasoning, code generation, security analysis, architecture decisions
- Both: brainstorming, planning, documentation review

---

### Known Active Issues (2026-03-21)

1. **Security status shows WARNING** — smartctl not found, needs investigation
2. **Scan result=error** — Eicar test files stuck in quarantine with chattr +i (need sudo cleanup)
3. **Log DB slightly stale** — Needs periodic re-ingest via `python -m ai.log_intel --all`
4. **npm audit** — 4 moderate vulns in esbuild/vite/vitest dev chain (not production, not urgent)

---

### What This Project Does NOT Cover

The base security/gaming system is managed in the "Bazzite Laptop" Claude.ai project:
- ClamAV scanning, quarantine, email alerts (base behavior)
- USBGuard, firewalld, SELinux configuration
- System health monitoring scripts (base behavior)
- GPU/display configuration, gaming setup, launch options
- Systemd service hardening, KDE Security menu structure
- Backup/restore procedures, LUKS encryption
- Browser hardening, service optimization

---

### Removed in Cleanup (2026-03-21)

These components were evaluated and removed:
- `ai/g4f_manager.py` — disabled, privacy risk, GPL v3 contamination
- `ai/mcp_bridge/claude_flow_proxy.py` — :8768 proxy for claude-flow (no longer auto-starts)
- `systemd/bazzite-claude-flow-mcp.service` — proxy service
- `systemd/claude-flow.service` — RuFlo auto-start daemon
- `systemd/agentdb-sleep-cycle.{service,timer}` — AgentDB weekly maintenance
- `scripts/agentdb-sleep-cycle.sh` — consolidation script
- 13 RuFlo plugins (~450MB) — domain-specific and redundant orchestration plugins
- `g4f[slim]` from requirements.txt

### Software NOT to Use (Evaluated and Rejected)

| Software | Why Skip |
|---|---|
| **Local LLM generation** (Qwen, DeepSeek, etc.) | 3-8 tok/s on GTX 1060 is unusable. Monopolizes VRAM. |
| **ChromaDB** | HNSW index lives in RAM. LanceDB (disk-based) is better for 16GB. |
| **g4f** | GPL v3, routes through unknown third-party proxies, privacy risk. |
| **Puter.js** | Third-party proxy, no SLA. |
| **DuckDuckGo AI wrappers** | Reverse-engineered unofficial APIs. |
| **SonarQube** | 2-4GB RAM + Elasticsearch. Too heavy. |
| **Wazuh** | Full SIEM needing 4-8GB RAM. |

---

### Resource Budget

| Component | RAM | VRAM | When Active |
|---|---|---|---|
| LLM Proxy (llm_proxy.py) | ~20MB | 0 | Always (user service) |
| MCP Bridge (mcp_bridge) | ~60MB | 0 | Always (user service) |
| LanceDB | ~10MB (mmap) | 0 | On query only |
| Ollama + nomic-embed-text | ~200MB | ~300MB | Embedding only, then unloads |
| threat-intel.py | ~30MB | 0 | Per-scan only |
| **Total AI overhead** | **~320MB** | **~300MB** | **Services + burst** |

The active workload takes priority. When gaming, AI services are throttled. When coding, AI gets normal priority. Resource control is managed via systemd slices and GameMode hooks.
