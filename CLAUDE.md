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
- scripts/ — all shell scripts (clamav, backup, setup utilities, AI wrappers)
- systemd/ — timer and service unit files
- desktop/ — .desktop files and security.menu
- configs/ — system config files (udev rules, sysctl, gamemode, litellm, rate-limits, etc.)
- tray/ — security tray app (Python) + 7 SVG icons (9-state machine)
- ai/ — AI enhancement layer (Python modules: threat intel, RAG, code quality, gaming)
- tests/ — Python unit tests for the AI layer
- .vscode/ — VS Code workspace settings and extension recommendations
- docs/ — all documentation and guides

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- MangoHud config: ~/.config/MangoHud/MangoHud.conf
- DNS config: /etc/systemd/resolved.conf.d/dns-over-tls.conf
- WiFi script: /usr/local/bin/public-wifi-mode
- Tray launcher: /usr/local/bin/start-security-tray.sh
- Integration tests: /usr/local/bin/integration-test.sh
- Claude Code settings: ~/.claude/settings.json
- Backup scripts: /mnt/backup/ (on USB flash drive sdc3)

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
| Encrypt keys | `sops --config ~/.config/bazzite-ai/.sops.yaml --input-type dotenv --output-type dotenv -e ~/.config/bazzite-ai/keys.env > configs/keys.env.enc` |
| Decrypt keys | `sops --config ~/.config/bazzite-ai/.sops.yaml --input-type dotenv --output-type dotenv -d configs/keys.env.enc` |

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

### Two-Phase Workflow (still applies for system-level changes)
- **Phase A**: Claude Code creates/edits files in the repo + runs approved tools
- **Phase B**: User manually runs sudo commands (deploy.sh, systemctl, integration tests)

Phase B is only needed for deploying to system paths. All development, testing,
venv management, and tool installation is Phase A (Claude Code handles it directly).
