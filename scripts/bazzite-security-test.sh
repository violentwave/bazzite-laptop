#!/bin/bash
# Bazzite Security Test Suite — comprehensive system validation
# Deploy to: /usr/local/bin/bazzite-security-test.sh (chmod 755)
# Usage: sudo bazzite-security-test.sh
# Validates every component of the security notification system end-to-end.
set -uo pipefail

# --- Root check ---
if [[ $EUID -ne 0 ]]; then
    echo "Error: Must run as root" >&2
    echo "Usage: sudo $0" >&2
    exit 1
fi

# --- Configuration ---
TOTAL_TESTS=15
QUARANTINE_DIR="/home/lch/security/quarantine"
STATUS_FILE="/home/lch/security/.status"
STATUS_BACKUP="/home/lch/security/.status.backup"
ICON_DIR="/home/lch/security/icons/hicolor/scalable/status"
ICON_THEME="/home/lch/security/icons/hicolor/index.theme"
LOG_DIR="/var/log/clamav-scans"
MSMTP_CONF="/home/lch/.msmtprc"
TEST_REPORT="/home/lch/security/test-report-$(date +%Y%m%d-%H%M%S).log"
LCH_UID="$(id -u lch)"

# --- ANSI Colors ---
BCYAN='\e[1;36m'
GREEN='\e[0;32m'
RED='\e[0;31m'
YELLOW='\e[0;33m'
BWHITE='\e[1;37m'
DIM='\e[2m'
RESET='\e[0m'

# --- Test tracking ---
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
RESULTS=()       # "PASS|WARN|FAIL"
RESULT_MSGS=()   # short description for summary
TEST_STARTED_CLAMD=false

# --- Logging ---
mkdir -p "$(dirname "$TEST_REPORT")"
exec > >(tee -a "$TEST_REPORT") 2>&1

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

# --- Banner ---
echo ""
echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE SECURITY TEST SUITE${RESET}    ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}│${RESET}  ${DIM}Comprehensive system validation${RESET}     ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"
echo ""

# --- System info header ---
echo -e "  ${DIM}─── System Info ─────────────────────────${RESET}"
echo -e "  ${DIM}Hostname:  $(hostname)${RESET}"
echo -e "  ${DIM}Date:      $(date '+%B %d, %Y %I:%M %p')${RESET}"
echo -e "  ${DIM}Kernel:    $(uname -r)${RESET}"
echo -e "  ${DIM}ClamAV:    $(clamdscan --version 2>/dev/null || echo 'not found')${RESET}"
echo -e "  ${DIM}Uptime:    $(uptime -p 2>/dev/null || uptime)${RESET}"
echo -e "  ${DIM}─────────────────────────────────────────${RESET}"
echo ""

# --- Status file backup ---
cp "$STATUS_FILE" "$STATUS_BACKUP" 2>/dev/null || true

# --- Cleanup handler ---
cleanup() {
    # Remove EICAR test files
    if [[ -d "${EICAR_DIR:-}" ]]; then
        rm -rf "$EICAR_DIR" 2>/dev/null
    fi
    local eicar_q="$QUARANTINE_DIR/eicar-test.txt"
    if [[ -f "$eicar_q" ]]; then
        chattr -i "$eicar_q" 2>/dev/null
        chmod 644 "$eicar_q" 2>/dev/null
        rm -f "$eicar_q" 2>/dev/null
    fi
    # Stop clamd if we started it
    if $TEST_STARTED_CLAMD; then
        systemctl stop clamd@scan 2>/dev/null || true
    fi
    # Restore status file
    if [[ -f "$STATUS_BACKUP" ]]; then
        cp "$STATUS_BACKUP" "$STATUS_FILE" 2>/dev/null
        rm -f "$STATUS_BACKUP" 2>/dev/null
    fi
    chmod 644 "$TEST_REPORT" 2>/dev/null
}
trap cleanup EXIT

# --- Test helpers ---
print_result() {
    local num="$1"
    local label="$2"
    local status="$3"  # PASS, WARN, FAIL
    local detail="${4:-}"

    local status_text color
    case "$status" in
        PASS) status_text="[PASS ✓]"; color="$GREEN"; PASS_COUNT=$((PASS_COUNT + 1)) ;;
        WARN) status_text="[WARN !]"; color="$YELLOW"; WARN_COUNT=$((WARN_COUNT + 1)) ;;
        FAIL) status_text="[FAIL ✗]"; color="$RED"; FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    esac

    RESULTS+=("$status")
    RESULT_MSGS+=("$(printf '[%02d] %s' "$num" "$label")")

    printf "  [%02d/%02d] %-42s ${color}%s${RESET}\n" "$num" "$TOTAL_TESTS" "$label" "$status_text"
    if [[ -n "$detail" ]]; then
        echo -e "          └─ ${DIM}${detail}${RESET}"
    fi
}

# ===========================
# PHASE 1: PREREQUISITES
# ===========================
echo -e "  ${BWHITE}Phase 1: Prerequisites${RESET}"
echo ""

# [01] clamd package installed
if rpm -q clamd &>/dev/null || rpm -q clamav &>/dev/null; then
    clamd_ver=$(rpm -q clamd 2>/dev/null || rpm -q clamav 2>/dev/null)
    print_result 1 "ClamAV package installed" "PASS" "$clamd_ver"
else
    print_result 1 "ClamAV package installed" "FAIL" "clamd/clamav package not found"
fi

# [02] clamdscan binary exists
if command -v clamdscan &>/dev/null; then
    print_result 2 "clamdscan binary exists" "PASS" "$(which clamdscan)"
else
    print_result 2 "clamdscan binary exists" "FAIL" "clamdscan not found in PATH"
fi

# [03] freshclam daemon active
if systemctl is-active --quiet clamav-freshclam.service 2>/dev/null; then
    print_result 3 "freshclam daemon active" "PASS" "clamav-freshclam.service running"
elif pgrep -x freshclam &>/dev/null; then
    print_result 3 "freshclam daemon active" "PASS" "freshclam process detected"
else
    print_result 3 "freshclam daemon active" "FAIL" "clamav-freshclam.service is not active"
fi

# [04] Virus signatures exist and fresh
SIG_FILE=""
for f in /var/lib/clamav/daily.cvd /var/lib/clamav/daily.cld; do
    [[ -f "$f" ]] && SIG_FILE="$f" && break
done
if [[ -n "$SIG_FILE" ]]; then
    SIG_AGE_SECS=$(( $(date +%s) - $(stat -c '%Y' "$SIG_FILE") ))
    SIG_AGE_DAYS=$(( SIG_AGE_SECS / 86400 ))
    if (( SIG_AGE_DAYS <= 3 )); then
        print_result 4 "Virus signatures fresh" "PASS" "${SIG_AGE_DAYS}d old (updated within 3 days)"
    elif (( SIG_AGE_DAYS <= 7 )); then
        print_result 4 "Virus signatures fresh" "WARN" "${SIG_AGE_DAYS}d old (consider updating)"
    else
        print_result 4 "Virus signatures fresh" "FAIL" "${SIG_AGE_DAYS}d old (stale >7 days)"
    fi
else
    print_result 4 "Virus signatures fresh" "FAIL" "No signature database found in /var/lib/clamav/"
fi

# [05] SELinux antivirus boolean
SEBOOL=$(getsebool antivirus_can_scan_system 2>/dev/null || echo "")
if echo "$SEBOOL" | grep -q "on"; then
    print_result 5 "SELinux antivirus boolean set" "PASS" "$SEBOOL"
elif [[ -z "$SEBOOL" ]]; then
    print_result 5 "SELinux antivirus boolean set" "WARN" "getsebool not available or SELinux disabled"
else
    print_result 5 "SELinux antivirus boolean set" "FAIL" "$SEBOOL"
fi

echo ""

# ===========================
# PHASE 2: INFRASTRUCTURE
# ===========================
echo -e "  ${BWHITE}Phase 2: Infrastructure${RESET}"
echo ""

# [06] clamd can start
CLAMD_START=$(date +%s)
systemctl start clamd@scan 2>/dev/null
if clamdscan --ping 60:2 2>/dev/null; then
    CLAMD_END=$(date +%s)
    CLAMD_SECS=$((CLAMD_END - CLAMD_START))
    TEST_STARTED_CLAMD=true
    print_result 6 "clamd daemon starts and responds" "PASS" "Ready in ${CLAMD_SECS}s"
else
    print_result 6 "clamd daemon starts and responds" "FAIL" "clamd failed to respond within 120s"
    systemctl stop clamd@scan 2>/dev/null || true
fi

# [07] Scan timers active
TIMER_STATUS=""
TIMER_OK=true
for timer in clamav-quick.timer clamav-deep.timer clamav-healthcheck.timer; do
    if systemctl is-active --quiet "$timer" 2>/dev/null; then
        TIMER_STATUS+="$timer: active  "
    elif systemctl is-enabled --quiet "$timer" 2>/dev/null; then
        TIMER_STATUS+="$timer: enabled  "
    else
        TIMER_STATUS+="$timer: MISSING  "
        TIMER_OK=false
    fi
done
if $TIMER_OK; then
    print_result 7 "Scan timers active" "PASS" "$TIMER_STATUS"
else
    print_result 7 "Scan timers active" "WARN" "$TIMER_STATUS"
fi

# [08] Log directory
if [[ -d "$LOG_DIR" ]]; then
    LOG_PERMS=$(stat -c '%a' "$LOG_DIR")
    if [[ "$LOG_PERMS" == "755" ]]; then
        print_result 8 "Log directory exists, correct perms" "PASS" "$LOG_DIR ($LOG_PERMS)"
    else
        print_result 8 "Log directory exists, correct perms" "WARN" "$LOG_DIR (perms=$LOG_PERMS, expected 755)"
    fi
else
    print_result 8 "Log directory exists, correct perms" "FAIL" "$LOG_DIR does not exist"
fi

# [09] Quarantine directory
if [[ -d "$QUARANTINE_DIR" ]]; then
    Q_PERMS=$(stat -c '%a' "$QUARANTINE_DIR")
    Q_OWNER=$(stat -c '%U:%G' "$QUARANTINE_DIR")
    if [[ "$Q_PERMS" == "750" ]] && [[ "$Q_OWNER" == "root:lch" ]]; then
        print_result 9 "Quarantine dir ownership/perms" "PASS" "$Q_OWNER $Q_PERMS"
    else
        print_result 9 "Quarantine dir ownership/perms" "WARN" "owner=$Q_OWNER perms=$Q_PERMS (expected root:lch 750)"
    fi
else
    print_result 9 "Quarantine dir ownership/perms" "FAIL" "$QUARANTINE_DIR does not exist"
fi

# [10] Status file writable
STATUS_TMP="/home/lch/security/.status.tmp.test"
if echo '{"state":"test"}' > "$STATUS_TMP" 2>/dev/null && mv -f "$STATUS_TMP" "$STATUS_FILE" 2>/dev/null; then
    print_result 10 "Status file atomic write" "PASS" "$STATUS_FILE writable"
else
    print_result 10 "Status file atomic write" "FAIL" "Cannot write to $STATUS_FILE"
    rm -f "$STATUS_TMP" 2>/dev/null
fi

echo ""

# ===========================
# PHASE 3: SCANNING
# ===========================
echo -e "  ${BWHITE}Phase 3: Scanning${RESET}"
echo ""

# [11] EICAR threat detection
EICAR_DIR="/tmp/bazzite-test-$$"
mkdir -p "$EICAR_DIR"
# shellcheck disable=SC2016
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > "$EICAR_DIR/eicar-test.txt"

if ! $TEST_STARTED_CLAMD; then
    systemctl start clamd@scan 2>/dev/null
    clamdscan --ping 60:2 2>/dev/null && TEST_STARTED_CLAMD=true
fi

if $TEST_STARTED_CLAMD; then
    EICAR_START=$(date +%s)
    SCAN_RESULT=$(clamdscan --fdpass --multiscan --infected --move="$QUARANTINE_DIR" "$EICAR_DIR" 2>&1) || true
    EICAR_END=$(date +%s)
    EICAR_SECS=$((EICAR_END - EICAR_START))

    EICAR_Q="$QUARANTINE_DIR/eicar-test.txt"
    EICAR_DETECTED=false
    EICAR_QUARANTINED=false
    EICAR_LOCKED=false

    # Check detection
    echo "$SCAN_RESULT" | grep -q "FOUND" && EICAR_DETECTED=true

    # Check quarantine
    [[ -f "$EICAR_Q" ]] && EICAR_QUARANTINED=true

    # Test lockdown
    if $EICAR_QUARANTINED; then
        chmod 000 "$EICAR_Q" 2>/dev/null
        chattr +i "$EICAR_Q" 2>/dev/null
        # Verify immutable flag
        if lsattr "$EICAR_Q" 2>/dev/null | grep -q "i"; then
            EICAR_LOCKED=true
        fi
    fi

    if $EICAR_DETECTED && $EICAR_QUARANTINED && $EICAR_LOCKED; then
        print_result 11 "EICAR threat detection + quarantine" "PASS" "Detected+quarantined+locked in ${EICAR_SECS}s"
    elif $EICAR_DETECTED && $EICAR_QUARANTINED; then
        print_result 11 "EICAR threat detection + quarantine" "WARN" "Detected+quarantined but chattr failed"
    elif $EICAR_DETECTED; then
        print_result 11 "EICAR threat detection + quarantine" "WARN" "Detected but not moved to quarantine"
    else
        print_result 11 "EICAR threat detection + quarantine" "FAIL" "EICAR not detected by clamdscan"
    fi

    # Clean up EICAR from quarantine
    if [[ -f "$EICAR_Q" ]]; then
        chattr -i "$EICAR_Q" 2>/dev/null
        chmod 644 "$EICAR_Q" 2>/dev/null
        rm -f "$EICAR_Q" 2>/dev/null
    fi
else
    print_result 11 "EICAR threat detection + quarantine" "FAIL" "clamd not running, cannot scan"
fi

# Clean up EICAR test directory
rm -rf "$EICAR_DIR" 2>/dev/null
unset EICAR_DIR

# Stop clamd to reclaim memory
if $TEST_STARTED_CLAMD; then
    systemctl stop clamd@scan 2>/dev/null || true
    TEST_STARTED_CLAMD=false
fi

echo ""

# ===========================
# PHASE 4: NOTIFICATIONS
# ===========================
echo -e "  ${BWHITE}Phase 4: Notifications${RESET}"
echo ""

# [12] Desktop notification
if command -v notify-send &>/dev/null; then
    if sudo -u lch DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${LCH_UID}/bus" \
        notify-send --app-name="Bazzite Security" --icon=security-high \
        "Test Notification" "Security test suite running" 2>/dev/null; then
        print_result 12 "Desktop notification (notify-send)" "PASS" "Notification sent"
    else
        print_result 12 "Desktop notification (notify-send)" "WARN" "notify-send exited non-zero"
    fi
else
    print_result 12 "Desktop notification (notify-send)" "FAIL" "notify-send not found"
fi

# [13] Email test
if [[ -f "$MSMTP_CONF" ]]; then
    TO_EMAIL=$(awk '/^\s*from\s/ {print $2; exit}' "$MSMTP_CONF" 2>/dev/null)
    if [[ -z "$TO_EMAIL" ]]; then
        TO_EMAIL=$(awk '/^\s*user\s/ {print $2; exit}' "$MSMTP_CONF" 2>/dev/null)
    fi

    if [[ -n "$TO_EMAIL" ]]; then
        EMAIL_BODY="This is an automated test from bazzite-security-test.sh. All systems operational."
        if printf "To: %s\nSubject: Bazzite Security Test — %s\nContent-Type: text/plain; charset=UTF-8\n\n%s\n" \
            "$TO_EMAIL" "$(date '+%Y-%m-%d %H:%M')" "$EMAIL_BODY" | \
            msmtp --file="$MSMTP_CONF" --read-recipients 2>/dev/null; then
            print_result 13 "Email alert (msmtp)" "PASS" "Test email sent to $TO_EMAIL"
        else
            print_result 13 "Email alert (msmtp)" "WARN" "msmtp send failed (check config/network)"
        fi
    else
        print_result 13 "Email alert (msmtp)" "WARN" "No recipient found in $MSMTP_CONF"
    fi
else
    print_result 13 "Email alert (msmtp)" "WARN" "$MSMTP_CONF not found"
fi

echo ""

# ===========================
# PHASE 5: TRAY & MENU
# ===========================
echo -e "  ${BWHITE}Phase 5: Tray & Menu${RESET}"
echo ""

# [14] Tray app running
if pgrep -f bazzite-security-tray &>/dev/null; then
    TRAY_PID=$(pgrep -f bazzite-security-tray | head -1)
    print_result 14 "Tray app running" "PASS" "PID $TRAY_PID"
else
    print_result 14 "Tray app running" "WARN" "Not running. Start: python3 ~/security/bazzite-security-tray.py"
fi

# [15] Custom icons exist
ICONS_OK=true
ICONS_MISSING=""
for icon in bazzite-sec-green bazzite-sec-yellow bazzite-sec-red bazzite-sec-blue bazzite-sec-blank; do
    if [[ ! -f "$ICON_DIR/${icon}.svg" ]]; then
        ICONS_OK=false
        ICONS_MISSING+=" ${icon}.svg"
    fi
done
if ! [[ -f "$ICON_THEME" ]]; then
    ICONS_OK=false
    ICONS_MISSING+=" index.theme"
fi

if $ICONS_OK; then
    print_result 15 "Custom tray icons installed" "PASS" "5 SVGs + index.theme"
else
    print_result 15 "Custom tray icons installed" "FAIL" "Missing:${ICONS_MISSING}"
fi

echo ""

# ===========================
# SUMMARY
# ===========================
BORDER_COLOR="$GREEN"
if (( FAIL_COUNT > 0 )); then
    BORDER_COLOR="$RED"
elif (( WARN_COUNT > 0 )); then
    BORDER_COLOR="$YELLOW"
fi

echo -e "  ${BORDER_COLOR}┌─── TEST RESULTS ─────────────────────┐${RESET}"
echo -e "  ${BORDER_COLOR}│${RESET}                                       ${BORDER_COLOR}│${RESET}"
printf "  ${BORDER_COLOR}│${RESET}  Total:    %-26s ${BORDER_COLOR}│${RESET}\n" "$TOTAL_TESTS tests"
printf "  ${BORDER_COLOR}│${RESET}  Passed:   ${GREEN}%-26s${RESET} ${BORDER_COLOR}│${RESET}\n" "$PASS_COUNT"
printf "  ${BORDER_COLOR}│${RESET}  Warnings: ${YELLOW}%-26s${RESET} ${BORDER_COLOR}│${RESET}\n" "$WARN_COUNT"
printf "  ${BORDER_COLOR}│${RESET}  Failed:   ${RED}%-26s${RESET} ${BORDER_COLOR}│${RESET}\n" "$FAIL_COUNT"
echo -e "  ${BORDER_COLOR}│${RESET}                                       ${BORDER_COLOR}│${RESET}"

# List failures
if (( FAIL_COUNT > 0 )); then
    echo -e "  ${BORDER_COLOR}│${RESET}  ${RED}FAILED:${RESET}                                ${BORDER_COLOR}│${RESET}"
    for i in "${!RESULTS[@]}"; do
        if [[ "${RESULTS[$i]}" == "FAIL" ]]; then
            printf "  ${BORDER_COLOR}│${RESET}    ${RED}%-33s${RESET} ${BORDER_COLOR}│${RESET}\n" "${RESULT_MSGS[$i]}"
        fi
    done
    echo -e "  ${BORDER_COLOR}│${RESET}                                       ${BORDER_COLOR}│${RESET}"
fi

# List warnings
if (( WARN_COUNT > 0 )); then
    echo -e "  ${BORDER_COLOR}│${RESET}  ${YELLOW}WARNINGS:${RESET}                              ${BORDER_COLOR}│${RESET}"
    for i in "${!RESULTS[@]}"; do
        if [[ "${RESULTS[$i]}" == "WARN" ]]; then
            printf "  ${BORDER_COLOR}│${RESET}    ${YELLOW}%-33s${RESET} ${BORDER_COLOR}│${RESET}\n" "${RESULT_MSGS[$i]}"
        fi
    done
    echo -e "  ${BORDER_COLOR}│${RESET}                                       ${BORDER_COLOR}│${RESET}"
fi

# shellcheck disable=SC2088
REPORT_SHORT="~/security/$(basename "$TEST_REPORT")"
printf "  ${BORDER_COLOR}│${RESET}  Report: %-28s ${BORDER_COLOR}│${RESET}\n" "$REPORT_SHORT"
echo -e "  ${BORDER_COLOR}│${RESET}                                       ${BORDER_COLOR}│${RESET}"
echo -e "  ${BORDER_COLOR}└───────────────────────────────────────┘${RESET}"
echo ""
