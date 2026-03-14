#!/bin/bash
# ClamAV scan script — accepts "quick" or "deep" as argument
# Deploy to: /usr/local/bin/clamav-scan.sh (chmod +x)
# Quick: scans /home/lch and /tmp
# Deep: scans /home/lch, /tmp, /var, and Steam library
set -uo pipefail

SCAN_TYPE="${1:-quick}"
QUARANTINE_DIR="/home/lch/quarantined"
LOG_DIR="/var/log/clamav-scans"
LOG_FILE="${LOG_DIR}/scan-$(date +%Y%m%d-%H%M%S).log"
LCH_UID="$(id -u lch)"

notify() {
    local urgency="$1"
    local summary="$2"
    local body="$3"
    sudo -u lch DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${LCH_UID}/bus" \
        notify-send --urgency="$urgency" "$summary" "$body"
}

send_alert() {
    local subject="$1"
    local body="$2"
    if command -v /usr/local/bin/clamav-alert.sh &>/dev/null; then
        echo "$body" | /usr/local/bin/clamav-alert.sh "$subject"
    fi
}

# Validate argument
if [[ "$SCAN_TYPE" != "quick" && "$SCAN_TYPE" != "deep" ]]; then
    echo "Usage: $0 {quick|deep}" >&2
    exit 2
fi

# Set scan targets
if [[ "$SCAN_TYPE" == "quick" ]]; then
    SCAN_DIRS=(/home/lch /tmp)
else
    SCAN_DIRS=(/home/lch /tmp /var /run/media/lch/SteamLibrary)
fi

# Create directories if missing
mkdir -p "$QUARANTINE_DIR"
mkdir -p "$LOG_DIR"

# Update signatures (suppress output unless error)
if ! freshclam --quiet 2>"${LOG_DIR}/freshclam-update-error.log"; then
    echo "Warning: freshclam update failed, continuing with existing signatures" >&2
fi

# Run clamscan — do NOT use set -e here because exit code 1 means infections found
clamscan \
    --infected \
    --recursive \
    --move="$QUARANTINE_DIR" \
    --log="$LOG_FILE" \
    --exclude-dir="^/home/lch/\.cache" \
    --exclude-dir="^/home/lch/\.local/share/Steam/steamapps/shadercache" \
    --exclude-dir="^/home/lch/quarantined" \
    "${SCAN_DIRS[@]}"

EXIT_CODE=$?

case $EXIT_CODE in
    0)
        notify "normal" "ClamAV" "Scan clean (${SCAN_TYPE})"
        ;;
    1)
        notify "critical" "ClamAV" "INFECTIONS FOUND during ${SCAN_TYPE} scan! Check quarantine."
        send_alert "ClamAV ALERT: Infections found (${SCAN_TYPE} scan)" "$(cat "$LOG_FILE")"
        ;;
    2)
        notify "critical" "ClamAV" "Scan error during ${SCAN_TYPE} scan!"
        send_alert "ClamAV ERROR: Scan failed (${SCAN_TYPE} scan)" "$(cat "$LOG_FILE")"
        ;;
esac

exit $EXIT_CODE
