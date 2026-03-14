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
- scripts/ — all shell scripts (clamav, backup, setup utilities)
- systemd/ — timer and service unit files
- desktop/ — .desktop files and security.menu
- configs/ — system config files (udev rules, sysctl, gamemode, etc.)
- tray/ — security tray app (Python) + icons
- docs/ — all documentation and guides

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- MangoHud config: ~/.config/MangoHud/MangoHud.conf
- DNS config: /etc/systemd/resolved.conf.d/dns-over-tls.conf
- WiFi script: /usr/local/bin/public-wifi-mode
- Claude Code settings: ~/.claude/settings.json
- Backup scripts: /mnt/backup/ (on USB flash drive sdc3)

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
- Tray status updates use atomic write (tmp + rename) to avoid corruption
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
