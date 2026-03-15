# System Health Monitoring — Deployment Guide

## Important: Claude Code Sandbox Rules

Claude Code runs sandboxed — **no sudo, no root commands**.
Deployment is split into two phases:
- **Phase A** — Claude Code (or you) places files into the repo
- **Phase B** — You manually run the sudo commands in a terminal

---

## Phase A: Repo File Placement (Claude Code safe)

Claude Code can do all of this from `~/projects/bazzite-laptop/`:

```bash
# 1. Place scripts
cp ~/Downloads/system-health-snapshot.sh scripts/
cp ~/Downloads/system-health-test.sh scripts/

# 2. Place systemd units
cp ~/Downloads/system-health.service systemd/
cp ~/Downloads/system-health.timer systemd/

# 3. Place config
cp ~/Downloads/logrotate-system-health configs/

# 4. Place desktop entries
cp ~/Downloads/security-health-snapshot.desktop desktop/
cp ~/Downloads/security-health-logs.desktop desktop/

# 5. Place docs
cp ~/Downloads/system-health-implementation.md docs/

# 6. Append to existing CLAUDE.md (DO NOT replace)
cat ~/Downloads/CLAUDE-addendum.md >> CLAUDE.md

# 7. Append new .gitignore entries
cat ~/Downloads/gitignore-additions.txt >> .gitignore

# 8. Install desktop entries (no sudo needed — user dir)
cp desktop/security-health-snapshot.desktop ~/.local/share/applications/
cp desktop/security-health-logs.desktop ~/.local/share/applications/
```

---

## Phase B: System Deployment (requires sudo — run manually)

Open a regular terminal (not Claude Code) and run these:

```bash
cd ~/projects/bazzite-laptop

# ── Scripts ──
sudo cp scripts/system-health-snapshot.sh /usr/local/bin/
sudo cp scripts/system-health-test.sh /usr/local/bin/
sudo chmod 755 /usr/local/bin/system-health-snapshot.sh
sudo chmod 755 /usr/local/bin/system-health-test.sh

# ── Log directory ──
sudo mkdir -p /var/log/system-health
sudo chmod 755 /var/log/system-health

# ── Systemd units ──
sudo cp systemd/system-health.service /etc/systemd/system/
sudo cp systemd/system-health.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now system-health.timer

# ── Logrotate ──
sudo cp configs/logrotate-system-health /etc/logrotate.d/system-health
```

---

## Phase C: Verify

```bash
# Run the 16-test validation suite
sudo system-health-test.sh

# Run a manual snapshot to see output
sudo system-health-snapshot.sh

# Verify timer is active
systemctl list-timers system-health*

# Verify KDE menu entries
# Open Start Menu → Security → should show two new entries

# Verify log was created
ls -la /var/log/system-health/
cat /var/log/system-health/health-latest.log
```

---

## Phase D: Update deploy.sh (Claude Code safe)

Add these lines to `scripts/deploy.sh` in the appropriate sections.
Use whatever function names already exist in your deploy script:

```bash
# ── Scripts section ──
deploy_file "scripts/system-health-snapshot.sh" "/usr/local/bin/system-health-snapshot.sh" 755
deploy_file "scripts/system-health-test.sh" "/usr/local/bin/system-health-test.sh" 755

# ── Systemd section ──
deploy_file "systemd/system-health.service" "/etc/systemd/system/system-health.service" 644
deploy_file "systemd/system-health.timer" "/etc/systemd/system/system-health.timer" 644

# ── Configs section ──
deploy_file "configs/logrotate-system-health" "/etc/logrotate.d/system-health" 644

# ── Desktop section ──
deploy_user_file "desktop/security-health-snapshot.desktop" \
    "${HOME}/.local/share/applications/security-health-snapshot.desktop"
deploy_user_file "desktop/security-health-logs.desktop" \
    "${HOME}/.local/share/applications/security-health-logs.desktop"

# ── Post-deploy (add to end) ──
mkdir -p /var/log/system-health
```

---

## Phase E: Git Commit (Claude Code safe)

```bash
git add \
    scripts/system-health-snapshot.sh \
    scripts/system-health-test.sh \
    systemd/system-health.service \
    systemd/system-health.timer \
    configs/logrotate-system-health \
    desktop/security-health-snapshot.desktop \
    desktop/security-health-logs.desktop \
    docs/system-health-implementation.md \
    CLAUDE.md \
    .gitignore

git commit -m "feat: add system health monitoring (SMART, GPU, thermals, storage)

- system-health-snapshot.sh: SMART, GPU, CPU, storage, service health
- Delta tracking detects growing error counts between snapshots
- --selftest flag runs SMART extended test with sleep inhibit
- Daily 8AM timer with persistent catch-up
- HTML email alerts on warnings/critical via existing msmtp
- Tray status integration (health keys in ~/security/.status)
- KDE Security menu: System Health Snapshot + View Health Logs
- 16-test validation suite (system-health-test.sh)
- 90-day log rotation"
```

Then push (requires SSH passphrase — manual):
```bash
git push origin master
```

---

## Existing Doc Updates Needed

After deployment, update these files (Claude Code can do this):

### bazzite-optimization-guide.md
Move "System Monitoring Tools" from REMAINING WORK to COMPLETED:
```markdown
### System Monitoring Tools ✅
- Mission Center: Flatpak (GUI system monitor)
- btop: pre-installed (terminal system monitor)
- nvtop: pre-installed (GPU terminal monitor)
- smartmontools: pre-installed (SMART disk health)
- lm-sensors: pre-installed (hardware temperatures)
- system-health-snapshot.sh: custom health monitoring — SMART delta tracking,
  GPU/CPU thermals, storage alerts, service checks, email alerts, tray integration
- system-health-test.sh: 16-test validation suite
- Daily 8AM timer (system-health.timer) with persistent catch-up
```

Add to Quick Reference Commands table:
```
| Health snapshot      | sudo system-health-snapshot.sh |
| Health + email       | sudo system-health-snapshot.sh --email |
| SMART self-test      | sudo system-health-snapshot.sh --selftest |
| Health test suite    | sudo system-health-test.sh |
| View health log      | less /var/log/system-health/health-latest.log |
```

### system-config-snapshot
Add to Active Systemd Timers:
```
| system-health.timer | Daily system health snapshot | Daily 8AM |
```

Add to Custom Files:
```
| /usr/local/bin/system-health-snapshot.sh | System health monitor |
| /usr/local/bin/system-health-test.sh | Health validation suite |
| /etc/systemd/system/system-health.* | Health timer + service |
| /etc/logrotate.d/system-health | Health log rotation |
```

Add to Flatpak Applications:
```
| Mission Center | io.missioncenter.MissionCenter | GUI system monitor |
```

### backup-official-guide.md
Add to backup list:
```
| health-deltas | /var/log/system-health/health-deltas.dat |
| system-health units | /etc/systemd/system/system-health.* |
| health desktop entries | ~/.local/share/applications/security-health-*.desktop |
| logrotate-system-health | /etc/logrotate.d/system-health |
```

### project-instructions.md
Add to Completed Setup:
```
- System health monitoring: system-health-snapshot.sh with SMART delta tracking,
  GPU/CPU thermals, storage alerts, tray integration, daily 8AM timer, email alerts,
  KDE Security menu entries, 16-test validation suite
```

### reference-links.md
Add:
```
smartmontools docs: https://www.smartmontools.org/wiki/TocDoc
NVIDIA SMI reference: https://developer.nvidia.com/nvidia-system-management-interface
lm-sensors wiki: https://hwmon.wiki.kernel.org/
Mission Center: https://missioncenter.io/
```

---

## Phase 2 Integration (Completed)

All Phase 2 integrations are implemented and committed:

### Tray app health state (completed)
- 9th state `STATE_HEALTH_WARNING` added to tray state machine
- Green shield + amber EKG pulse badge icon (`bazzite-sec-health-warn.svg`)
- Shows when ClamAV is idle+healthy AND `health_status` is WARNING or CRITICAL
- ClamAV scan states always take priority over health state
- Health submenu shows status and issue count in tray right-click menu

### Icon refresh (completed)
- 7 SVG icons with shape-differentiated badges (viewBox 48x48)
- Unique badge shapes per state for colorblind accessibility
- Interior glyphs (checkmarks, exclamation, X marks) visible at 22px panel size
- freedesktop index.theme with Context=Status, MinSize=16, MaxSize=256

### Scan email health summary (completed)
- `--append` flag on system-health-snapshot.sh generates compact summary
- Included in every ClamAV scan email

### Status file safety (completed)
- Read-modify-write pattern: read existing → update health keys → atomic write
- Prevents race condition between scan and health scripts writing to ~/security/.status
