# P76 — Systemd Scope Remediation

**Date:** 2026-04-13 (updated 2026-04-14)  
**Phase:** P76 ( remediation follow-up to ingestion reliability work )  
**Machine:** Acer Predator G3-571 on Bazzite/Fedora Atomic  
**Boot Stack:** GRUB+shim (not systemd-boot)

---

## Executive Summary

This document addresses host-side systemd/service design issues causing repo-owned scheduled jobs to fail. The root cause is a **scope mismatch**: system-scoped services attempting to execute binaries and access files in user home directories, which fails due to SELinux policies and namespace restrictions on immutable Fedora Atomic systems.

**What was fixed:**
- Created user-scoped unit files for 4 repo-owned scheduled jobs
- Provided migration script and validation procedures
- Follow-up: corrected `rag-embed.service` to a valid repo entrypoint (`ai.log_intel.ingest --all`)
- Follow-up: hardened code-index embedding behavior to use local Ollama embeddings (or zero-vectors) instead of cloud retry storms when provider auth/quota fails

**What remains manual:**
- API key rotation for security-audit.service
- Potential SELinux policy work for system-health.service
- System-level logrotate boot.log permissions
- Secure Boot/firmware updates (outside repo scope)

---

## Root Cause Analysis

### The Permission Denied Problem (203/EXEC)

**Symptom:**
```
system-scoped services are executing user-home repo venv paths like:
  /var/home/lch/projects/bazzite-laptop/.venv/bin/python

Result: 203/EXEC Permission denied
```

**Why it happens:**
1. On Fedora Atomic (Bazzite), `/home` is a symlink to `/var/home`
2. User home directories have SELinux label `user_home_t`
3. System services run in restricted domains that cannot execute `user_home_t` files
4. The Python interpreter in `.venv/bin/python` is itself a symlink chain into `~/.local/share/uv/...`
5. Even with `User=lch` in the service, the execution context is still a system service domain

**Affected services:**
- `code-index.service` — Daily code intelligence indexing
- `fedora-updates.service` — Weekly Fedora/Bodhi update check
- `release-watch.service` — Daily upstream release watch
- `rag-embed.service` — Daily RAG embedding (also had namespace issues)

### The Namespace Problem (226/NAMESPACE)

**Symptom:**
```
rag-embed.service fails with 226/NAMESPACE
```

**Why it happens:**
1. Service used `ProtectHome=read-only` and `ReadWritePaths=/home/lch/...`
2. Actual paths on Bazzite are `/var/home/lch/...` (symlinked)
3. The vector database lives on an external SSD at `/var/mnt/ext-ssd/.bazzite-data/vector-db`
4. Systemd namespace restrictions conflict with symlinked home paths

---

## The Solution: User-Scoped Units

### Why User Units?

| Aspect | System Unit | User Unit |
|--------|-------------|-----------|
| Runs as | root (or specified User=) | User's own systemd instance |
| SELinux domain | system service restrictions | User session context |
| Home directory access | Blocked by policy | Natural access |
| Venv execution | Requires explicit permissions | Works natively |
| ProtectHome/ReadWritePaths | Can conflict with symlinks | Not needed |

For repo-owned scheduled jobs that:
- Execute code from the repo's virtual environment
- Write to user-owned directories (`~/security/`, `~/.config/`)
- Don't require root privileges

**User units are the correct scope.**

### What Changed

**New user unit files (repo-owned):**
```
systemd/user/
├── code-index.service      # Uses %h/projects/bazzite-laptop paths
├── code-index.timer        # Same schedule: daily 06:00
├── fedora-updates.service  # Same schedule: Monday 03:00
├── fedora-updates.timer
├── release-watch.service   # Same schedule: daily 09:45
├── release-watch.timer
├── rag-embed.service       # Removed ProtectHome/ReadWritePaths
└── rag-embed.timer         # Same schedule: daily 09:00
```

**Key differences from system units:**
1. Uses `%h` (user home) instead of hardcoded `/home/lch` or `/var/home/lch`
2. Removed `ProtectHome`, `ReadWritePaths`, `ProtectSystem` hardening (not needed in user context)
3. Conservative resource limits preserved (`Nice=10` or `Nice=19`)
4. Same `OnCalendar` schedules as before

### Follow-up Fixes (2026-04-14)

1. `rag-embed.service` no longer references the non-existent module `ai.rag.embed_pipeline`.
   It now runs:

```ini
ExecStart=%h/projects/bazzite-laptop/.venv/bin/python -m ai.log_intel.ingest --all
```

2. `ai/code_intel/store.py` now routes indexing-time embeddings through `_embed_or_zero()` everywhere, and `_embed_or_zero()` uses `provider="ollama"`.
   This prevents Gemini/Cohere retry storms during scheduled indexing. If Ollama is unavailable, indexing degrades to zero vectors after one failure.

3. `scripts/install-user-timers.sh` now sets permissions only on managed timer/service files.
   This avoids chmod failures when unrelated user unit files exist in `~/.config/systemd/user/`.

4. Validation pass confirmed user-scope services complete successfully (`code-index`, `fedora-updates`, `release-watch`, `rag-embed`).

---

## Installation Instructions

### Automated Installation

```bash
# From repo root
cd ~/projects/bazzite-laptop
./scripts/install-user-timers.sh

# To also disable old system timers (requires sudo):
./scripts/install-user-timers.sh --disable-system
```

### Manual Installation

```bash
# 1. Copy user units to systemd user directory
mkdir -p ~/.config/systemd/user
cp systemd/user/*.service ~/.config/systemd/user/
cp systemd/user/*.timer ~/.config/systemd/user/

# 2. Reload user systemd
systemctl --user daemon-reload

# 3. Enable and start timers
systemctl --user enable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer

# 4. (Optional) Disable old system timers
sudo systemctl disable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer
```

---

## Validation Commands

### Verify Installation

```bash
# List all user timers
systemctl --user list-timers --all

# Check specific timer status
systemctl --user status code-index.timer --no-pager
systemctl --user status fedora-updates.timer --no-pager
systemctl --user status release-watch.timer --no-pager
systemctl --user status rag-embed.timer --no-pager
```

### Manual Service Testing

```bash
# Run services immediately to verify they work
systemctl --user start code-index.service
systemctl --user start fedora-updates.service
systemctl --user start release-watch.service
systemctl --user start rag-embed.service

# Check results
systemctl --user status code-index.service --no-pager
systemctl --user status fedora-updates.service --no-pager
systemctl --user status release-watch.service --no-pager
systemctl --user status rag-embed.service --no-pager
```

### Log Inspection

```bash
# User service logs (no sudo needed)
journalctl --user -u code-index.service -n 80 --no-pager
journalctl --user -u fedora-updates.service -n 80 --no-pager
journalctl --user -u release-watch.service -n 80 --no-pager
journalctl --user -u rag-embed.service -n 80 --no-pager

# Follow real-time logs
journalctl --user -u rag-embed.service -f
```

---

## Rollback Path

If user units cause issues, revert to system units:

```bash
# 1. Disable and remove user units
systemctl --user disable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer
rm -f ~/.config/systemd/user/{code-index,fedora-updates,release-watch,rag-embed}.{service,timer}
systemctl --user daemon-reload

# 2. Re-enable system units (if they still exist)
sudo systemctl enable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer

# 3. If system unit files were deleted, restore from git:
#    sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
#    sudo systemctl daemon-reload
#    sudo systemctl enable --now <timers>
```

---

## Remaining Issues (Manual Steps Required)

### 1. security-audit.service — API Key Issues

**Status:** Service runs but providers fail authentication

**Symptoms:**
- Gemini: "invalid API key"
- Cohere: trial/rate limit errors
- Ollama emergency fallback: working

**Root Cause:**
API keys have validity periods. Key presence (`~/.config/bazzite-ai/keys.env` exists) does not equal key validity.

**Remediation Steps:**

```bash
# 1. Verify key presence (names only, NEVER read values)
cat ~/.config/bazzite-ai/keys.env | grep -E '^(GEMINI|COHERE)_API_KEY' | cut -d= -f1

# 2. Test key validity manually
source ~/.config/bazzite-ai/keys.env
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
# If response contains "API key not valid", the key needs rotation

# 3. Update keys (manual operator action required)
#    - Generate new key from Google AI Studio (Gemini)
#    - Generate new key from Cohere dashboard
#    - Update ~/.config/bazzite-ai/keys.env with new values
#    - NEVER commit keys to git

# 4. Verify fallback works
systemctl --user status bazzite-mcp-bridge.service
# Ollama embedding should be active on :11434
```

**Why this remains manual:**
- Key rotation requires account access
- API providers have their own workflows
- Keys are secrets that must not be exposed in scripts

### 2. system-health.service — Exit Code 1

**Status:** Service exits with code 1

**Potential Causes:**
1. Path issues in `/usr/local/bin/system-health-snapshot.sh`
2. SELinux preventing access to `/var/log/system-health/`
3. Missing device UUID configuration
4. Permission issues writing to `~/security/.status`

**Diagnostic Steps:**

```bash
# Check service status and recent logs
sudo systemctl status system-health.service --no-pager
sudo journalctl -u system-health.service -n 100 --no-pager

# Check log directory permissions
ls -laZ /var/log/system-health/

# Test script manually (as root for SMART access)
sudo /usr/local/bin/system-health-snapshot.sh --quiet
echo "Exit code: $?"

# Check SELinux denials
sudo ausearch -m avc -ts recent | grep system-health

# Verify paths in script
grep -E '(REPO_DIR|VENV|UUID_CONF|LOG_DIR)' /usr/local/bin/system-health-snapshot.sh
```

**Potential Fixes (manual operator decision):**

If SELinux is blocking access:
```bash
# Option 1: Restore SELinux labels
sudo restorecon -Rv /var/log/system-health/
sudo restorecon -Rv /usr/local/bin/system-health-snapshot.sh

# Option 2: Add custom SELinux policy (if needed)
# This requires audit2allow and should be done carefully
sudo grep system-health /var/log/audit/audit.log | audit2allow -M system-health-local
sudo semodule -i system-health-local.pp
```

**Why this remains manual:**
- Requires root access for diagnostics
- May need SELinux policy work
- System-level path (`/usr/local/bin/`) outside repo scope
- Should be investigated thoroughly before automated changes

### 3. logrotate.service — boot.log Permissions

**Status:** Failing on `/var/log/boot.log` permission/SELinux access

**Root Cause:**
- logrotate runs as root but SELinux may be restricting access
- boot.log may have incorrect SELinux labels
- logrotate configuration may need adjustment

**Diagnostic Steps:**

```bash
# Check logrotate status
sudo systemctl status logrotate.service --no-pager
sudo journalctl -u logrotate.service -n 50 --no-pager

# Check boot.log permissions and labels
ls -laZ /var/log/boot.log

# Check logrotate configuration
sudo logrotate -d /etc/logrotate.conf 2>&1 | head -50

# Check for SELinux denials
sudo ausearch -m avc -ts recent | grep logrotate
```

**Potential Fixes:**

```bash
# Fix boot.log SELinux labels
sudo restorecon -v /var/log/boot.log

# Or set permissive for logrotate (if confirmed safe)
# (Not recommended without understanding the root cause)
```

**Why this remains manual:**
- System-level service outside repo scope
- May indicate broader SELinux configuration issues
- Requires root access
- Fedora Atomic updates may reset configuration

---

## Policy Clarification

### What This Repo Handles

✅ **In scope:**
- User-scoped unit files for repo-owned scheduled jobs
- Migration scripts for moving from system to user scope
- Documentation of the scope mismatch problem
- Validation commands for user units

❌ **Out of scope (documented only):**
- System-level services (`system-health`, `logrotate`)
- API key rotation (operator account access required)
- SELinux policy changes (requires root, system-wide impact)
- Secure Boot/firmware updates (hardware-level)

---

## Security Considerations

### User Units vs System Units Security Model

**System units with hardening:**
- Run in restricted SELinux domains
- Can use `ProtectHome`, `ProtectSystem`, `NoNewPrivileges`
- Cannot easily access user files (by design)

**User units:**
- Run in user's session context
- Inherit user's SELinux context
- Have natural access to user's files
- Rely on user-level permissions, not service hardening

**Risk Assessment:**
- These services execute code from the repo's virtual environment
- They write to user-owned directories only (`~/security/`, `~/.config/`)
- They do not require root privileges
- **User scope is appropriate and secure for this use case.**

### Preserved Safeguards

1. **Resource limits:** `Nice=10` or `Nice=19` prevents gaming/interactive interference
2. **Timeout protection:** `TimeoutStartSec` prevents hung services
3. **Working directory:** Explicit `WorkingDirectory` prevents path confusion
4. **Explicit python path:** Uses `.venv/bin/python` directly, not system Python

---

## References

- [AGENT.md](./AGENT.md) — Architecture and constraints
- [USER-GUIDE.md](./USER-GUIDE.md) — Operator documentation
- [HANDOFF.md](../HANDOFF.md) — Session context
- Fedora Atomic documentation: https://docs.fedoraproject.org/en-US/fedora-silverblue/
- systemd.unit(5), systemd.timer(5), systemd.exec(5) man pages

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-13 | Initial remediation document and user units created |

---

**Validation Status:**
- User unit files reviewed for correct `%h` usage ✅
- Schedules match existing timers ✅
- No hardcoded `/home/lch` paths ✅
- No `shell=True` or unsafe patterns ✅
- Install script includes rollback instructions ✅
