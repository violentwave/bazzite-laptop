#!/bin/bash
# ClamAV scan script using clamd daemon for fast parallel scanning
# Deploy to: /usr/local/bin/clamav-scan.sh (chmod +x)
# Usage: clamav-scan.sh {quick|deep}
# Quick: scans /home/lch /tmp
# Deep:  scans /home/lch /tmp /var
# Pattern: start clamd → scan with clamdscan → stop clamd (reclaim ~1.1GB RAM)
set -uo pipefail

# --- Configuration ---
SCAN_TYPE="${1:-quick}"
QUARANTINE_DIR="/home/lch/security/quarantine"
LOG_DIR="/var/log/clamav-scans"
LOG_FILE="${LOG_DIR}/scan-$(date +%Y%m%d-%H%M%S).log"
STATUS_FILE="/home/lch/security/.status"
STATUS_TMP="/home/lch/security/.status.tmp"
LCH_UID="$(id -u lch)"
INTERACTIVE=false
[ -t 1 ] && INTERACTIVE=true

# --- ANSI Colors ---
CYAN='\e[0;36m'
BCYAN='\e[1;36m'
GREEN='\e[0;32m'
RED='\e[0;31m'
YELLOW='\e[0;33m'
BWHITE='\e[1;37m'
DIM='\e[2m'
RESET='\e[0m'

# --- Validate argument ---
if [[ "$SCAN_TYPE" != "quick" && "$SCAN_TYPE" != "deep" && "$SCAN_TYPE" != "test" ]]; then
    echo "Usage: $0 {quick|deep|test}" >&2
    exit 2
fi

# --- Scan targets ---
if [[ "$SCAN_TYPE" == "quick" ]]; then
    SCAN_DIRS=(/home/lch /tmp)
elif [[ "$SCAN_TYPE" == "test" ]]; then
    SCAN_DIRS=(/tmp)
else
    SCAN_DIRS=(/home/lch /tmp /var)
fi

# --- Create directories ---
mkdir -p "$QUARANTINE_DIR"
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# --- Helper: write status file (atomic) ---
write_status() {
    local state="$1"
    local message="${2:-}"
    local current_dir="${3:-}"
    local dirs_completed="${4:-0}"
    local dirs_total="${5:-${#SCAN_DIRS[@]}}"
    local result="${6:-}"
    local threat_count="${7:-0}"
    local files_scanned="${8:-0}"
    local duration="${9:-}"
    local last_scan_time="${10:-}"

    cat > "$STATUS_TMP" << STATUSEOF
{
  "state": "${state}",
  "scan_type": "${SCAN_TYPE}",
  "message": "${message}",
  "current_dir": "${current_dir}",
  "dirs_completed": ${dirs_completed},
  "dirs_total": ${dirs_total},
  "result": "${result}",
  "threat_count": ${threat_count},
  "files_scanned": ${files_scanned},
  "duration": "${duration}",
  "last_scan_time": "${last_scan_time}",
  "timestamp": "$(date -Iseconds)"
}
STATUSEOF
    mv -f "$STATUS_TMP" "$STATUS_FILE"
}

# --- Helper: terminal output (only when interactive) ---
print_banner() {
    $INTERACTIVE || return 0
    local scan_label="Quick Scan"
    [[ "$SCAN_TYPE" == "deep" ]] && scan_label="Deep Scan"
    [[ "$SCAN_TYPE" == "test" ]] && scan_label="Test Scan"
    local date_str
    date_str="$(date '+%b %d, %Y %I:%M %p')"
    echo ""
    echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
    echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE SECURITY SCANNER${RESET}       ${BCYAN}│${RESET}"
    echo -e "  ${BCYAN}│${RESET}  ${DIM}${scan_label} · ${date_str}${RESET} ${BCYAN}│${RESET}"
    echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"
    echo ""
}

print_phase() {
    local label="$1"
    local status="$2"  # running, starting, done, error
    $INTERACTIVE || return 0
    local dot color status_text
    case "$status" in
        running)
            dot="${YELLOW}●${RESET}"
            status_text="${YELLOW}[SCANNING]${RESET}"
            [[ "$label" == *"signatures"* ]] && status_text="${YELLOW}[UPDATING]${RESET}"
            ;;
        starting)
            dot="${YELLOW}●${RESET}"
            status_text="${YELLOW}[STARTING]${RESET}"
            ;;
        done)
            dot="${GREEN}●${RESET}"
            status_text="${GREEN}[DONE ✓]${RESET}"
            ;;
        ready)
            dot="${GREEN}●${RESET}"
            status_text="${GREEN}[READY ✓]${RESET}"
            ;;
        error)
            dot="${RED}●${RESET}"
            status_text="${RED}[ERROR ✗]${RESET}"
            ;;
    esac
    # Print with padding to overwrite previous line
    printf "  [${dot}] %-40s ${status_text}\n" "$label"
}

print_results() {
    local result_status="$1"
    local files_scanned="$2"
    local threat_count="$3"
    local duration="$4"
    $INTERACTIVE || return 0
    local border_color status_icon status_text
    if [[ "$result_status" == "clean" ]]; then
        border_color="$GREEN"
        status_icon="✓"
        status_text="CLEAN"
    elif [[ "$result_status" == "threats" ]]; then
        border_color="$RED"
        status_icon="✗"
        status_text="THREATS FOUND"
    else
        border_color="$RED"
        status_icon="!"
        status_text="ERROR"
    fi
    echo ""
    echo -e "  ${border_color}┌─── SCAN RESULTS ─────────────────────┐${RESET}"
    echo -e "  ${border_color}│${RESET}  Status:    ${status_icon} ${status_text}$(printf '%*s' $((21 - ${#status_text})) '')${border_color}│${RESET}"
    echo -e "  ${border_color}│${RESET}  Scanned:   $(printf '%-25s' "${files_scanned} files")${border_color}│${RESET}"
    echo -e "  ${border_color}│${RESET}  Threats:   $(printf '%-25s' "${threat_count}")${border_color}│${RESET}"
    echo -e "  ${border_color}│${RESET}  Duration:  $(printf '%-25s' "${duration}")${border_color}│${RESET}"
    echo -e "  ${border_color}│${RESET}  Quarantine: $(printf '%-24s' "~/security/quarantine")${border_color}│${RESET}"
    echo -e "  ${border_color}└───────────────────────────────────────┘${RESET}"
    echo ""
}

# --- Helper: desktop notification ---
notify() {
    local urgency="$1"
    local summary="$2"
    local body="$3"
    local icon="security-high"
    [[ "$urgency" == "critical" ]] && icon="dialog-warning"
    sudo -u lch DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${LCH_UID}/bus" \
        notify-send --app-name="Bazzite Security" --icon="$icon" --urgency="$urgency" "$summary" "$body"
}

# --- Helper: send email alert ---
send_alert() {
    local status="$1"
    local threat_count="$2"
    local files_scanned="$3"
    local duration="$4"
    if command -v /usr/local/bin/clamav-alert.sh &>/dev/null; then
        /usr/local/bin/clamav-alert.sh "$SCAN_TYPE" "$status" "$threat_count" "$files_scanned" "$duration" "$LOG_FILE"
    fi
}

# --- Helper: parse clamdscan summary ---
parse_scan_output() {
    local output="$1"
    # Count FOUND lines (each is a detected threat); --infected means no OK lines
    PARSED_THREATS=$(echo "$output" | grep -c "FOUND" || true)
    PARSED_THREATS="${PARSED_THREATS// /}"
    PARSED_THREATS="${PARSED_THREATS:-0}"
}

# --- Helper: format seconds to human readable ---
format_duration() {
    local seconds="$1"
    if (( seconds >= 3600 )); then
        printf "%dh %dm %ds" $((seconds / 3600)) $(((seconds % 3600) / 60)) $((seconds % 60))
    elif (( seconds >= 60 )); then
        printf "%dm %ds" $((seconds / 60)) $((seconds % 60))
    else
        printf "%ds" "$seconds"
    fi
}

# --- Helper: stop clamd (best effort) ---
stop_clamd() {
    systemctl stop clamd@scan 2>/dev/null || true
    print_phase "Stopping scan daemon..." "done"
    $INTERACTIVE && printf "\e[1A\e[2K"
    print_phase "Stopping scan daemon..." "done"
}

# ===========================
# MAIN
# ===========================

print_banner

# --- Phase 1: Update virus signatures ---
# Run freshclam BEFORE starting clamd so it loads the latest signatures
# Check if freshclam daemon is already running
if systemctl is-active --quiet clamav-freshclam.service 2>/dev/null || \
   pgrep -x freshclam &>/dev/null || \
   [[ -f /run/clamav/freshclam.pid ]] || \
   [[ -f /var/run/clamav/freshclam.pid ]] || \
   [[ -f /run/freshclam.pid ]]; then
    # Freshclam daemon is active — signatures are kept current automatically
    if $INTERACTIVE; then
        print_phase "Virus signatures up to date (daemon active)" "done"
    fi
    write_status "updating" "Signatures managed by freshclam daemon"
else
    # No daemon running, try manual update
    if $INTERACTIVE; then
        print_phase "Updating virus signatures..." "running"
    fi
    write_status "updating" "Updating virus signatures..."
    if freshclam --quiet 2>/dev/null; then
        if $INTERACTIVE; then
            print_phase "Updating virus signatures..." "done"
        fi
    else
        if $INTERACTIVE; then
            print_phase "Updating virus signatures..." "error"
            echo -e "    ${DIM}Warning: freshclam update failed, using existing signatures${RESET}"
        fi
    fi
fi

# --- Test mode: create EICAR test file ---
if [[ "$SCAN_TYPE" == "test" ]]; then
    EICAR_DIR="/tmp/clamav-test-$$"
    mkdir -p "$EICAR_DIR"
    echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > "$EICAR_DIR/eicar-test.txt"
    if $INTERACTIVE; then
        echo -e "    ${DIM}Created EICAR test file at $EICAR_DIR/eicar-test.txt${RESET}"
    fi
    SCAN_DIRS=("$EICAR_DIR")
fi

# --- Phase 2: Start clamd ---
write_status "scanning" "Starting scan daemon"
print_phase "Starting scan daemon..." "starting"

systemctl start clamd@scan 2>/dev/null

# Wait for clamd to be ready (up to 120 seconds, ping every 2 seconds)
if clamdscan --ping 60:2 2>/dev/null; then
    $INTERACTIVE && printf "\e[1A\e[2K"
    print_phase "Starting scan daemon..." "ready"
else
    $INTERACTIVE && printf "\e[1A\e[2K"
    print_phase "Starting scan daemon..." "error"
    $INTERACTIVE && echo -e "    ${DIM}Error: clamd failed to start within 120 seconds${RESET}"
    write_status "complete" "Scan daemon startup failed" "" "0" "${#SCAN_DIRS[@]}" \
        "error" "0" "0" "" "$(date -Iseconds)"
    notify "critical" "Scan Error" "clamd daemon failed to start. Check: systemctl status clamd@scan"
    systemctl stop clamd@scan 2>/dev/null || true
    exit 2
fi

# --- Phase 3: Scanning with clamdscan ---
SCAN_START=$(date +%s)
SCAN_OUTPUT=""
dirs_completed=0

for dir in "${SCAN_DIRS[@]}"; do
    dirs_completed=$((dirs_completed + 1))
    write_status "scanning" "Scanning ${dir}" "$dir" "$((dirs_completed - 1))" "${#SCAN_DIRS[@]}"
    print_phase "Scanning ${dir}... (multiscan)" "running"

    DIR_OUTPUT=$(clamdscan \
        --fdpass \
        --multiscan \
        --infected \
        --move="$QUARANTINE_DIR" \
        --log="$LOG_FILE" \
        "$dir" 2>&1 | grep -v "LibClamAV Warning: cli_realpath") || true

    SCAN_OUTPUT+="$DIR_OUTPUT"$'\n'

    $INTERACTIVE && printf "\e[1A\e[2K"
    print_phase "Scanning ${dir}..." "done"

    write_status "scanning" "Finished ${dir}" "$dir" "$dirs_completed" "${#SCAN_DIRS[@]}"
done

SCAN_END=$(date +%s)
SCAN_SECONDS=$((SCAN_END - SCAN_START))
DURATION=$(format_duration $SCAN_SECONDS)
LAST_SCAN_TIME=$(date -Iseconds)

# --- Count scanned files (clamdscan --infected doesn't report this) ---
PARSED_FILES=$(timeout 30 find "${SCAN_DIRS[@]}" -type f 2>/dev/null | wc -l)
PARSED_FILES="${PARSED_FILES:-0}"

# --- Phase 4: Stop clamd (reclaim ~1.1GB RAM) ---
print_phase "Stopping scan daemon..." "running"
systemctl stop clamd@scan 2>/dev/null || true
chmod 644 /var/log/clamav-scans/clamd.log 2>/dev/null
$INTERACTIVE && printf "\e[1A\e[2K"
print_phase "Stopping scan daemon..." "done"

# --- Parse results ---
parse_scan_output "$SCAN_OUTPUT"

# Write full output to log (clamdscan --log appends per-dir, also capture combined)
echo "$SCAN_OUTPUT" >> "$LOG_FILE"

# Determine exit code from threat count
if echo "$SCAN_OUTPUT" | grep -q "ERROR"; then
    EXIT_CODE=2
    RESULT_STATUS="error"
elif [[ "$PARSED_THREATS" -gt 0 ]]; then
    EXIT_CODE=1
    RESULT_STATUS="threats"
else
    EXIT_CODE=0
    RESULT_STATUS="clean"
fi
chmod 644 "$LOG_FILE" 2>/dev/null

# --- Lock down quarantined files ---
if [[ -d "$QUARANTINE_DIR" ]]; then
    # Remove all permissions from quarantined files (only root can access)
    find "$QUARANTINE_DIR" -type f -exec chmod 000 {} \; 2>/dev/null
    # Make quarantined files immutable (can't be modified, deleted, or executed)
    find "$QUARANTINE_DIR" -type f -exec chattr +i {} \; 2>/dev/null
    # Set directory permissions: root can read/write/enter, lch can list
    chmod 750 "$QUARANTINE_DIR" 2>/dev/null
    chown root:lch "$QUARANTINE_DIR" 2>/dev/null
fi

# --- Log SHA256 hashes of quarantined files for threat intelligence ---
HASH_LOG="/home/lch/security/quarantine-hashes.log"
if [[ "$PARSED_THREATS" -gt 0 ]] && [[ -d "$QUARANTINE_DIR" ]]; then
    echo "--- $(date -Iseconds) --- $SCAN_TYPE scan ---" >> "$HASH_LOG"
    find "$QUARANTINE_DIR" -type f -newer "$LOG_FILE" 2>/dev/null | while read -r qfile; do
        chattr -i "$qfile" 2>/dev/null
        HASH=$(sha256sum "$qfile" 2>/dev/null | awk '{print $1}')
        chattr +i "$qfile" 2>/dev/null
        FNAME=$(basename "$qfile")
        echo "$HASH  $FNAME  https://www.virustotal.com/gui/file/$HASH" >> "$HASH_LOG"
    done
    chmod 644 "$HASH_LOG" 2>/dev/null
fi

# --- Final status file ---
write_status "complete" "Scan complete" "" "${#SCAN_DIRS[@]}" "${#SCAN_DIRS[@]}" \
    "$RESULT_STATUS" "$PARSED_THREATS" "$PARSED_FILES" "$DURATION" "$LAST_SCAN_TIME"

# --- Terminal results ---
print_results "$RESULT_STATUS" "$PARSED_FILES" "$PARSED_THREATS" "$DURATION"

# --- Desktop notifications ---
case $EXIT_CODE in
    0)
        notify "normal" "Scan Complete — Clean" "${SCAN_TYPE^} scan finished. ${PARSED_FILES} files scanned, no threats found."
        ;;
    1)
        notify "critical" "THREATS FOUND" "${PARSED_THREATS} threat(s) found during ${SCAN_TYPE} scan! Files quarantined to ~/security/quarantine"
        ;;
    2)
        notify "critical" "Scan Error" "Error occurred during ${SCAN_TYPE} scan. Check logs: ${LOG_FILE}"
        ;;
esac

# --- Email alerts ---
# Always send email after scan completion
send_alert "$RESULT_STATUS" "$PARSED_THREATS" "$PARSED_FILES" "$DURATION"

# --- Test mode: clean up EICAR test directory ---
if [[ "$SCAN_TYPE" == "test" ]] && [[ -d "${EICAR_DIR:-}" ]]; then
    rm -rf "$EICAR_DIR" 2>/dev/null
fi

# --- Test mode: clean up quarantined EICAR file and reset status ---
if [[ "$SCAN_TYPE" == "test" ]]; then
    EICAR_Q="$QUARANTINE_DIR/eicar-test.txt"
    if [[ -f "$EICAR_Q" ]]; then
        chattr -i "$EICAR_Q" 2>/dev/null
        chmod 644 "$EICAR_Q" 2>/dev/null
        rm -f "$EICAR_Q" 2>/dev/null
    fi

    # Reset status to idle/clean so tray goes back to green
    write_status "idle" "Test complete — system clean" "" "0" "0" \
        "clean" "0" "0" "" "" "clean"

    if $INTERACTIVE; then
        echo ""
        echo -e "    ${DIM}Test cleanup: EICAR file removed from quarantine${RESET}"
        echo -e "    ${DIM}Tray icon will return to green${RESET}"
    fi
fi

exit $EXIT_CODE
