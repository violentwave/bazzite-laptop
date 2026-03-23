# Bazzite AI Layer — Agent Reference
<!-- System: Acer Predator G3-571 | Bazzite 43 | Last updated: 2026-03-22 -->

Quick-reference for AI assistants (Claude Code, Newelle, Gemini) working on
this codebase. See `docs/project-onboarding.md` for detailed constraints and
`docs/newelle-integration.md` for MCP bridge internals.

---

## Architecture

```
Newelle (Flatpak GTK4)
  │
  ├── MCP tools ──► bazzite-mcp-bridge  127.0.0.1:8766  (FastMCP)
  │                 ai/mcp_bridge/server.py — 43 tools
  │
  └── LLM chat  ──► bazzite-llm-proxy   127.0.0.1:8767  (OpenAI-compat)
                    ai/llm_proxy.py — 6 cloud providers
```

Both services auto-start on login as systemd user services. Both bind to
127.0.0.1 only. Neither talks to 0.0.0.0.

---

## MCP Tools (43 total)

### system.*

| Tool | Source | Description |
|------|--------|-------------|
| `system.disk_usage` | command: `df -h` | Disk usage |
| `system.cpu_temps` | command: `sensors -j` | CPU temperatures (JSON) |
| `system.gpu_status` | command: `nvidia-smi` | GPU temp, VRAM, power |
| `system.memory_usage` | command: `free -h` | RAM + ZRAM usage |
| `system.uptime` | command: `uptime` | System uptime and load |
| `system.service_status` | command: `systemctl show` | Status of 4 key services |
| `system.llm_models` | python | Available LLM modes + provider chains |
| `system.mcp_manifest` | python | All tools with descriptions and args |
| `system.llm_status` | json_file: `~/security/llm-status.json` | Provider health, token usage |
| `system.key_status` | json_file: `~/security/key-status.json` | API key presence (never values) |
| `system.release_watch` | json_file: `~/security/release-watch.json` | Upstream release updates (GitHub, GHSA) |
| `system.fedora_updates` | json_file: `~/security/fedora-updates.json` | Fedora/Bazzite pending updates (Bodhi) |
| `system.pkg_intel` | python: `ai.system.pkg_intel` | Package advisories via deps.dev |

### security.*

| Tool | Source | Description |
|------|--------|-------------|
| `security.last_scan` | file_tail: `/var/log/clamav-scans/` | Last 20 lines of latest ClamAV log |
| `security.health_snapshot` | file_tail: `/var/log/system-health/` | Last 30 lines of latest health log |
| `security.status` | json_file: `~/security/.status` | Filtered status JSON (6 keys) |
| `security.threat_lookup` | python: `ai.threat_intel.lookup` | Hash lookup (VT + OTX + MalwareBazaar) |
| `security.ip_lookup` | python: `ai.threat_intel.ip_lookup` | IP reputation (AbuseIPDB + GreyNoise + Shodan) |
| `security.url_lookup` | python: `ai.threat_intel.ioc_lookup` | URL/IOC lookup (URLhaus + ThreatFox + CIRCL) |
| `security.cve_check` | python: `ai.threat_intel.cve_scanner` | CVE scan (NVD + OSV + CISA KEV) |
| `security.sandbox_submit` | python: `ai.threat_intel.sandbox` | Submit quarantine file to Hybrid Analysis |
| `security.threat_summary` | python: `ai.threat_intel.summary` | Compile summary from all report dirs |
| `security.run_scan` | python | Trigger ClamAV scan via systemctl |
| `security.run_health` | python | Trigger health snapshot via systemctl |
| `security.run_ingest` | python | Trigger log pipeline re-ingestion |

### knowledge.*

| Tool | Source | Description |
|------|--------|-------------|
| `knowledge.rag_query` | python: `ai.rag.query` | Semantic search — raw context chunks (no LLM) |
| `knowledge.rag_qa` | python: `ai.rag.query` | LLM-synthesized answer from knowledge base |
| `knowledge.ingest_docs` | python: `ai.rag.ingest_docs` | Re-embed docs/ into LanceDB |

### gaming.*

| Tool | Source | Description |
|------|--------|-------------|
| `gaming.profiles` | python: `ai.gaming.scopebuddy` | List configured game profiles |
| `gaming.mangohud_preset` | python: `ai.gaming.scopebuddy` | MangoHud preset for a game |

### logs.*

| Tool | Source | Description |
|------|--------|-------------|
| `logs.health_trend` | python: `ai.log_intel.queries` | Last 7 health snapshots with deltas |
| `logs.scan_history` | python: `ai.log_intel.queries` | Last 10 ClamAV scan results |
| `logs.anomalies` | python: `ai.log_intel.queries` | Unacknowledged anomalies |
| `logs.search` | python: `ai.log_intel.queries` | Semantic search across system logs |
| `logs.stats` | python: `ai.log_intel.queries` | Log pipeline statistics |

### code.*

| Tool | Source | Description |
|------|--------|-------------|
| `code.search` | python: ripgrep | Pattern search across Python source |
| `code.rag_query` | python: `ai.rag.code_query` | Semantic search over indexed code |

### agents.*

| Tool | Source | Description |
|------|--------|-------------|
| `agents.security_audit` | python: `ai.agents.security_audit` | Scan + health + ingest + RAG summary |
| `agents.performance_tuning` | python: `ai.agents.performance_tuning` | Temps, memory, disk, gaming profiles |
| `agents.knowledge_storage` | python: `ai.agents.knowledge_storage` | Vector DB health + Ollama status |
| `agents.code_quality` | python: `ai.agents.code_quality_agent` | ruff + bandit + git status |

### Built-in

| Tool | Description |
|------|-------------|
| `health` | Returns `{"status": "ok", "tools": 43}` |

---

## Systemd Timers (12 total)

| Timer | Service | Schedule | Purpose |
|-------|---------|----------|---------|
| `system-health.timer` | `system-health.service` | Daily 8AM | Hardware health snapshot |
| `clamav-quick.timer` | `clamav-quick.service` | Hourly | ClamAV quick scan |
| `clamav-deep.timer` | `clamav-deep.service` | Weekly Sunday | ClamAV full scan |
| `clamav-healthcheck.timer` | `clamav-healthcheck.service` | Daily | ClamAV daemon check |
| `rag-embed.timer` | `rag-embed.service` | Periodic | Re-ingest logs into LanceDB |
| `security-audit.timer` | `security-audit.service` | Scheduled | Automated security audit |
| `performance-tuning.timer` | `performance-tuning.service` | Scheduled | Performance analysis |
| `knowledge-storage.timer` | `knowledge-storage.service` | Scheduled | Knowledge base health |
| `cve-scanner.timer` | `cve-scanner.service` | Weekly | CVE scan of installed packages |
| `release-watch.timer` | `release-watch.service` | Daily | GitHub Releases + GHSA check |
| `fedora-updates.timer` | `fedora-updates.service` | Daily | Fedora Bodhi update check |
| `log-archive.timer` | `log-archive.service` | Weekly Sunday 01:00 | Upload old logs to R2 |

---

## Cloud Providers (6)

| Provider | Task Types | Key Var |
|----------|-----------|---------|
| Google Gemini | fast, reason, batch, code, embed | `GEMINI_API_KEY` |
| Groq | fast, reason, batch, code | `GROQ_API_KEY` |
| Mistral | fast, reason, batch, code, embed | `MISTRAL_API_KEY` |
| OpenRouter | fast, reason, batch, code | `OPENROUTER_API_KEY` |
| z.ai | fast, reason, code (GLM-4-32B) | `ZAI_API_KEY` |
| Cerebras | fast, batch | `CEREBRAS_API_KEY` |
| Ollama (local) | embed emergency fallback only | — |

Health-weighted selection: 3 failures → auto-demotion, exponential backoff
(5 min → 10 min → 30 min max).

Embed chain: Gemini Embedding 001 (primary, free 10M TPM) → Cohere embed-english-v3.0 (fallback) → Ollama nomic-embed-text (emergency, not loaded by default).

**Stream recovery**: 2KB commit threshold. Pre-commit failure → retry next provider. Post-commit → fatal (partial output already sent).

---

## Key Paths

| Path | Purpose |
|------|---------|
| `ai/mcp_bridge/server.py` | FastMCP server, tool registration |
| `ai/mcp_bridge/tools.py` | All 43 tool dispatch handlers |
| `ai/llm_proxy.py` | OpenAI-compat proxy, model→task type mapping |
| `ai/router.py` | LiteLLM V2 router |
| `ai/health.py` | Provider health + auto-demotion |
| `ai/rate_limiter.py` | Cross-script rate limiting |
| `ai/config.py` | Paths, scoped key loading |
| `ai/key_manager.py` | API key presence checker |
| `configs/mcp-bridge-allowlist.yaml` | 43 tool definitions + arg validation |
| `configs/litellm-config.yaml` | LiteLLM provider routing |
| `configs/ai-rate-limits.json` | Per-provider rate limits |
| `configs/keys.env.enc` | sops-encrypted API keys (in git) |
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys (chmod 600, not in git) |
| `~/security/vector-db/` | LanceDB data (embeddings, log intel) |
| `~/security/.status` | Shared JSON: ClamAV + health state |
| `~/security/llm-status.json` | LLM provider health + token usage |
| `~/security/key-status.json` | API key presence map |
| `~/security/release-watch.json` | Release watch results |
| `~/security/fedora-updates.json` | Fedora update check results |

---

## Build & Test

```bash
source .venv/bin/activate
python -m pytest tests/ -v          # 998 tests
ruff check ai/ tests/               # Lint
bandit -r ai/ -c pyproject.toml     # Security scan
uv pip install -r requirements.txt  # Install/update deps
```

---

## OpenCode (z.ai GLM-5)

Secondary coding agent for audits, reviews, and small targeted edits.

**Config:** `opencode.json` in project root (not in git)
**Instructions:** `.opencode/AGENTS.md`
**Shared context:** `.claude-flow/SHARED-CONTEXT.md` (read by both agents)
**MCP access:** bazzite-tools via mcp-remote → 127.0.0.1:8766/mcp
**LLM provider:** z.ai GLM-5 (direct, not through local proxy)

OpenCode follows the same rules as Claude Code. It cannot run sudo, read .env files, or push to git. Use for read-heavy audits and small config fixes. Defer multi-file refactors to Claude Code.

---

## NEVER Violate

1. No local LLM generation models — Ollama `nomic-embed-text` is emergency embed fallback only (Gemini Embedding 001 is primary)
2. No API keys in code, scripts, or git
3. No `ai.router` import inside `ai/mcp_bridge/` process
4. No `shell=True` in subprocess calls
5. No writes to `~/security/.status` without read-modify-write + atomic rename
6. No global pip installs — `uv` + `.venv/` only
7. No `/usr` modifications — immutable OS (Fedora Atomic)
8. No PRIME offload env vars — they crash Proton/Vulkan on this hardware

---

## Claude Code Constraints (VS Code)

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

---

## Gemini Pro Usage Notes

Gemini Pro is used alongside Claude for this project via Google AI Studio / Gemini API.

**Gemini's strengths**: 2M token context window for full codebase analysis, multimodal input (MangoHud screenshots), fast embeddings via Gemini Embedding 001.

**Gemini must follow the same rules as Claude.** Copy the NEVER Violate section into any Gemini conversation.

**When to use Gemini vs Claude:**
- Gemini: massive context analysis (full log dumps, codebase review), multimodal tasks
- Claude: complex reasoning, code generation, security analysis, architecture decisions
- Both: brainstorming, planning, documentation review

---

## Software NOT to Use

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

## Known Active Issues

1. **Security status shows WARNING** — smartctl not found, needs investigation
2. **Scan result=error** — Eicar test files stuck in quarantine with chattr +i (need sudo cleanup)
3. **Log DB slightly stale** — Needs periodic re-ingest via `python -m ai.log_intel --all`
4. **npm audit** — 4 moderate vulns in esbuild/vite/vitest dev chain (not production, not urgent)
