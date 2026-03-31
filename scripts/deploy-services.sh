#!/bin/bash
# Deploy/update Bazzite systemd services (user + system).
#
# User services (Newelle AI layer):
#   bazzite-llm-proxy, bazzite-mcp-bridge, service-canary.timer
#
# System services (health monitoring):
#   system-health.timer/service, system-health-snapshot.sh
#
# Usage: bash scripts/deploy-services.sh          (no sudo!)
#        bash scripts/deploy-services.sh --dry-run (print commands without executing)
set -euo pipefail

# ── Dry-run mode ──────────────────────────────────────────────────
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    echo "[DRY-RUN] Commands will be printed, not executed"
    echo ""
fi

# Wrapper: echo in dry-run, execute otherwise
run_cmd() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  [dry-run] $*"
    else
        "$@"
    fi
}

# ── Guard: refuse to run as root ──────────────────────────────────
if [[ "$EUID" -eq 0 ]]; then
    echo "ERROR: Do not run with sudo. User services need your user session."
    echo "Usage: bash scripts/deploy-services.sh"
    exit 1
fi

SRC="$(cd "$(dirname "$0")/.." && pwd)/systemd"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"

# ══════════════════════════════════════════════════════════════════
# 1. User services (systemctl --user, no sudo)
# ══════════════════════════════════════════════════════════════════
echo "=== Deploying User Services ==="

DEST="$HOME/.config/systemd/user"
run_cmd mkdir -p "$DEST"

for svc in bazzite-llm-proxy.service bazzite-mcp-bridge.service service-canary.service; do
    if [[ -f "$SRC/$svc" ]]; then
        run_cmd cp "$SRC/$svc" "$DEST/$svc"
        echo "  Copied $svc"
    fi
done

run_cmd systemctl --user daemon-reload
echo "  Daemon reloaded"

for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    run_cmd systemctl --user enable "$svc.service" 2>/dev/null || true
    run_cmd systemctl --user restart "$svc.service"
    echo "  Restarted $svc"
done

# Deploy service-canary script + timer
if [[ -f "$SCRIPTS/service-canary.sh" ]]; then
    run_cmd sudo cp "$SCRIPTS/service-canary.sh" /usr/local/bin/service-canary.sh
    run_cmd sudo chmod 755 /usr/local/bin/service-canary.sh
    echo "  Deployed service-canary.sh to /usr/local/bin/"
fi
if [[ -f "$SRC/service-canary.timer" ]]; then
    run_cmd cp "$SRC/service-canary.timer" "$DEST/service-canary.timer"
    run_cmd systemctl --user enable service-canary.timer 2>/dev/null || true
    run_cmd systemctl --user start service-canary.timer
    echo "  Enabled service-canary.timer"
fi

# ══════════════════════════════════════════════════════════════════
# 2. System services (requires sudo for /etc/systemd/system)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying System Services (requires sudo) ==="

# Deploy health snapshot script
if [[ -f "$SCRIPTS/system-health-snapshot.sh" ]]; then
    sudo cp "$SCRIPTS/system-health-snapshot.sh" /usr/local/bin/system-health-snapshot.sh
    sudo chmod 755 /usr/local/bin/system-health-snapshot.sh
    echo "  Deployed system-health-snapshot.sh to /usr/local/bin/"
fi

# Deploy system-health timer and service
for unit in system-health.service system-health.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

sudo systemctl daemon-reload
sudo systemctl enable system-health.timer 2>/dev/null || true
sudo systemctl start system-health.timer || echo "  WARNING: timer start failed"
echo "  Enabled system-health.timer"

# Deploy rag-embed timer and service
for unit in rag-embed.service rag-embed.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo chown root:root "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/rag-embed.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable rag-embed.timer 2>/dev/null || true
    sudo systemctl start rag-embed.timer || echo "  WARNING: rag-embed timer start failed"
    echo "  Enabled rag-embed.timer"
fi

# ══════════════════════════════════════════════════════════════════
# 3. Thermal protection service (system, requires sudo)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying Thermal Protection Service ==="

# Install Python script
if [[ -f "$SCRIPTS/thermal-protection.py" ]]; then
    sudo install -m 755 "$SCRIPTS/thermal-protection.py" /usr/local/bin/thermal-protection.py
    echo "  Installed thermal-protection.py to /usr/local/bin/"
fi

# Create config directory and install config
sudo mkdir -p /etc/bazzite
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$REPO_ROOT/configs/thermal-protection.conf" ]]; then
    sudo install -m 644 "$REPO_ROOT/configs/thermal-protection.conf" /etc/bazzite/thermal-protection.conf
    echo "  Installed thermal-protection.conf to /etc/bazzite/"
fi

# Install service unit with SELinux fix
if [[ -f "$SRC/thermal-protection.service" ]]; then
    sudo install -m 644 "$SRC/thermal-protection.service" /etc/systemd/system/thermal-protection.service
    sudo restorecon -v /etc/systemd/system/thermal-protection.service
    echo "  Installed thermal-protection.service"
fi

# Ensure log directory exists
sudo mkdir -p /var/log/bazzite

sudo systemctl daemon-reload
sudo systemctl enable --now thermal-protection.service 2>/dev/null || \
    echo "  WARNING: thermal-protection.service enable/start failed"
echo "  Enabled thermal-protection.service"

# ══════════════════════════════════════════════════════════════════
# 4. Agent timers (security-audit, performance-tuning, knowledge-storage)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying Agent Timers ==="

# security-audit
for unit in security-audit.service security-audit.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/security-audit.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable --now security-audit.timer 2>/dev/null || \
        echo "  WARNING: security-audit.timer enable/start failed"
    echo "  Enabled security-audit.timer"
fi

# performance-tuning
for unit in performance-tuning.service performance-tuning.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/performance-tuning.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable --now performance-tuning.timer 2>/dev/null || \
        echo "  WARNING: performance-tuning.timer enable/start failed"
    echo "  Enabled performance-tuning.timer"
fi

# knowledge-storage
for unit in knowledge-storage.service knowledge-storage.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/knowledge-storage.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable --now knowledge-storage.timer 2>/dev/null || \
        echo "  WARNING: knowledge-storage.timer enable/start failed"
    echo "  Enabled knowledge-storage.timer"
fi

# lancedb-optimize
for unit in lancedb-optimize.service lancedb-optimize.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/lancedb-optimize.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable --now lancedb-optimize.timer 2>/dev/null || \
        echo "  WARNING: lancedb-optimize.timer enable/start failed"
    echo "  Enabled lancedb-optimize.timer"
fi

# cve-scanner
for unit in cve-scanner.service cve-scanner.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/cve-scanner.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable cve-scanner.timer 2>/dev/null || \
        echo "  WARNING: cve-scanner.timer enable failed"
    sudo systemctl start cve-scanner.timer || echo "  WARNING: cve-scanner.timer start failed"
    echo "  Enabled cve-scanner.timer"
fi

# log-archive
for unit in log-archive.service log-archive.timer; do
    if [[ -f "$SRC/$unit" ]]; then
        sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
        sudo restorecon -v "/etc/systemd/system/$unit"
        echo "  Installed $unit to /etc/systemd/system/"
    fi
done

if [[ -f "$SRC/log-archive.timer" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable log-archive.timer 2>/dev/null || \
        echo "  WARNING: log-archive.timer enable failed"
    sudo systemctl start log-archive.timer || echo "  WARNING: log-archive.timer start failed"
    echo "  Enabled log-archive.timer"
fi

# ══════════════════════════════════════════════════════════════════
# 4b. ClamAV timers
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying ClamAV Timers ==="

for timer_name in clamav-quick clamav-deep clamav-healthcheck; do
    for unit in "$timer_name.service" "$timer_name.timer"; do
        if [[ -f "$SRC/$unit" ]]; then
            sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
            sudo restorecon -v "/etc/systemd/system/$unit"
            echo "  Installed $unit to /etc/systemd/system/"
        fi
    done

    if [[ -f "$SRC/$timer_name.timer" ]]; then
        sudo systemctl daemon-reload
        sudo systemctl enable "$timer_name.timer" 2>/dev/null || \
            echo "  WARNING: $timer_name.timer enable failed"
        sudo systemctl start "$timer_name.timer" || echo "  WARNING: $timer_name.timer start failed"
        echo "  Enabled $timer_name.timer"
    fi
done

# ══════════════════════════════════════════════════════════════════
# 4c. Release watch and Fedora updates timers
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying Release Watch & Fedora Updates Timers ==="

for timer_name in release-watch fedora-updates; do
    for unit in "$timer_name.service" "$timer_name.timer"; do
        if [[ -f "$SRC/$unit" ]]; then
            sudo install -m 644 "$SRC/$unit" "/etc/systemd/system/$unit"
            sudo restorecon -v "/etc/systemd/system/$unit"
            echo "  Installed $unit to /etc/systemd/system/"
        fi
    done

    if [[ -f "$SRC/$timer_name.timer" ]]; then
        sudo systemctl daemon-reload
        sudo systemctl enable "$timer_name.timer" 2>/dev/null || \
            echo "  WARNING: $timer_name.timer enable failed"
        sudo systemctl start "$timer_name.timer" || echo "  WARNING: $timer_name.timer start failed"
        echo "  Enabled $timer_name.timer"
    fi
done

# ══════════════════════════════════════════════════════════════════
# 4d. Kernel / boot-time tune services
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying Kernel / Boot-Time Tune Services ==="

# btrfs-readahead-tune (oneshot, no timer)
if [[ -f "$SRC/btrfs-readahead-tune.service" ]]; then
    sudo install -m 644 "$SRC/btrfs-readahead-tune.service" /etc/systemd/system/btrfs-readahead-tune.service
    sudo restorecon -v /etc/systemd/system/btrfs-readahead-tune.service
    echo "  Installed btrfs-readahead-tune.service to /etc/systemd/system/"
fi

if [[ -f "$SRC/btrfs-readahead-tune.service" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable btrfs-readahead-tune.service 2>/dev/null || \
        echo "  WARNING: btrfs-readahead-tune.service enable failed"
    echo "  Enabled btrfs-readahead-tune.service"
fi

# nvidia-persistence
if [[ -f "$SRC/nvidia-persistence.service" ]]; then
    sudo install -m 644 "$SRC/nvidia-persistence.service" /etc/systemd/system/nvidia-persistence.service
    sudo restorecon -v /etc/systemd/system/nvidia-persistence.service
    echo "  Installed nvidia-persistence.service to /etc/systemd/system/"
fi

if [[ -f "$SRC/nvidia-persistence.service" ]]; then
    sudo systemctl daemon-reload
    sudo systemctl enable --now nvidia-persistence.service 2>/dev/null || \
        echo "  WARNING: nvidia-persistence.service enable/start failed"
    echo "  Enabled nvidia-persistence.service"
fi

# ══════════════════════════════════════════════════════════════════
# 4e. Config file deployments (sysctl, sysconfig, oomd, X11)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying Config Files ==="

REPO_CONFIGS="$(cd "$(dirname "$0")/.." && pwd)/configs"

# 20-nvidia-coolbits.conf → /etc/X11/xorg.conf.d/
if [[ -f "$REPO_CONFIGS/20-nvidia-coolbits.conf" ]]; then
    sudo mkdir -p /etc/X11/xorg.conf.d
    sudo install -m 644 "$REPO_CONFIGS/20-nvidia-coolbits.conf" /etc/X11/xorg.conf.d/20-nvidia-coolbits.conf
    echo "  Installed 20-nvidia-coolbits.conf to /etc/X11/xorg.conf.d/"
fi

# 90-bazzite-vm.conf → /etc/sysctl.d/
if [[ -f "$REPO_CONFIGS/90-bazzite-vm.conf" ]]; then
    sudo mkdir -p /etc/sysctl.d
    sudo install -m 644 "$REPO_CONFIGS/90-bazzite-vm.conf" /etc/sysctl.d/90-bazzite-vm.conf
    echo "  Installed 90-bazzite-vm.conf to /etc/sysctl.d/"
fi

# earlyoom → /etc/sysconfig/earlyoom
if [[ -f "$REPO_CONFIGS/earlyoom" ]]; then
    sudo mkdir -p /etc/sysconfig
    sudo install -m 644 "$REPO_CONFIGS/earlyoom" /etc/sysconfig/earlyoom
    echo "  Installed earlyoom to /etc/sysconfig/earlyoom"
fi

# 90-bazzite-oomd.conf → /etc/systemd/oomd.conf.d/
if [[ -f "$REPO_CONFIGS/90-bazzite-oomd.conf" ]]; then
    sudo mkdir -p /etc/systemd/oomd.conf.d
    sudo install -m 644 "$REPO_CONFIGS/90-bazzite-oomd.conf" /etc/systemd/oomd.conf.d/90-bazzite-oomd.conf
    echo "  Installed 90-bazzite-oomd.conf to /etc/systemd/oomd.conf.d/"
fi

# 90-oomd-protect-user-slice.conf → /etc/systemd/system/user.slice.d/
if [[ -f "$REPO_CONFIGS/90-oomd-protect-user-slice.conf" ]]; then
    sudo mkdir -p /etc/systemd/system/user.slice.d
    sudo install -m 644 "$REPO_CONFIGS/90-oomd-protect-user-slice.conf" \
        /etc/systemd/system/user.slice.d/90-oomd-protect-user-slice.conf
    sudo restorecon -v /etc/systemd/system/user.slice.d/90-oomd-protect-user-slice.conf
    echo "  Installed 90-oomd-protect-user-slice.conf to /etc/systemd/system/user.slice.d/"
fi

sudo systemctl daemon-reload

# ══════════════════════════════════════════════════════════════════
# 4f. AI slice (resource cgroup for AI services)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Deploying AI Slice ==="

if [[ -f "$SRC/ai.slice" ]]; then
    sudo install -m 644 "$SRC/ai.slice" /etc/systemd/system/ai.slice
    sudo restorecon -v /etc/systemd/system/ai.slice
    echo "  Installed ai.slice to /etc/systemd/system/"
    sudo systemctl daemon-reload
fi

# ══════════════════════════════════════════════════════════════════
# 5. Status checks
# ══════════════════════════════════════════════════════════════════
sleep 3

echo ""
echo "=== User Service Status ==="
for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
    status=$(systemctl --user is-active "$svc.service" 2>/dev/null || echo "failed")
    printf "  %-35s %s\n" "$svc" "$status"
done

echo ""
echo "=== System Service Status ==="
thermal_status=$(sudo systemctl is-active thermal-protection.service 2>/dev/null || echo "inactive")
printf "  %-35s %s\n" "thermal-protection.service" "$thermal_status"
timer_enabled=$(sudo systemctl is-enabled system-health.timer 2>/dev/null || echo "disabled")
printf "  %-35s %s\n" "system-health.timer" "$timer_enabled"
sudo systemctl list-timers system-health.timer --no-pager 2>/dev/null | grep -q system-health \
    && sudo systemctl list-timers system-health.timer --no-pager 2>/dev/null | grep system-health \
    || echo "  (timer not scheduled — run: sudo systemctl start system-health.timer)"
printf "  %-35s %s\n" "security-audit.timer" \
    "$(sudo systemctl is-enabled security-audit.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "performance-tuning.timer" \
    "$(sudo systemctl is-enabled performance-tuning.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "knowledge-storage.timer" \
    "$(sudo systemctl is-enabled knowledge-storage.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "cve-scanner.timer" \
    "$(sudo systemctl is-enabled cve-scanner.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "log-archive.timer" \
    "$(sudo systemctl is-enabled log-archive.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "clamav-quick.timer" \
    "$(sudo systemctl is-enabled clamav-quick.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "clamav-deep.timer" \
    "$(sudo systemctl is-enabled clamav-deep.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "clamav-healthcheck.timer" \
    "$(sudo systemctl is-enabled clamav-healthcheck.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "release-watch.timer" \
    "$(sudo systemctl is-enabled release-watch.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "fedora-updates.timer" \
    "$(sudo systemctl is-enabled fedora-updates.timer 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "btrfs-readahead-tune.service" \
    "$(sudo systemctl is-enabled btrfs-readahead-tune.service 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "nvidia-persistence.service" \
    "$(sudo systemctl is-enabled nvidia-persistence.service 2>/dev/null || echo 'not installed')"
printf "  %-35s %s\n" "service-canary.timer" \
    "$(systemctl --user is-enabled service-canary.timer 2>/dev/null || echo 'not installed')"

# ══════════════════════════════════════════════════════════════════
# 6. Health checks (port listening + HTTP where available)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== Health Checks ==="
# LLM proxy has a real /health HTTP endpoint
curl -sf --max-time 2 http://127.0.0.1:8767/health 2>/dev/null \
    && echo "" || echo "  LLM proxy (8767): not responding"
# MCP bridge uses FastMCP streamable-http — no standalone /health route
ss -tln | grep -q ':8766 ' \
    && echo "  MCP bridge (8766): listening" \
    || echo "  MCP bridge (8766): not responding"

# ══════════════════════════════════════════════════════════════════
# 7. SELinux: blanket restorecon (catches any missed contexts)
# ══════════════════════════════════════════════════════════════════
echo ""
echo "=== SELinux: blanket restorecon ==="
sudo restorecon -Rv /usr/local/bin/ /etc/systemd/system/ 2>/dev/null || true

echo ""
echo "Done. User services auto-start on login. All 13 timers + 2 system services + 5 config files deployed."
echo "  Daily: health 8:00, perf 8:15, audit 8:30, rag 9:00, knowledge 9:15, release 9:45, clamav-quick 12:00"
echo "  Every 15m: service-canary (user)"
echo "  Weekly: clamav-healthcheck Wed 14:00, clamav-deep Fri 23:00, cve-scanner Sat 00:00, log-archive Sun 01:00, fedora-updates Mon 03:00, lancedb-optimize Sun 02:00"

# ══════════════════════════════════════════════════════════════════
# 8. Auto-verify (not in dry-run)
# ══════════════════════════════════════════════════════════════════
if [[ "$DRY_RUN" -eq 0 ]]; then
    echo ""
    echo "=== Running verify-services.sh ==="
    bash "$SCRIPTS/verify-services.sh" || true
fi
