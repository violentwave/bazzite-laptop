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
Refer to these project documents (all in `docs/`) for full details:
- `bazzite-optimization-guide.md` — Master guide with completed/remaining work
- `system-config-snapshot` — Exact system configuration for disaster recovery
- `troubleshooting-log` — Problems already solved, do not re-debug
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
- Security hardening: ClamAV clamd daemon mode (daily quick + weekly deep + test scans), USBGuard (12 devices whitelisted), LUKS Argon2id + header backup, firewall log-denied=all
- Email alerts: HTML emails via msmtp + Gmail app password — sent after EVERY scan (quick/deep/test) + healthcheck failures
- KDE Security menu: 12 shortcuts (deep scan, quick scan, firewall, firewall status, KWalletManager, scan logs, start security monitor, system health snapshot, update email password, USB devices, view health logs, view quarantine)
- ~/security/ hub: centralized security folder with status file, quarantine dir, scan logs
- Notification system: System tray app with 9-state icon machine (7 custom SVG icons with shape-differentiated badges for colorblind accessibility), 3s polling, SIGHUP-resistant, autostart, health submenu
- Quarantine hardening: chmod 000 + chattr +i on quarantined files, root:lch 750 directory, release manager script
- Healthcheck: /usr/local/bin/clamav-healthcheck.sh — 10+ checks, Wednesdays 2PM, email on failure
- Test suite: /usr/local/bin/bazzite-security-test.sh — 15-test diagnostic with EICAR detection validation
- Backup: Unified backup.sh/restore.sh on BazziteBackup flash drive (5 scenarios documented)
- GitHub: Private repo at github.com:violentwave/bazzite-laptop.git
- Deploy: `sudo ./scripts/deploy.sh [--dry-run]` syncs repo files to system locations
- System health monitoring: system-health-snapshot.sh with SMART delta tracking,
  GPU/CPU thermals, storage alerts, tray integration (health_warning state with amber EKG pulse icon),
  daily 8AM timer, email alerts, health summary in scan emails, KDE Security menu entries, 16-test validation suite
- VS Code workspace: .vscode/settings.json + extensions.json for SVG preview and design tools

### Remaining Work (Prioritized)
1. **ScopeBuddy configuration** — Per-game advanced launch management
2. **Proton environment variable testing** — WAYLAND, NTSYNC flags for compatible games
3. **AI/Coding setup** (deferred) — Ollama with CUDA, VS Code, local LLMs
4. **Downloads folder watcher** — inotify auto-scan new downloads

### Repo Layout
- `scripts/` — all shell scripts (clamav, backup, setup, deploy utilities)
- `systemd/` — timer and service unit files
- `desktop/` — .desktop files and security.menu
- `configs/` — system config files (udev rules, sysctl, gamemode, etc.)
- `tray/` — security tray app (Python) + icons
- `.vscode/` — VS Code workspace settings and extension recommendations
- `docs/` — all documentation and guides

### Quick Reference
| Task | Command |
|------|---------|
| Deploy repo to system | `sudo ./scripts/deploy.sh` |
| Deploy (preview only) | `sudo ./scripts/deploy.sh --dry-run` |
| Health snapshot | `sudo system-health-snapshot.sh` |
| Health + email | `sudo system-health-snapshot.sh --email` |
| SMART self-test | `sudo system-health-snapshot.sh --selftest` |
| Health test suite | `sudo system-health-test.sh` |
| View health log | `less /var/log/system-health/health-latest.log` |
| Push to GitHub | `git push origin master` |

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

#### GitHub Push Workflow
```bash
# From ~/projects/bazzite-laptop/
git add <files>
git commit -m "Description of changes"
git push origin master
```
Remote is `github.com:violentwave/bazzite-laptop.git` (private repo, SSH key auth).

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

### How to Test the Security System
```
sudo bazzite-security-test.sh    # Full 15-test validation
sudo clamav-scan.sh test         # Quick EICAR detection test
sudo clamav-healthcheck.sh       # Infrastructure health check
```

### Quarantine Management
```
sudo quarantine-release.sh --list         # View quarantined files
sudo quarantine-release.sh --interactive  # Release files interactively
```
Quarantine location: `~/security/quarantine` (root:lch 750, files chmod 000 + chattr +i)
