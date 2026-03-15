# System Health Monitoring — Bazzite Gaming Laptop

Hardware and performance health monitoring integrated with the existing
ClamAV security system on an Acer Predator G3-571 running Bazzite 43.

## Quick Start

```bash
# Run a health snapshot (interactive, terminal output)
sudo system-health-snapshot.sh

# Run with email alert
sudo system-health-snapshot.sh --email

# Run SMART extended self-test (blocks suspend, ~20 min)
sudo system-health-snapshot.sh --selftest

# Validate the installation
sudo system-health-test.sh
```

KDE Start Menu → Security → **System Health Snapshot** / **View Health Logs**

---

## What It Monitors

### Drive Health (SMART)
| Drive | Interface | What's checked |
|-------|-----------|----------------|
| sda — SK hynix 256GB | SATA M.2 | Health status, reallocated sectors, offline uncorrectable, ATA errors, wear leveling, temperature, power losses, self-test results |
| sdb — WD SN580E 2TB | NVMe (USB) | Health status, available spare, percentage used, media errors, temperature, unsafe shutdowns |

Both drives have **delta tracking** — the script remembers previous values and
flags if error counts are *growing* between snapshots, not just above a threshold.

### GPU (NVIDIA GTX 1060 Mobile)
Temperature, power draw, VRAM usage, performance state, fan speed, clock speeds,
supergfxctl mode, and NVIDIA XID errors from kernel log (hardware faults).

### CPU & Thermals (i7-7700HQ)
Package temperature, per-core temperatures, fan speeds via lm-sensors. Falls
back to sysfs thermal zones if lm-sensors is unavailable.

### Storage & ZRAM
Filesystem usage with threshold alerts, inode usage, ZRAM compression ratio
and utilization, vm.swappiness verification (must be 180 for Bazzite).

### Key Services
Firewall, ClamAV signatures, GPU switching, thermal management, DNS resolver,
USB guard, SSD TRIM timer, SELinux status, firewall zone verification.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    system-health-snapshot.sh             │
│  Collects: SMART · GPU · CPU · Storage · Services       │
├────────────┬────────────┬───────────┬───────────────────┤
│  Logs to   │  Updates   │  Emails   │  Self-test mode   │
│  /var/log/ │  tray .status  │  via msmtp │  --selftest  │
│  system-   │  (shared w/    │  on warn/  │  blocks sleep│
│  health/   │   ClamAV)      │  critical  │  polls result│
└────────────┴────────────┴───────────┴───────────────────┘

  Timer: system-health.timer (daily 8AM, persistent)
  Logs:  /var/log/system-health/health-YYYY-MM-DD-HHMM.log
  Delta: /var/log/system-health/health-deltas.dat
```

### Relationship to ClamAV Security System

The health monitoring is **completely independent** of the ClamAV security
pipeline. It never starts/stops clamd, touches quarantine, or modifies scan
logs. The only shared touchpoints are:

1. **Tray status file** (`~/security/.status`) — health data is added as
   separate JSON keys (`health_status`, `health_issues`, etc.) alongside
   existing ClamAV scan status
2. **Email infrastructure** — uses the same msmtp + Gmail app password config
3. **KDE Security menu** — new entries added alongside existing scan shortcuts

### Completed Integrations (Phase 2)

All Phase 2 integrations have been implemented:

- **Tray app health state**: 9th state (`health_warning`) added to tray state machine.
  When ClamAV is idle+healthy but `health_status` reports WARNING or CRITICAL,
  the tray shows a green shield with amber EKG pulse badge (steady, no blink).
  ClamAV scan states always take priority over health state.
- **Tray health submenu**: Health status and issue count displayed in tray right-click menu,
  read from `.status` JSON during 3-second poll cycle.
- **Status file read-modify-write**: Health script reads existing `.status` JSON,
  updates only health keys, writes atomically (tmp + rename) to avoid corrupting
  ClamAV scan status.
- **Scan email health summary**: `--append` flag generates compact health summary
  included in every ClamAV scan email.
- **Icon refresh**: 7 SVG icons with shape-differentiated badges (viewBox 48x48)
  for colorblind accessibility — each state has a unique badge shape.

---

## Alert Thresholds

| Check | Threshold | Level |
|-------|-----------|-------|
| Reallocated sectors (sda) | ≥20 | Warning |
| Reallocated sectors growing | Any increase | **Critical** |
| Offline uncorrectable (sda) | ≥100 | **Critical** |
| Offline uncorrectable growing | Any increase | **Critical** |
| ATA errors growing | Any increase | Warning |
| Wear leveling (sda) | ≥500 cycles | Warning |
| NVMe available spare (sdb) | ≤20% | **Critical** |
| NVMe percentage used (sdb) | ≥80% | Warning |
| NVMe media errors (sdb) | >0 | **Critical** |
| NVMe media errors growing | Any increase | **Critical** |
| GPU temperature | ≥85°C | Warning |
| CPU package temperature | ≥90°C | Warning |
| Disk usage | ≥85% | Warning |
| ZRAM usage | ≥80% | Warning |
| SMART self-test | Aborted | Warning |
| SMART self-test | Failed/errors | **Critical** |
| Required service down | Any | Warning |
| SELinux not enforcing | — | Warning |
| Firewall zone ≠ drop | — | Warning |
| vm.swappiness ≠ 180 | — | Warning |

---

## File Manifest

### Scripts
| File | System Location | Purpose |
|------|-----------------|---------|
| `scripts/system-health-snapshot.sh` | `/usr/local/bin/` | Core health monitor |
| `scripts/system-health-test.sh` | `/usr/local/bin/` | 16-test validation suite |

### Systemd
| File | System Location | Purpose |
|------|-----------------|---------|
| `systemd/system-health.service` | `/etc/systemd/system/` | Oneshot service |
| `systemd/system-health.timer` | `/etc/systemd/system/` | Daily 8AM trigger |

### Configs
| File | System Location | Purpose |
|------|-----------------|---------|
| `configs/logrotate-system-health` | `/etc/logrotate.d/system-health` | 90-day log rotation |

### Desktop
| File | System Location | Purpose |
|------|-----------------|---------|
| `desktop/security-health-snapshot.desktop` | `~/.local/share/applications/` | KDE menu: run snapshot |
| `desktop/security-health-logs.desktop` | `~/.local/share/applications/` | KDE menu: view logs |

### Docs
| File | Purpose |
|------|---------|
| `README.md` | This file — architecture and usage |
| `CLAUDE-addendum.md` | Appended to existing CLAUDE.md (do not replace) |
| `docs/system-health-implementation.md` | Deployment guide with all steps |

### Runtime (not in repo)
| Path | Purpose |
|------|---------|
| `/var/log/system-health/health-*.log` | Timestamped snapshots |
| `/var/log/system-health/health-latest.log` | Symlink to most recent |
| `/var/log/system-health/health-deltas.dat` | Delta tracking data |
| `~/security/.status` | Tray status (health keys added to existing) |

---

## Command Reference

| Task | Command |
|------|---------|
| Interactive snapshot | `sudo system-health-snapshot.sh` |
| Snapshot + email | `sudo system-health-snapshot.sh --email` |
| Quiet (for timers) | `sudo system-health-snapshot.sh --quiet` |
| Compact (for scan email) | `sudo system-health-snapshot.sh --append` |
| Run SMART self-test | `sudo system-health-snapshot.sh --selftest` |
| Validation suite | `sudo system-health-test.sh` |
| Check timer status | `systemctl list-timers system-health*` |
| View latest log | `less /var/log/system-health/health-latest.log` |
| View delta trends | `cat /var/log/system-health/health-deltas.dat` |
| Browse log directory | `ls -lht /var/log/system-health/` |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All OK — no issues |
| 1 | Warnings detected |
| 2 | Critical issues detected |
| 3 | Script error |

---

## Surviving Bazzite Updates

All files are in persistent locations that survive rpm-ostree updates:

| Path | Persists | Notes |
|------|----------|-------|
| `/usr/local/bin/` | ✅ | Scripts |
| `/etc/systemd/system/` | ✅ | Timers and services |
| `/etc/logrotate.d/` | ✅ | Log rotation config |
| `/var/log/system-health/` | ✅ | Logs and delta data |
| `~/.local/share/applications/` | ✅ | Desktop entries |
| `~/security/.status` | ✅ | Tray integration |

---

## Parent Project

This is part of the **bazzite-laptop** project:
- Repo: `github.com:violentwave/bazzite-laptop.git` (private)
- Full docs: `~/projects/bazzite-laptop/docs/`
- Deploy: `sudo ./scripts/deploy.sh` from repo root
