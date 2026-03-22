# Pending Claude Code Review
> Created: 2026-03-21 | Status: AWAITING REVIEW — do not commit until approved

This document tracks all changes made outside of Claude Code that need
review before being committed to the repo. Update this file after every
change session.

---

## Session: 2026-03-21 (Logan + Perplexity AI)

### Context
Phase 3 is complete per phases_3-5-overview.md.
These files were created via terminal to fix a thermal-protection service
that was crash-looping (status=203/EXEC) after being partially created
by the Newelle AI session without ever being committed to disk.

Root cause of original crash loop:
- scripts/thermal-protection.py did not exist on disk or in repo
- systemd unit used Restart=always with no burst limit (endless restart storm)
- ExecStart pointed to bare .py path without python3 interpreter prefix
- Permission denied writing to /etc/systemd/system/ directly without sudo install

All issues resolved. Service now active and stable.

---

## New Files Added

### 1. scripts/thermal-protection.py (318 lines)
**Status:** On disk, service running, tested OK
**Purpose:** Systemd-managed thermal protection daemon for GTX 1060 + Intel HD 630 hybrid laptop

**What it does:**
- Reads thresholds from /etc/bazzite/thermal-protection.conf at startup with hardcoded fallback defaults
- Polls CPU temps via sensors -A -j every 10s (configurable via POLL_INTERVAL)
- Polls GPU temp via nvidia-smi --query-gpu=temperature.gpu
- State machine: normal -> warn -> throttle -> critical
- On warn: switches CPU governor to schedutil
- On throttle: powersave governor + CPU capped at 1.6GHz + GPU capped at 60W
- On critical: powersave + CPU capped at 800MHz + GPU capped at 40W
- Saves CPU governor state at startup and restores exact saved state on clean exit via SIGTERM
- Sends notify-send desktop notifications on every state transition using sudo -u lch to reach user session from root process
- Logs to /var/log/bazzite/thermal-protection.log
- Runs as root via systemd (required for /sys CPU freq writes)

**Rules compliance — Claude Code please verify:**
- [ ] No shell=True in any subprocess calls
- [ ] No PRIME offload variables (NV_PRIME_RENDER_OFFLOAD, GLXVENDORLIBRARYNAME, VKLAYERNVoptimus, prime-run, DRI_PRIME)
- [ ] No hardcoded API keys
- [ ] No writes to /usr
- [ ] notify-send correctly uses sudo -u lch pattern to reach desktop from root
- [ ] All subprocess calls use list form not string form
- [ ] Compatible with Bazzite immutable OS constraints

---

### 2. systemd/thermal-protection.service
**Status:** Installed at /etc/systemd/system/thermal-protection.service, enabled, running

**Full file contents:**
[Unit]
Description=Bazzite Thermal Protection Service
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/lch/projects/bazzite-laptop/scripts/thermal-protection.py
Restart=on-failure
RestartSec=30
StartLimitBurst=3
StartLimitIntervalSec=300
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

text

**Rules compliance — Claude Code please verify:**
- [ ] Follows patterns in existing systemd/ units (compare with system-health.service, bazzite-mcp-bridge.service)
- [ ] Restart=on-failure with burst limit is correct (not Restart=always which caused the original crash loop)
- [ ] deploy-services.sh needs a stanza added to install this on fresh deploy

---

### 3. configs/thermal-protection.conf
**Status:** Currently only at /etc/bazzite/thermal-protection.conf — needs adding to repo

**Full file contents:**
Bazzite Thermal Protection Configuration
Edit these values to tune throttling behavior for your hardware
Changes take effect on next service restart
CPU temperature thresholds (C)
CPU_WARN=80
CPU_THROTTLE=88
CPU_CRITICAL=95

GPU temperature thresholds (C)
GPU_WARN=75
GPU_THROTTLE=83
GPU_CRITICAL=90

Polling interval in seconds
POLL_INTERVAL=10

text

**Notes:**
- deploy-services.sh should install this to /etc/bazzite/ on fresh deploy
- /etc/bazzite/ directory must be created if it does not exist (sudo mkdir -p /etc/bazzite)

---

## System-Level Changes (outside repo — applied manually via sudo)

| What | Location | How Applied | Status |
|---|---|---|---|
| Config directory | /etc/bazzite/ | sudo mkdir -p /etc/bazzite | Done |
| Thermal config | /etc/bazzite/thermal-protection.conf | sudo tee | Done |
| Service unit | /etc/systemd/system/thermal-protection.service | sudo install -m 644 | Done |
| Service enabled | systemd | sudo systemctl enable --now thermal-protection.service | Done |
| Journal size cap | /etc/systemd/journald.conf.d/size-limit.conf | pending | NOT YET DONE |

---

## TODO for Claude Code — Action Required Before Commit

1. REVIEW scripts/thermal-protection.py against all rules in project-instructions-updated.md
   and docs/project-onboarding.md — flag any violations

2. ADD deploy stanza to scripts/deploy-services.sh:
   - sudo mkdir -p /etc/bazzite
   - sudo install -m 644 configs/thermal-protection.conf /etc/bazzite/thermal-protection.conf
   - sudo install -m 644 systemd/thermal-protection.service /etc/systemd/system/thermal-protection.service
   - sudo systemctl daemon-reload
   - sudo systemctl enable --now thermal-protection.service

3. ADD to scripts/verify-services.sh:
   - Check thermal-protection.service is active
   - Check /etc/bazzite/thermal-protection.conf exists
   - Check /var/log/bazzite/ directory exists

4. ADD to backup.sh systemd-units loop:
   - /etc/systemd/system/thermal-protection.service should be included in backup

5. CONFIRM all clear then commit with:
   git add scripts/thermal-protection.py \
           systemd/thermal-protection.service \
           configs/thermal-protection.conf \
           docs/pending-review.md
   git commit -m "feat: add thermal protection service with configurable thresholds and desktop notifications"

---

## Changelog — Append Future Sessions Below

### 2026-03-21 — Session 1 (Logan + Perplexity AI)
- Created thermal-protection.py from scratch (original was missing from disk and repo)
- Fixed all crash-loop root causes (203/EXEC, permission denied, Restart=always)
- Added configurable threshold loading from /etc/bazzite/thermal-protection.conf
- Added notify-send desktop alerts for all thermal state transitions
- Added CPU governor save/restore at startup/exit
- Service confirmed active and stable: active (running) since 17:31:55 EDT
- Created /etc/bazzite/thermal-protection.conf with tuned thresholds
- Created this pending-review.md document for Claude Code handoff


### 2026-03-21 — Session 1 continued (Journal Size Cap)
- Created /etc/systemd/journald.conf.d/size-limit.conf
- Settings: SystemMaxUse=200M, SystemKeepFree=1G, MaxRetentionSec=90day
- Applied via sudo systemctl restart systemd-journald
- Result: journals now at 48MB (was 470MB before previous cleanup)
- NOTE: This is a system-level change only — no repo file needed
  (journald drop-in does not need to be in the bazzite-laptop repo)
  However: consider adding to deploy-services.sh or a new setup-journald.sh
  so fresh installs get this cap automatically

### 2026-03-21 — Session 1 continued (Governor OSError Bugfix)
- ISSUE: Service crashed with OSError: [Errno 22] Invalid argument when trying
  to write 'schedutil' governor to /sys on Intel i7-7700HQ
- ROOT CAUSE: Some Intel hybrid CPU governor paths reject certain governors
  even as root — not a permissions issue, a kernel/hardware constraint
- FIX: Added OSError catch in set_cpu_governor() with powersave fallback
  If requested governor is rejected, falls back to powersave silently
  If powersave also rejected, logs warning and skips that core
- RESULT: Service now survives invalid governor writes without crashing
- Service restarted clean: no errors, 24.9M memory peak, stable
- NOTE for Claude Code: review the new OSError handler in set_cpu_governor()
  around line 128-145 — confirm fallback logic is correct for this hardware

### 2026-03-21 — Session 2 (System Audit + Fixes)

#### Timers Were All Dead — Root Cause: SELinux + Missing deploy coverage
- All 4 custom timers (system-health, clamav-quick, clamav-deep, clamav-healthcheck)
  showed "Refusing to start — unit to trigger not loaded" after every reboot
- Root cause: .service files copied from ~/projects/ inherited SELinux context
  user_home_t instead of required systemd_unit_file_t
- systemd silently refuses to load units with wrong SELinux context
- Fix applied: sudo restorecon -v on all 6 affected unit files
  (clamav-quick, clamav-deep, clamav-healthcheck, system-health, rag-embed × .service/.timer)
- All files now labeled: unconfined_u:object_r:systemd_unit_file_t:s0
- sudo systemctl daemon-reload + start applied to all timers
- NOTE for Claude Code: deploy-services.sh must run restorecon after every
  install/copy of unit files to /etc/systemd/system/ — add this to the
  deploy stanza for ALL units, not just system-health

#### rag-embed.timer — Never Enabled, Wrong Ownership
- rag-embed.service and rag-embed.timer were owned by lch not root
- Fixed: sudo chown root:root + restorecon
- Fixed: sudo systemctl enable --now rag-embed.timer
- Now scheduled: next run Sun 2026-03-22 09:00 AM
- NOTE for Claude Code: add rag-embed to deploy-services.sh with proper
  sudo install -m 644 + restorecon + enable --now

#### health-latest.log Symlink Was Stale
- Symlink pointed to health-2026-03-17-0136.log (4 days old)
- MCP tools and tray app were reading stale March 17 data
- Fixed: sudo ln -sf to health-2026-03-21-0701.log
- NOTE for Claude Code: system-health-snapshot.sh should update this
  symlink atomically after every successful snapshot run

#### LanceDB health_records Backfilled
- Ingest state tracker uses last-file-only deduplication
- Only 1 health record existed despite 50+ log files
- Workaround: cleared last_health_file/last_health_ingest from
  .ingest-state.json and ran python3 -m ai.log_intel --health × 10 passes
- Result: health_records 1 → 45 rows (full historical backfill)
- scan_records: 24 rows (already current)
- security_logs: 0 rows (needs separate investigation)
- threat_intel: 0 rows (needs threat lookups to populate)
- NOTE for Claude Code: ingest.py tracks only last file processed —
  Phase 3 item #11 (MAXDOCSPERRUN + processed-file set) will fix this
  permanently so historical backfill is never needed again

#### All Timers Now Scheduled
| Timer                  | Next Run                  |
|------------------------|---------------------------|
| system-health.timer    | Sun 2026-03-22 08:01 AM   |
| rag-embed.timer        | Sun 2026-03-22 09:00 AM   |
| clamav-quick.timer     | Sun 2026-03-22 12:00 PM   |
| clamav-healthcheck.timer | Wed 2026-03-25           |
| clamav-deep.timer      | Fri 2026-03-27            |

#### security.status File Missing
- ~/security.status does not exist anywhere on this system
- Tray app and MCP security.status tool are returning errors/empty
- Root cause unknown — needs investigation
- NOTE for Claude Code: determine where security.status should be
  created (clamav-scan.sh? system-health-snapshot.sh?) and add
  initialization to deploy-services.sh

#### ZRAM stats and bc validation

- Verified ZRAM stats block in system-health-snapshot.sh:
  - When ORIG_MB and COMP_MB are 0 ("no swap pressure"), the bc call is not
    executed.
  - Confirmed with a standalone test script using the same logic.
- Conclusion: current ZRAM section does not cause early exits when swap
  usage is zero; no code change required.

#### New AI Operational Playbook

- Added docs/ai-operational-playbook.md as a high-level runbook for humans
  and AI assistants.
- Captures:
  - Canonical paths (logs, LanceDB, status JSON, systemd units).
  - Safe day-to-day commands for health checks, scans, and ingestion.
  - Systemd + SELinux deployment rules for all project units.
  - Expectations for updating docs/pending-review.md after changes.
- All future operational or AI-facing changes should keep this playbook in
  sync with actual behavior.
