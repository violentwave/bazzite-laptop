#!/bin/bash
# start-security-tray.sh — Start or restart the security tray monitor
# Deploy to: /usr/local/bin/start-security-tray.sh

TRAY_SCRIPT="/home/lch/security/bazzite-security-tray.py"
LOCK_FILE="/home/lch/security/.tray.lock"
LOG_FILE="/home/lch/security/.tray-start.log"

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }

log "--- start-security-tray.sh invoked ---"

# Kill any existing instance (use [.]py regex trick to avoid matching grep itself)
if pgrep -f "bazzite-security-tray[.]py" &>/dev/null; then
    log "Killing existing tray instance"
    pkill -f "bazzite-security-tray[.]py" 2>/dev/null
    # Wait up to 5 seconds for the process to exit
    for _ in $(seq 1 10); do
        pgrep -f "bazzite-security-tray[.]py" &>/dev/null || break
        sleep 0.5
    done
    # Force kill if still running
    if pgrep -f "bazzite-security-tray[.]py" &>/dev/null; then
        log "Force killing stubborn tray instance"
        pkill -9 -f "bazzite-security-tray[.]py" 2>/dev/null
        sleep 1
    fi
fi

# Remove stale lock file (flock is FD-based, so this just cleans up the file)
rm -f "$LOCK_FILE" 2>/dev/null

# Verify the script exists
if [[ ! -f "$TRAY_SCRIPT" ]]; then
    log "ERROR: $TRAY_SCRIPT not found"
    notify-send --app-name="Bazzite Security" --urgency=critical \
        "Tray Start Failed" "Script not found: $TRAY_SCRIPT" 2>/dev/null
    exit 1
fi

# Start fresh instance (setsid creates a new session so KDE won't kill it)
log "Starting tray: setsid python3 $TRAY_SCRIPT"
setsid python3 "$TRAY_SCRIPT" &>/dev/null &

# Brief wait to check if it actually started
sleep 1
if pgrep -f "bazzite-security-tray[.]py" &>/dev/null; then
    log "Tray started successfully"
else
    log "ERROR: Tray process died immediately"
    notify-send --app-name="Bazzite Security" --urgency=critical \
        "Tray Start Failed" "Process exited immediately. Check: python3 $TRAY_SCRIPT" 2>/dev/null
    exit 1
fi

exit 0
