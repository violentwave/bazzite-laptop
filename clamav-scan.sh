#!/bin/bash
# ClamAV scan script with terminal UI, status file, desktop notifications, and email alerts
# Deploy to: /usr/local/bin/clamav-scan.sh (chmod +x)
# Usage: clamav-scan.sh {quick|deep}
# Quick: scans /home/lch /tmp
# Deep:  scans /home/lch /tmp /var
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
if [[ "$SCAN_TYPE" != "quick" && "$SCAN_TYPE" != "deep" ]]; then
    echo "Usage: $0 {quick|deep}" >&2
    exit 2
fi

# --- Scan targets ---
if [[ "$SCAN_TYPE" == "quick" ]]; then
    SCAN_DIRS=(/home/lch /tmp)
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
    local status="$2"  # running, done, error
    $INTERACTIVE || return 0
    local dot color status_text
    case "$status" in
        running)
            dot="${YELLOW}●${RESET}"
            status_text="${YELLOW}[SCANNING]${RESET}"
            [[ "$label" == *"signatures"* ]] && status_text="${YELLOW}[UPDATING]${RESET}"
            ;;
        done)
            dot="${GREEN}●${RESET}"
            status_text="${GREEN}[DONE ✓]${RESET}"
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

# --- Helper: parse clamscan summary ---
parse_scan_output() {
    local output="$1"
    PARSED_FILES=$(echo "$output" | grep -oP 'Scanned files:\s*\K[0-9]+' || echo "0")
    PARSED_THREATS=$(echo "$output" | grep -oP 'Infected files:\s*\K[0-9]+' || echo "0")
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

# ===========================
# MAIN
# ===========================

print_banner

# --- Phase 1: Update virus signatures ---
write_status "updating" "Updating virus signatures"
print_phase "Updating virus signatures..." "running"

if [[ -f /run/clamav/freshclam.pid ]] || pgrep -x freshclam &>/dev/null; then
    # freshclam daemon is already running and keeping signatures current
    $INTERACTIVE && printf "\e[1A\e[2K"
    print_phase "Virus signatures up to date" "done"
    write_status "updating" "Signatures managed by freshclam daemon"
else
    # Run freshclam manually
    FRESHCLAM_OK=true
    if ! freshclam --quiet 2>"${LOG_DIR}/freshclam-update-error.log"; then
        FRESHCLAM_OK=false
    fi

    if $FRESHCLAM_OK; then
        $INTERACTIVE && printf "\e[1A\e[2K"
        print_phase "Updating virus signatures..." "done"
    else
        $INTERACTIVE && printf "\e[1A\e[2K"
        print_phase "Updating virus signatures..." "error"
        $INTERACTIVE && echo -e "    ${DIM}Warning: freshclam update failed, using existing signatures${RESET}"
    fi
fi

# --- Phase 2: Scanning ---
SCAN_START=$(date +%s)
SCAN_OUTPUT=""
dirs_completed=0

for dir in "${SCAN_DIRS[@]}"; do
    dirs_completed=$((dirs_completed + 1))
    write_status "scanning" "Scanning ${dir}" "$dir" "$((dirs_completed - 1))" "${#SCAN_DIRS[@]}"
    print_phase "Scanning ${dir}..." "running"

    DIR_OUTPUT=$(clamscan \
        --infected \
        --recursive \
        --move="$QUARANTINE_DIR" \
        --exclude-dir="^/home/lch/\.cache" \
        --exclude-dir="^/home/lch/\.local/share/Steam/steamapps/shadercache" \
        --exclude-dir="^/home/lch/security/quarantine" \
        "$dir" 2>&1) || true

    SCAN_OUTPUT+="$DIR_OUTPUT"$'\n'

    $INTERACTIVE && printf "\e[1A\e[2K"
    print_phase "Scanning ${dir}..." "done"

    write_status "scanning" "Finished ${dir}" "$dir" "$dirs_completed" "${#SCAN_DIRS[@]}"
done

SCAN_END=$(date +%s)
SCAN_SECONDS=$((SCAN_END - SCAN_START))
DURATION=$(format_duration $SCAN_SECONDS)
LAST_SCAN_TIME=$(date -Iseconds)

# --- Parse results ---
parse_scan_output "$SCAN_OUTPUT"

# Write clean log
echo "$SCAN_OUTPUT" > "$LOG_FILE"

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
# Deep scan: always send (weekly security report)
# Quick scan: only on threats or errors
if [[ "$SCAN_TYPE" == "deep" ]]; then
    send_alert "$RESULT_STATUS" "$PARSED_THREATS" "$PARSED_FILES" "$DURATION"
elif [[ $EXIT_CODE -eq 1 || $EXIT_CODE -eq 2 ]]; then
    send_alert "$RESULT_STATUS" "$PARSED_THREATS" "$PARSED_FILES" "$DURATION"
fi

exit $EXIT_CODE
