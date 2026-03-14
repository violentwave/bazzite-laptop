# Project Instructions — Bazzite Gaming Laptop
## For use by Claude (claude.ai chats) and Claude Code sessions

### System Identity
- **Machine**: Acer Predator G3-571 | Bazzite 42/43 (KDE6/Wayland)
- **User**: lch
- **GPUs**: NVIDIA GTX 1060 Mobile 6GB + Intel HD 630 (Hybrid mode)
- **Key constraint**: nvidia-drm.modeset=1 is set, NVIDIA drives HDMI. PRIME offload env vars crash Proton games — never suggest them.
- **OS type**: Immutable (Fedora Atomic). Use rpm-ostree for system packages, Flatpak for apps, Distrobox for dev environments.

### Critical Rules — Always Follow
1. **NEVER suggest PRIME offload variables** (`__NV_PRIME_RENDER_OFFLOAD`, `__GLX_VENDOR_LIBRARY_NAME`, `__VK_LAYER_NV_optimus`) in game launch options. They crash games on this system.
2. **NEVER lower vm.swappiness** below 180. Bazzite uses ZRAM and needs high swappiness.
3. **NEVER suggest `nvidia-xconfig`** — it doesn't exist on Bazzite's immutable filesystem.
4. **NEVER suggest `ujust enable-gamemode`** — it doesn't exist. GameMode was installed via `rpm-ostree install gamemode`.
5. **NEVER suggest ProtonUp-Qt** — this system uses ProtonPlus instead.
6. **NEVER suggest `supergfxctl -m Dedicated`** — Dedicated mode is not available. Only Integrated and Hybrid are supported.
7. **Prefer Flatpak → Homebrew → Distrobox → rpm-ostree** for installing software. Minimize layered packages.
8. **Always check project documents** before suggesting config changes — the work may already be done.

### Current System State
Refer to these project documents for full details:
- `bazzite-optimization-guide.md` — Master guide with completed/remaining work
- `system-config-snapshot` — Exact system configuration for disaster recovery
- `troubleshooting-log` — Problems already solved, do not re-debug
- `services-optimize-current` — Services audit (all listed services have been disabled)
- `reference-links` — Verified documentation links
- `backup-official-guide.md` — Backup/restore procedures with 5 scenarios

### Completed Setup (Do Not Redo)
- GPU: Hybrid mode, nvidia-drm.modeset=1, dual display (laptop + TV via HDMI)
- Gaming: Steam + Proton Experimental + GE-Proton + GameMode + MangoHud
- Security: SSH disabled, firewall DROP zone (log-denied=all), CUPS disabled, DNS-over-TLS, SELinux enforcing
- Storage: External 1.8TB SSD as Steam library at /run/media/lch/SteamLibrary
- Launch options: `gamemoderun mangohud %command%` for all games, `SteamDeck=1 gamemoderun mangohud %command%` for Marvel Rivals
- MangoHud: F12 toggle overlay, F11 toggle logging
- Services: Disabled avahi, ModemManager, virt*, vbox*, vmtools*, sssd, iscsi*, mdmonitor, raid-check, qemu-guest-agent
- Performance: GameMode config, NVIDIA shader cache 4GB, I/O scheduler mq-deadline, TCP Fast Open
- Security hardening: ClamAV (daily quick + weekly deep scans), USBGuard (12 devices whitelisted), LUKS Argon2id + header backup, firewall log-denied=all
- Email alerts: msmtp + Gmail app password for ClamAV scan notifications
- KDE Security menu: 6 shortcuts in app launcher (quick scan, deep scan, logs, quarantine, firewall, USB devices)
- ~/security/ hub: centralized security folder with status file, quarantine dir, scan logs
- Backup: Unified backup.sh/restore.sh on BazziteBackup flash drive (5 scenarios documented)

### Remaining Work (Prioritized)
1. **Notification system overhaul** — Fancy terminal output, HTML emails, system tray security icon
2. **ScopeBuddy configuration** — Per-game advanced launch management
3. **Proton environment variable testing** — WAYLAND, NTSYNC flags for compatible games
4. **System monitoring tools** — Mission Center, btop, nvtop, smartmontools
5. **AI/Coding setup** (deferred) — Ollama with CUDA, VS Code, local LLMs

### Game Launch Options Quick Reference
| Game | Launch Options |
|------|---------------|
| All games (default) | `gamemoderun mangohud %command%` |
| Marvel Rivals | `SteamDeck=1 gamemoderun mangohud %command%` |

### How to Use Claude Code on This System

#### Authentication
Claude Code is installed at `~/.local/bin/claude`. Authenticate by running `claude` in terminal — it opens browser for OAuth with your Claude.ai account. Credentials stored in `~/.claude/`.

#### Security Setup (Do First)
1. Enable sandbox: run `/sandbox` inside Claude Code on first launch
2. Apply settings to `~/.claude/settings.json`:
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
      "Bash(sudo:*)", "Bash(curl:*)", "Bash(wget:*)", "Bash(rm -rf:*)"
    ]
  },
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

#### Project Context with CLAUDE.md
Create a `CLAUDE.md` file in any project directory. Claude Code reads this automatically on launch. Example for this project:
```markdown
# Bazzite Gaming Laptop Project
## System: Acer Predator G3-571 | Bazzite 43 | NVIDIA GTX 1060 + Intel HD 630

## Rules
- This is an immutable OS (Fedora Atomic). Do NOT modify /usr directly.
- Use rpm-ostree for system packages, flatpak for apps.
- Never use sudo rm -rf, curl piped to bash, or wget without permission.
- Custom configs go in /etc/ (survives updates) or ~/.config/ (user configs).
- Test all changes before committing.

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- MangoHud config: ~/.config/MangoHud/MangoHud.conf
- DNS config: /etc/systemd/resolved.conf.d/dns-over-tls.conf
- WiFi script: /usr/local/bin/public-wifi-mode
- Claude Code settings: ~/.claude/settings.json
```

#### Safe Usage Rules
- Always launch from a **project directory**, never from $HOME
- Review `git diff` after every session
- Never use `--dangerously-skip-permissions`
- No third-party MCP servers — only Anthropic-official tools
- Use `/sandbox` mode always
- Check `claude doctor` if anything seems off

#### Useful Commands Inside Claude Code
| Command | Purpose |
|---------|---------|
| `/sandbox` | Enable bubblewrap sandboxing |
| `/model` | Switch between Sonnet/Opus |
| `/mcp` | Check MCP server status |
| `?` | Show all keyboard shortcuts |
| `/` | Show all slash commands |
| `!command` | Run a shell command and feed output to Claude |
| Esc | Stop Claude mid-action |
| Esc+Esc | Rewind to last checkpoint |

#### What Claude Code Can Do For This Project
- Write and test systemd timer units for automated security scans
- Create shell scripts for system monitoring and alerting
- Configure GameMode, ScopeBuddy, and per-game optimizations
- Set up ClamAV scanning with proper exclusions for Steam library
- Build backup scripts for game saves and system configs
- Audit and harden system configurations
- Help with future Ollama/VS Code/AI development setup
