#!/bin/bash
# ClamAV security system health check with terminal UI, notifications, and logging
# Deploy to: /usr/local/bin/clamav-healthcheck.sh (chmod 755)
# Runs weekly via systemd timer to verify the entire security notification pipeline
set -uo pipefail

# --- Configuration ---
QUARANTINE_DIR="/home/lch/security/quarantine"
LOG_DIR="/var/log/clamav-scans"
HEALTHCHECK_LOG="/home/lch/security/.healthcheck.log"
STATUS_TMP="/home/lch/security/.status.tmp"
LCH_UID="$(id -u lch)"
INTERACTIVE=false
[ -t 1 ] && INTERACTIVE=true

# --- ANSI Colors ---
BCYAN='\e[1;36m'
GREEN='\e[0;32m'
RED='\e[0;31m'
YELLOW='\e[0;33m'
BWHITE='\e[1;37m'
DIM='\e[2m'
RESET='\e[0m'

# --- Counters ---
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# --- Helper: terminal output (only when interactive) ---
print_banner() {
    $INTERACTIVE || return 0
    local date_str
    date_str="$(date '+%a %b %d, %Y %I:%M %p')"
    echo ""
    echo -e "  ${BCYAN}+--------------------------------------+${RESET}"
    echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE SECURITY HEALTHCHECK${RESET}  ${BCYAN}│${RESET}"
    echo -e "  ${BCYAN}|${RESET}  ${DIM}${date_str}${RESET}$(printf '%*s' $((24 - ${#date_str})) '')${BCYAN}|${RESET}"
    echo -e "  ${BCYAN}+--------------------------------------+${RESET}"
    echo ""
}

print_check() {
    $INTERACTIVE || return 0
    local icon="$1"
    local label="$2"
    local status="$3"
    local color

    case "$status" in
        OK)   color="$GREEN" ;;
        WARN) color="$YELLOW" ;;
        FAIL) color="$RED" ;;
    esac

    printf "  [${color}${icon}${RESET}] %-40s ${color}[${status}]${RESET}\n" "$label"
}

print_summary() {
    $INTERACTIVE || return 0
    local border_color status_icon status_text

    if [[ $FAIL_COUNT -gt 0 ]]; then
        border_color="$RED"
        status_icon="✗"
        status_text="FAILURES DETECTED"
    elif [[ $WARN_COUNT -gt 0 ]]; then
        border_color="$YELLOW"
        status_icon="✓"
        status_text="ALL SYSTEMS GO"
    else
        border_color="$GREEN"
        status_icon="✓"
        status_text="ALL SYSTEMS GO"
    fi

    local total=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
    echo ""
    echo -e "  ${border_color}+--- HEALTH STATUS ---------------------+${RESET}"
    echo -e "  ${border_color}|${RESET}  Status:    ${status_icon} ${status_text}$(printf '%*s' $((20 - ${#status_text})) '')${border_color}|${RESET}"
    echo -e "  ${border_color}|${RESET}  Checks:    $(printf '%-27s' "${total} passed, ${FAIL_COUNT} failed")${border_color}|${RESET}"
    echo -e "  ${border_color}|${RESET}  Warnings:  $(printf '%-27s' "${WARN_COUNT}")${border_color}|${RESET}"
    echo -e "  ${border_color}+---------------------------------------+${RESET}"
    echo ""
}

# --- Helper: desktop notification ---
notify() {
    local urgency="$1"
    local summary="$2"
    local body="$3"
    local icon="$4"
    sudo -u lch DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${LCH_UID}/bus" \
        notify-send --app-name="Bazzite Security" --icon="$icon" --urgency="$urgency" "$summary" "$body"
}

# --- Check functions ---
check_ok() {
    local label="$1"
    PASS_COUNT=$((PASS_COUNT + 1))
    print_check "✓" "$label" "OK"
}

check_warn() {
    local label="$1"
    WARN_COUNT=$((WARN_COUNT + 1))
    print_check "⚠" "$label" "WARN"
}

check_fail() {
    local label="$1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    print_check "✗" "$label" "FAIL"
}

# ===========================
# MAIN
# ===========================

print_banner

# --- Check 1: clamdscan binary ---
if command -v clamdscan &>/dev/null; then
    check_ok "ClamAV daemon scanner present"
else
    check_fail "ClamAV daemon scanner not found"
fi

# --- Check 2: freshclam binary ---
if command -v freshclam &>/dev/null; then
    check_ok "Freshclam updater present"
else
    check_fail "Freshclam updater not found"
fi

# --- Check 3: Signature freshness ---
SIG_FILE="/var/lib/clamav/daily.cvd"
if [[ -f "$SIG_FILE" ]]; then
    SIG_AGE_SECONDS=$(( $(date +%s) - $(stat -c %Y "$SIG_FILE") ))
    SIG_AGE_DAYS=$(( SIG_AGE_SECONDS / 86400 ))
    if (( SIG_AGE_DAYS > 7 )); then
        check_fail "Virus signatures stale (${SIG_AGE_DAYS} days old)"
    elif (( SIG_AGE_DAYS > 3 )); then
        check_warn "Virus signatures aging (${SIG_AGE_DAYS} days old)"
    else
        check_ok "Virus signatures fresh (${SIG_AGE_DAYS} day(s) old)"
    fi
elif [[ -f "/var/lib/clamav/daily.cld" ]]; then
    SIG_FILE="/var/lib/clamav/daily.cld"
    SIG_AGE_SECONDS=$(( $(date +%s) - $(stat -c %Y "$SIG_FILE") ))
    SIG_AGE_DAYS=$(( SIG_AGE_SECONDS / 86400 ))
    if (( SIG_AGE_DAYS > 7 )); then
        check_fail "Virus signatures stale (${SIG_AGE_DAYS} days old)"
    elif (( SIG_AGE_DAYS > 3 )); then
        check_warn "Virus signatures aging (${SIG_AGE_DAYS} days old)"
    else
        check_ok "Virus signatures fresh (${SIG_AGE_DAYS} day(s) old)"
    fi
else
    check_fail "Virus signature database not found"
fi

# --- Check 4: Quarantine directory ---
if [[ -d "$QUARANTINE_DIR" ]]; then
    check_ok "Quarantine directory exists"
else
    check_fail "Quarantine directory missing"
fi

# --- Check 5: Log directory ---
if [[ -d "$LOG_DIR" && -w "$LOG_DIR" ]]; then
    check_ok "Log directory exists and writable"
elif [[ -d "$LOG_DIR" ]]; then
    check_fail "Log directory exists but not writable"
else
    check_fail "Log directory missing"
fi

# --- Check 6: clamav-quick.timer ---
if systemctl is-active --quiet clamav-quick.timer 2>/dev/null; then
    check_ok "Quick scan timer active"
else
    check_fail "Quick scan timer not active"
fi

# --- Check 7: clamav-deep.timer ---
if systemctl is-active --quiet clamav-deep.timer 2>/dev/null; then
    check_ok "Deep scan timer active"
else
    check_fail "Deep scan timer not active"
fi

# --- Check 8: msmtp configured ---
if [[ -f /home/lch/.msmtprc ]]; then
    check_ok "Email alerts configured (msmtp)"
else
    check_warn "msmtp not configured"
fi

# --- Check 9: Disk space for signatures ---
if [[ -d /var/lib/clamav ]]; then
    CLAMAV_SIZE_KB=$(du -sk /var/lib/clamav 2>/dev/null | awk '{print $1}')
    CLAMAV_SIZE_MB=$(( CLAMAV_SIZE_KB / 1024 ))
    if (( CLAMAV_SIZE_KB > 1048576 )); then
        check_warn "Signature DB large (${CLAMAV_SIZE_MB}MB, >1GB)"
    else
        check_ok "Signature DB size OK (${CLAMAV_SIZE_MB}MB)"
    fi
else
    check_fail "ClamAV data directory missing"
fi

# --- Check 10: Status file writable ---
if touch "$STATUS_TMP" 2>/dev/null && rm -f "$STATUS_TMP" 2>/dev/null; then
    check_ok "Status file writable"
else
    check_fail "Status file not writable"
fi

# --- Check 11: clamd@scan service configured ---
if systemctl cat clamd@scan &>/dev/null; then
    check_ok "clamd service configured"
else
    check_fail "clamd service not configured"
fi

# --- Check 12: system-health.timer active ---
if systemctl is-active --quiet system-health.timer 2>/dev/null; then
    check_ok "Health snapshot timer active"
else
    check_fail "system-health.timer not active"
fi

# --- Check 13: health log freshness (warn if older than 48 hours) ---
if [[ -L /var/log/system-health/health-latest.log ]]; then
    HEALTH_AGE=$(( $(date +%s) - $(stat -c %Y /var/log/system-health/health-latest.log) ))
    if [[ $HEALTH_AGE -gt 172800 ]]; then
        check_warn "Health log older than 48 hours"
    else
        HEALTH_AGE_H=$(( HEALTH_AGE / 3600 ))
        check_ok "Health log fresh (${HEALTH_AGE_H}h old)"
    fi
else
    check_warn "No health log symlink found"
fi

# --- Terminal summary ---
print_summary

# --- Log results ---
{
    echo "[$(date -Iseconds)] Healthcheck: ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${WARN_COUNT} warnings"
} >> "$HEALTHCHECK_LOG"

# --- Write status file so tray app updates (preserves health_* keys) ---
STATUS_FILE="/home/lch/security/.status"
if [[ $FAIL_COUNT -gt 0 ]]; then
    HC_RESULT="error"
else
    HC_RESULT="clean"
fi
HC_TIMESTAMP="$(date -Iseconds)"
HC_MSG="Healthcheck: ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${WARN_COUNT} warnings"
python3 -c "
import json, os
path = '$STATUS_FILE'
tmp = '${STATUS_TMP}'
try:
    with open(path, 'r') as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
    data = {}
data.update({
    'state': 'idle',
    'scan_type': '',
    'message': '$HC_MSG',
    'current_dir': '',
    'dirs_completed': 0,
    'dirs_total': 0,
    'result': '$HC_RESULT',
    'threat_count': 0,
    'files_scanned': 0,
    'duration': '',
    'last_scan_time': '$HC_TIMESTAMP',
    'last_scan_result': '$HC_RESULT',
    'timestamp': '$HC_TIMESTAMP'
})
try:
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.rename(tmp, path)
except (PermissionError, OSError):
    pass
" 2>/dev/null || true
chown lch:lch "$STATUS_FILE" 2>/dev/null

# --- Desktop notifications ---
TOTAL_CHECKS=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
if [[ $FAIL_COUNT -gt 0 ]]; then
    notify "critical" "Health check FAILED: ${FAIL_COUNT} issues" \
        "${TOTAL_CHECKS} checks run, ${FAIL_COUNT} failed, ${WARN_COUNT} warnings" \
        "dialog-warning"
elif [[ $WARN_COUNT -gt 0 ]]; then
    notify "normal" "Health check: ${WARN_COUNT} warnings" \
        "All ${TOTAL_CHECKS} checks passed with ${WARN_COUNT} warning(s)" \
        "security-medium"
else
    notify "low" "Health check passed" \
        "All ${TOTAL_CHECKS} checks passed, no issues found" \
        "security-high"
fi

# --- Email alert on critical failures only ---
if [[ $FAIL_COUNT -gt 0 ]]; then
    if command -v /usr/local/bin/clamav-alert.sh &>/dev/null; then
        /usr/local/bin/clamav-alert.sh "healthcheck" "error" "$FAIL_COUNT" "$TOTAL_CHECKS" "n/a" "$HEALTHCHECK_LOG"
    fi
fi

# --- Exit code ---
if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi
exit 0
