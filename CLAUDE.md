# Bazzite Gaming Laptop Project
## System: Acer Predator G3-571 | Bazzite 43 | NVIDIA GTX 1060 + Intel HD 630

## Rules
- This is an immutable OS (Fedora Atomic). Do NOT modify /usr directly.
- Use rpm-ostree for system packages, flatpak for apps.
- Never use sudo rm -rf, curl piped to bash, or wget without permission.
- Custom configs go in /etc/ (survives updates) or ~/.config/ (user configs).
- Test all changes before committing.
- NEVER use PRIME offload env vars in game launch options — they crash games.
- NEVER lower vm.swappiness — 180 is correct for ZRAM.

## Repo Layout
- scripts/ — all shell scripts (clamav, backup, setup utilities, AI wrappers, start-security-tray-qt.sh)
- systemd/ — timer and service unit files
- desktop/ — .desktop files, security.menu, security-tray-qt-autostart.desktop
- configs/ — system config files (udev rules, sysctl, gamemode, litellm, rate-limits, etc.)
- tray/ — PySide6/Qt6 security tray + dashboard (__init__.py, state_machine.py, security_tray_qt.py, dashboard_window.py); 9-state machine; Security/Health/About tabs; KDE notifications; health log parser; pkexec for privileged actions
- ai/ — AI enhancement layer (Python modules: threat intel, RAG, code quality, gaming)
- tests/ — Python unit tests (374 tests: AI layer + tray state machine)
- .vscode/ — VS Code workspace settings and extension recommendations
- docs/ — all documentation and guides (incl. RuFlo v3.5 reference manuals, superpowers/specs/ design specs)

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- MangoHud config: ~/.config/MangoHud/MangoHud.conf
- DNS config: /etc/systemd/resolved.conf.d/dns-over-tls.conf
- WiFi script: /usr/local/bin/public-wifi-mode
- Tray launcher (Qt6): /usr/local/bin/start-security-tray-qt.sh
- Tray launcher (GTK3, legacy): /usr/local/bin/start-security-tray.sh
- Integration tests: /usr/local/bin/integration-test.sh
- Claude Code settings: ~/.claude/settings.json
- Backup scripts: /mnt/backup/ (on USB flash drive sdc3)
- RuFlo reference: docs/RuFlo_v3.5_Reference_Manual.pdf + .docx

## Desktop Files
- All custom icons use absolute SVG paths (KDE doesn't resolve custom icon theme names)
- Terminal-based entries use `konsole -e bash -c '...; echo "Press Enter to close"; read'`
- Never use `konsole --hold` (no visible prompt to close)

## Systemd Hardening
All ClamAV and health services include: NoNewPrivileges, ProtectSystem=strict,
ProtectHome=read-only, PrivateTmp=yes, ReadWritePaths whitelist.

## System Health Monitoring

### Overview
Hardware & performance health monitoring integrated with the existing security
system. Collects SMART disk health, GPU state, CPU thermals, storage/ZRAM stats.

### Health Monitoring Files
| Repo Path | System Path | Purpose |
|-----------|-------------|---------|
| `scripts/system-health-snapshot.sh` | `/usr/local/bin/` | Core health monitor |
| `scripts/system-health-test.sh` | `/usr/local/bin/` | 16-test validation suite |
| `systemd/system-health.service` | `/etc/systemd/system/` | Oneshot service |
| `systemd/system-health.timer` | `/etc/systemd/system/` | Daily 8AM trigger |
| `configs/logrotate-system-health` | `/etc/logrotate.d/system-health` | 90-day log rotation |
| `desktop/security-health-snapshot.desktop` | `~/.local/share/applications/` | KDE menu entry |
| `desktop/security-health-logs.desktop` | `~/.local/share/applications/` | KDE menu entry |

### Health Monitoring Constraints
- Health snapshots must complete in <30 seconds (no long SMART tests inline)
- The --selftest flag handles SMART tests separately with sleep inhibit
- Tray status updates use read-modify-write + atomic write (tmp + rename) to avoid corruption
- .status is shared JSON: ClamAV owns scan keys, health owns health keys — never overwrite the whole file
- Delta file format: simple key=value, one per line in health-deltas.dat
- Never start clamd — that is the scan script's job
- Never modify ~/security/quarantine or ClamAV scan logs
- Email alerts use absolute path /home/lch/.msmtprc (scripts run as root)

### Health Monitoring Commands
| Task | Command (run manually, not from Claude Code) |
|------|------|
| Interactive snapshot | `sudo system-health-snapshot.sh` |
| Snapshot + email | `sudo system-health-snapshot.sh --email` |
| SMART self-test | `sudo system-health-snapshot.sh --selftest` |
| Validation suite | `sudo system-health-test.sh` |
| View latest log | `less /var/log/system-health/health-latest.log` |
| View delta trends | `cat /var/log/system-health/health-deltas.dat` |

### Runtime Paths (not in repo)
- Logs: `/var/log/system-health/health-*.log`
- Latest symlink: `/var/log/system-health/health-latest.log`
- Delta tracking: `/var/log/system-health/health-deltas.dat`
- Tray status: `~/security/.status` (shared with ClamAV, health keys added)

---

## AI Enhancement Layer

### Overview
Cloud-brain AI integrations that enrich the existing security/gaming system.
All AI logic lives in `ai/`. Shell wrappers live in `scripts/`. Nothing runs as
a persistent daemon — everything is on-demand (scan triggers, timers, user action).

### AI Layer Rules (NEVER violate)
1. **NEVER run local LLM generation models.** Only `nomic-embed-text` (~300MB VRAM) via Ollama.
2. **NEVER store API keys in code, scripts, or git.** Keys: `~/.config/bazzite-ai/keys.env` (chmod 600).
3. **NEVER install Python packages globally.** Use `uv` + project venv at `.venv/`.
4. **NEVER run AI as persistent daemons.** On-demand only. Gaming takes priority.
5. **NEVER call cloud APIs without `ai/rate_limiter.py`.** Coordinates cross-script rate limits.
6. **NEVER hardcode API providers.** All LLM calls go through `ai/router.py` (LiteLLM).
7. **All shell wrappers in `scripts/`, all Python logic in `ai/`.**
8. **LanceDB at `~/security/vector-db/`.** Not in repo, not in /tmp. Backed up by backup.sh.
9. **Atomic writes for `~/security/.status`.** Read-modify-write + tmp + mv. Only update AI keys.

### AI Key Paths
| Path | Purpose |
|------|---------|
| `ai/` | All AI Python modules |
| `ai/config.py` | Paths, constants, key loading |
| `ai/router.py` | LiteLLM wrapper for provider routing |
| `ai/rate_limiter.py` | Cross-script rate limit coordinator |
| `ai/threat_intel/` | Phase 1: VT, OTX, MalwareBazaar lookups |
| `ai/rag/` | Phase 2: LanceDB, embeddings, queries |
| `ai/code_quality/` | Phase 3: Linter orchestration, AI fixes |
| `ai/gaming/` | Phase 4: MangoHud analysis, ScopeBuddy |
| `tests/` | Python unit tests |
| `.venv/` | Python virtual environment (managed by uv) |
| `configs/litellm-config.yaml` | LiteLLM provider routing config |
| `configs/ai-rate-limits.json` | Per-provider rate limit definitions |
| `configs/keys.env.enc` | sops-encrypted API keys (IN git) |
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys (chmod 600, NOT in git) |
| `~/security/vector-db/` | LanceDB data (disk-based, backed up) |

### AI Layer Notes
- `litellm`, `rich`, and `python-dotenv` do not expose `__version__`. Use `importlib.metadata.version("package-name")` instead.
- `ai/router.py` is live (not scaffold). Uses `litellm.Router` in-process with lazy init.
- Task types: `fast` (Groq, z.ai), `reason` (Gemini, z.ai, OpenRouter), `batch` (Mistral, Gemini), `code` (z.ai GLM-4-32B), `embed` (Ollama local, Mistral fallback).
- z.ai uses OpenAI-compatible API at `https://api.z.ai/api/paas/v4`. Key: `ZAI_API_KEY`.
- `socksio` is required for httpx SOCKS proxy support (used by litellm in sandboxed environments).

### AI Commands
| Task | Command |
|------|---------|
| Activate AI venv | `source .venv/bin/activate` |
| Run threat lookup | `python -m ai.threat_intel.lookup --hash <sha256>` |
| Run RAG query | `python -m ai.rag.query "question here"` |
| Run all linters | `bash scripts/code-quality.sh` |
| Run AI unit tests | `python -m pytest tests/ -v` |
| Ruff check | `ruff check ai/ tests/` |
| Bandit scan | `bandit -r ai/ -c pyproject.toml` |
| Install/update deps | `uv pip install -r requirements.txt` |
| Test LLM router | `python -c "from ai.config import load_keys; from ai.router import route_query; load_keys(); print(route_query('fast', 'Say hello'))"` |
| Encrypt keys | `cd ~/projects/bazzite-laptop && SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml sops -e --input-type dotenv --output-type dotenv ~/.config/bazzite-ai/keys.env > configs/keys.env.enc` |
| Decrypt keys | `SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml sops -d --input-type dotenv --output-type dotenv configs/keys.env.enc` |

---

## RuFlo Natural Language Integration (MANDATORY)

RuFlo is the master orchestration layer. The user speaks naturally; Claude Code
auto-invokes the matching RuFlo capability. NEVER require the user to type
exact commands — infer intent and invoke automatically.

### Intent → Action Mapping
| User Intent | RuFlo Action |
|---|---|
| build/create/implement | `hooks route` → spawn coder agents |
| review/check/audit | dispatch reviewer/security-architect |
| test/verify | tester agent + pytest |
| fix/debug | systematic-debugging skill |
| design/plan/architect | brainstorming → writing-plans skills |
| learn/remember | `memory store` + `intelligence pattern-store` |
| search/find | `memory search` (HNSW semantic) |
| optimize | perf-analyzer agent |
| secure/protect | security-architect + AIDefence |
| deploy/release | release-manager agent |
| coordinate/parallel | swarm init → spawn agents |

### Always Active
- Daemon running, MCP server active
- Trajectory tracking on multi-step tasks
- Pattern storage after completions
- Model routing (haiku/sonnet/opus per complexity)
- Memory search before re-reading docs

### Master Reference
- GitHub: github.com/ruvnet/ruflo (v3.5.15)
- Local: `docs/RuFlo_v3.5_Reference_Manual.pdf`
- Memory: `reference_ruflo_master_guide.md` (auto-loaded)

---

## Claude Code Permissions (VS Code)

### Sandbox
Claude Code runs as user `lch` inside bubblewrap sandbox. No root access.
Settings at `~/.claude/settings.json`. Sandbox is ALWAYS enabled.
Launch from `~/projects/bazzite-laptop/` — NEVER from $HOME.

### What Claude Code CAN Do
- Create/edit files in `~/projects/bazzite-laptop/`
- Run `git add`, `git commit`, `git push`
- Run Python scripts and `pytest` in the .venv
- Run Ruff, Bandit, ShellCheck on project files
- Create directories under the project root
- Read files anywhere (read-only access outside project)
- **Install tools via `curl`, `wget`, `brew`** (user-space only)
- **Manage Python env via `uv`** (venv, pip install)
- **Run `gpg` and `sops`** for key management
- **Run `ollama`** (pull models, generate embeddings)
- **Run AI Python modules** (threat intel, RAG queries, etc.)

### What Claude Code CANNOT Do (requires manual terminal)
- `sudo` anything — no root commands
- `systemctl enable/start/stop` — no service management
- `rpm-ostree` — no system package management
- `rm -rf` — destructive deletion blocked
- Read `*.env`, `*.key`, `*.pem` files — secrets are runtime-only
- Write to `/usr/local/bin/` — no script deployment
- Write to `/etc/` — no system config changes
- Run `deploy.sh` — requires sudo
- Run `integration-test.sh` — requires sudo

### Approved AI Toolchain (Claude Code can run these directly)
| Tool | What It Does | Install Method |
|------|-------------|----------------|
| `uv` | Python venv + package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `sops` | Encrypt/decrypt API keys | `brew install sops` |
| `gpg` | GPG key management for sops | Pre-installed on Bazzite |
| `ollama` | Local embedding model server | Flatpak or curl installer |
| `ruff` | Python linter/formatter | `uv pip install ruff` (in venv) |
| `bandit` | Python security scanner | `uv pip install bandit` (in venv) |
| `shellcheck` | Bash linter | Pre-installed on Bazzite |
| `pytest` | Python test runner | `uv pip install pytest` (in venv) |

### Security Settings
```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  },
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "deny": [
      "Read(**/.env)", "Read(**/.env.*)", "Read(**/secrets/**)",
      "Read(**/*.key)", "Read(**/*.pem)",
      "Bash(sudo:*)", "Bash(rm -rf:*)",
      "Bash(rpm-ostree:*)", "Bash(systemctl:*)"
    ]
  },
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

---

## RuFlo v3.5 Integration (ALWAYS ACTIVE)

### Mandatory for Every Session
RuFlo (Claude Flow) v3.5.15 is the orchestration backbone. Reference manual at
`docs/RuFlo_v3.5_Reference_Manual.pdf`. ALL operations MUST use RuFlo tools.

### Session Lifecycle (ALWAYS run these)
```bash
# Session start (auto-runs via hooks)
claude-flow daemon start
claude-flow hooks session-start
claude-flow hooks pretrain --depth medium

# Session end
claude-flow hooks session-end
```

### 3-Tier Model Routing (ALWAYS apply)
| Tier | When | Model | Cost |
|------|------|-------|------|
| 1 | Simple transforms, edits | Agent Booster / Haiku | <1ms / $0 |
| 2 | Bug fixes, routine code | Sonnet | ~500ms / $0.0002 |
| 3 | Architecture, security, complex | Opus | 2-5s / $0.015 |

### Agent Training (ALWAYS do)
- `hooks intelligence trajectory-start` before multi-step work
- `hooks intelligence trajectory-step` after each significant action
- `hooks intelligence trajectory-end` when task completes
- `hooks intelligence pattern-store` for reusable learnings
- `hooks pretrain` at session start for codebase analysis

### Memory System (ALWAYS use)
- `memory store` — save patterns, decisions, constraints with HNSW embeddings
- `memory search` — semantic search before re-reading docs (saves tokens)
- Store patterns after successful completions for future agent reuse
- Namespaces: `patterns`, `project`, `reference`, `default`

### Swarm Orchestration (for multi-file/multi-step work)
- `swarm init --topology hierarchical --max-agents 6-8`
- Spawn agents via Claude Code Task tool (not CLI alone)
- ALL agents in ONE message for parallel execution
- Use `raft` consensus, `specialized` strategy
- Anti-drift: swarm init + agent spawn in SAME message

### Hooks (use for quality gates)
- `hooks route` — route tasks to optimal agent type
- `hooks post-task` — record success/failure for learning
- `hooks metrics` — check performance stats
- `hooks intelligence pattern-search` — find similar past solutions

### Skills (invoke via /skill-name)
- `/superpowers:brainstorming` — BEFORE any feature design
- `/superpowers:verification-before-completion` — BEFORE claiming done
- `/superpowers:writing-plans` — for multi-step implementation plans
- `/superpowers:test-driven-development` — for new features
- `/superpowers:systematic-debugging` — for bug investigation

### Security (run after security-related changes)
```bash
claude-flow security scan --depth full
claude-flow hooks intelligence pattern-search --query "security vulnerability"
```

### Available MCP Tools (213+)
All `mcp__claude-flow__*` tools are available. Key categories:
- `memory_*` — store, search, retrieve, delete, stats
- `hooks_intelligence_*` — trajectory tracking, pattern storage, learning
- `hooks_route` — semantic task routing
- `swarm_*` — init, status, health, shutdown
- `agent_*` — spawn, list, status, health, terminate
- `task_*` — create, assign, complete, cancel
- `session_*` — save, restore, list
- `neural_*` — train, predict, patterns, optimize
- `performance_*` — benchmark, bottleneck, metrics

### Token Optimization Rules
1. Use `memory search` before re-reading large docs
2. Route simple tasks to Haiku (Tier 2 low)
3. Batch ALL operations in single messages
4. Store successful patterns for agent reuse
5. Run background agents for independent work
6. Use hierarchical topology to limit drift

---

### Two-Phase Workflow (still applies for system-level changes)
- **Phase A**: Claude Code creates/edits files in the repo + runs approved tools
- **Phase B**: User manually runs sudo commands (deploy.sh, systemctl, integration tests)

Phase B is only needed for deploying to system paths. All development, testing,
venv management, and tool installation is Phase A (Claude Code handles it directly).
