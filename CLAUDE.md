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
- scripts/ — shell scripts (clamav, backup, setup, AI wrappers, start-security-tray-qt.sh)
- systemd/ — timer and service unit files
- desktop/ — .desktop files, security.menu, autostart
- configs/ — system config files (udev, sysctl, gamemode, litellm, rate-limits)
- tray/ — PySide6/Qt6 security tray + dashboard (9-state machine, Security/Health/About tabs)
- ai/ — AI enhancement layer (threat intel, RAG, code quality, gaming)
- tests/ — Python unit tests (389 tests)
- docs/ — documentation and guides
- plugins/ — 15 claude-flow plugins (`file:` refs in package.json)

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- Tray launcher: /usr/local/bin/start-security-tray-qt.sh
- Claude Code settings: ~/.claude/settings.json

## Desktop Files
- All custom icons use absolute SVG paths (KDE doesn't resolve custom icon theme names)
- Terminal entries: `konsole -e bash -c '...; echo "Press Enter to close"; read'`
- Never use `konsole --hold` (no visible prompt to close)

## Systemd Hardening
All ClamAV and health services include: NoNewPrivileges, ProtectSystem=strict,
ProtectHome=read-only, PrivateTmp=yes, ReadWritePaths whitelist.

## AI Layer Rules (NEVER violate)
1. **NEVER run local LLM generation models.** Only `nomic-embed-text` (~300MB VRAM) via Ollama.
2. **NEVER store API keys in code, scripts, or git.** Keys: `~/.config/bazzite-ai/keys.env` (chmod 600).
3. **NEVER install Python packages globally.** Use `uv` + project venv at `.venv/`.
4. **NEVER run AI as persistent daemons.** On-demand only. Exception: g4f subprocess (5-min idle timeout, sandboxed).
5. **NEVER call cloud APIs without `ai/rate_limiter.py`.**
6. **NEVER hardcode API providers.** All LLM calls go through `ai/router.py` (LiteLLM).
7. **All shell wrappers in `scripts/`, all Python logic in `ai/`.**
8. **LanceDB at `~/security/vector-db/`.** Not in repo, not in /tmp.
9. **Atomic writes for `~/security/.status`.** Read-modify-write + tmp + mv.

## Claude Code Permissions

**Sandbox:** Runs as user `lch` inside bubblewrap. No root. ALWAYS enabled.
Launch from `~/projects/bazzite-laptop/` — NEVER from $HOME.

**CAN do:** Create/edit files in project, git, pytest, ruff, bandit, shellcheck,
uv, sops, gpg, ollama, curl/wget (user-space), AI Python modules.

**CANNOT do (requires manual terminal):** sudo, systemctl, rpm-ostree, rm -rf,
read *.env/*.key/*.pem, write to /usr/local/bin/ or /etc/, deploy.sh, integration-test.sh.

**Two-Phase Workflow:**
- Phase A: Claude Code creates/edits files + runs approved tools
- Phase B: User manually runs sudo commands (deploy.sh, systemctl)

## Build & Test
```bash
source .venv/bin/activate
python -m pytest tests/ -v        # Run all tests
ruff check ai/ tests/             # Lint
bandit -r ai/ -c pyproject.toml   # Security scan
uv pip install -r requirements.txt # Install deps
```

## Concurrency Rules
- All operations MUST be concurrent/parallel in a single message
- ALWAYS batch ALL file reads/writes/edits in ONE message
- ALWAYS batch ALL Bash commands in ONE message
- ALWAYS spawn ALL agents in ONE message with full instructions
- ALWAYS run background agents for independent work
