#!/bin/bash
# ClamAV HTML email alert script using msmtp
# Deploy to: /usr/local/bin/clamav-alert.sh (chmod +x)
# Usage: clamav-alert.sh <scan_type> <status> <threat_count> <files_scanned> <duration> <log_file> [health_summary]
#   scan_type:      quick | deep | healthcheck
#   status:         clean | threats | error
#   threat_count:   number of threats found
#   files_scanned:  total files scanned
#   duration:       human-readable duration string
#   log_file:       path to the scan log file
#   health_summary: optional health snapshot text (from --append mode)
set -euo pipefail

# --- Arguments ---
SCAN_TYPE="${1:?Usage: $0 <scan_type> <status> <threat_count> <files_scanned> <duration> <log_file> [health_summary]}"
STATUS="${2:?Missing status (clean|threats|error)}"
THREAT_COUNT="${3:?Missing threat_count}"
FILES_SCANNED="${4:?Missing files_scanned}"
DURATION="${5:?Missing duration}"
LOG_FILE="${6:?Missing log_file}"
HEALTH_SUMMARY="${7:-}"

# Validate numeric arguments to prevent email header injection
if ! [[ "$THREAT_COUNT" =~ ^[0-9]+$ ]]; then
    echo "Error: THREAT_COUNT must be numeric, got: '$THREAT_COUNT'" >&2
    exit 1
fi
if ! [[ "$FILES_SCANNED" =~ ^[0-9]+$ ]]; then
    echo "Error: FILES_SCANNED must be numeric, got: '$FILES_SCANNED'" >&2
    exit 1
fi

# HTML-escape helper — prevents broken email rendering from special characters
html_escape() {
    local text="$1"
    text="${text//&/&amp;}"
    text="${text//</&lt;}"
    text="${text//>/&gt;}"
    text="${text//\"/&quot;}"
    printf '%s' "$text"
}

# Escape health summary
if [[ -n "$HEALTH_SUMMARY" ]]; then
    HEALTH_SUMMARY=$(html_escape "$HEALTH_SUMMARY")
fi

HOSTNAME="$(hostname)"
DATE_STR="$(date '+%B %d, %Y at %I:%M %p')"

# Capitalize scan type for display (handles "healthcheck" → "Healthcheck")
SCAN_TYPE_DISPLAY="${SCAN_TYPE^}"

# HTML-escape all variables interpolated into email body (H5 security fix)
H_SCAN_TYPE=$(html_escape "$SCAN_TYPE")
H_SCAN_TYPE_DISPLAY=$(html_escape "$SCAN_TYPE_DISPLAY")
H_FILES_SCANNED=$(html_escape "$FILES_SCANNED")
H_DURATION=$(html_escape "$DURATION")
H_DATE_STR=$(html_escape "$DATE_STR")
H_LOG_FILE=$(html_escape "$LOG_FILE")
H_THREAT_COUNT=$(html_escape "$THREAT_COUNT")

# --- Resolve recipient ---
TO_EMAIL=""
if [[ -f /home/lch/.msmtprc ]]; then
    TO_EMAIL=$(awk '/^\s*from\s/ {print $2; exit}' /home/lch/.msmtprc 2>/dev/null)
    if [[ -z "$TO_EMAIL" ]]; then
        TO_EMAIL=$(awk '/^\s*user\s/ {print $2; exit}' /home/lch/.msmtprc 2>/dev/null)
    fi
fi

if [[ -z "$TO_EMAIL" ]]; then
    echo "Warning: No recipient address found in /home/lch/.msmtprc. Email alert skipped." >&2
    exit 0
fi

# --- Email rate limiting (max 6 emails per hour) ---
# Rate file in root-owned log dir (not world-writable /tmp)
EMAIL_RATE_DIR="/var/log/clamav-scans"
mkdir -p "$EMAIL_RATE_DIR"
EMAIL_RATE_FILE="${EMAIL_RATE_DIR}/.email-rate"
# Ensure restrictive permissions on rate file
[[ -f "$EMAIL_RATE_FILE" ]] || { touch "$EMAIL_RATE_FILE"; chmod 600 "$EMAIL_RATE_FILE"; }
EMAIL_MAX_PER_HOUR=6
_now=$(date +%s)
if [[ -f "$EMAIL_RATE_FILE" ]]; then
    # Read timestamps and filter to last hour only
    _recent=$(awk -v cutoff="$((_now - 3600))" '$1 > cutoff' "$EMAIL_RATE_FILE" 2>/dev/null | wc -l)
    if [[ "$_recent" -ge "$EMAIL_MAX_PER_HOUR" ]]; then
        echo "Email rate limit reached (${EMAIL_MAX_PER_HOUR}/hour). Alert skipped." >&2
        exit 0
    fi
fi
# Record this send attempt
echo "$_now" >> "$EMAIL_RATE_FILE"
# Prune entries older than 1 hour
if [[ -f "$EMAIL_RATE_FILE" ]]; then
    awk -v cutoff="$((_now - 3600))" '$1 > cutoff' "$EMAIL_RATE_FILE" > "${EMAIL_RATE_FILE}.tmp" 2>/dev/null
    mv -f "${EMAIL_RATE_FILE}.tmp" "$EMAIL_RATE_FILE" 2>/dev/null || true
fi

# --- Determine subject and banner ---
case "$STATUS" in
    clean)
        SUBJECT="Bazzite Weekly Security Report — All Clear"
        BANNER_COLOR="#22c55e"
        BANNER_TEXT="ALL CLEAR"
        BANNER_ICON="&#x2705;"
        ;;
    threats)
        SUBJECT="Bazzite Security Alert: ${THREAT_COUNT} threats found — ${SCAN_TYPE} scan"
        BANNER_COLOR="#ef4444"
        BANNER_TEXT="THREATS DETECTED"
        BANNER_ICON="&#x1F6A8;"
        ;;
    error)
        if [[ "$SCAN_TYPE" == "healthcheck" ]]; then
            SUBJECT="Bazzite Security Alert: Health check failed"
        else
            SUBJECT="Bazzite Security Alert: Scan error — ${SCAN_TYPE} scan"
        fi
        BANNER_COLOR="#f59e0b"
        BANNER_TEXT="SCAN ERROR"
        BANNER_ICON="&#x26A0;"
        ;;
    *)
        echo "Error: Invalid status '${STATUS}'" >&2
        exit 1
        ;;
esac

# --- Build threat details table rows (for threats status) ---
THREAT_TABLE_ROWS=""
if [[ "$STATUS" == "threats" && -f "$LOG_FILE" ]]; then
    while IFS= read -r line; do
        # Lines look like: /path/to/file: ThreatName FOUND
        filepath="${line%%: * FOUND}"
        filename=$(html_escape "$(basename "$filepath")")
        filepath_esc=$(html_escape "$filepath")
        threatname=$(html_escape "$(echo "$line" | sed 's/^.*: //' | sed 's/ FOUND$//')")
        THREAT_TABLE_ROWS+="<tr style=\"border-bottom:1px solid #334155;background:#1e293b\"><td style=\"padding:10px 12px;font-family:'JetBrains Mono','Courier New',monospace;font-size:12px;color:#e2e8f0\">${filename}</td><td style=\"padding:10px 12px;font-size:12px;color:#64748b;word-break:break-all\">${filepath_esc}</td><td style=\"padding:10px 12px;font-size:12px;color:#ef4444;font-weight:700\">${threatname}</td><td style=\"padding:10px 12px;font-size:12px;color:#22c55e;font-weight:600\">Quarantined</td></tr>"
    done < <(grep "FOUND$" "$LOG_FILE" 2>/dev/null || true)

    # --- Extract hashes for AI threat intel enrichment ---
    HASH_LOG="/home/lch/security/quarantine-hashes.log"
    if [[ -f "$HASH_LOG" ]]; then
        THREAT_HASHES=$(tac "$HASH_LOG" 2>/dev/null | sed '/^---/q' | grep -v '^---' | awk 'NF{print $1}' | tac)
    fi
fi

# --- AI Threat Intelligence enrichment (optional, graceful degradation) ---
THREAT_INTEL_HTML=""
if [[ -n "${THREAT_HASHES:-}" ]]; then
    if command -v /usr/local/bin/threat-lookup.sh &>/dev/null; then
        THREAT_INTEL_HTML=$(echo "$THREAT_HASHES" | timeout 30 runuser -u lch -- /usr/local/bin/threat-lookup.sh --batch --format html 2>/dev/null) || THREAT_INTEL_HTML=""
    fi
fi

# --- Build body content based on status ---
BODY_CONTENT=""

case "$STATUS" in
    clean)
        BODY_CONTENT="
        <p style=\"font-size:15px;color:#e2e8f0;line-height:1.6;margin:0 0 20px 0\">Your scheduled <strong style=\"color:#00d4ff\">${H_SCAN_TYPE}</strong> scan completed successfully with no threats detected.</p>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden\">
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;width:40%;border-bottom:1px solid #334155\">Scan Type</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_SCAN_TYPE_DISPLAY}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Files Scanned</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_FILES_SCANNED}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Threats Found</td><td style=\"padding:12px 16px;font-size:14px;color:#22c55e;font-weight:700;border-bottom:1px solid #334155\">0</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Duration</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_DURATION}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8\">Completed</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600\">${H_DATE_STR}</td></tr>
        </table>
        <!-- Visual health bar -->
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:20px\"><tr>
            <td style=\"background:#22c55e;height:4px;border-radius:4px\"></td>
        </tr></table>
        <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Your system remains protected. Virus signatures are kept up to date automatically before each scan.</p>"
        ;;

    threats)
        BODY_CONTENT="
        <p style=\"font-size:15px;color:#e2e8f0;line-height:1.6;margin:0 0 20px 0\"><strong style=\"color:#ef4444\">${H_THREAT_COUNT} threat(s)</strong> were detected during the <strong style=\"color:#00d4ff\">${H_SCAN_TYPE}</strong> scan. Infected files have been moved to quarantine.</p>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden\">
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;width:40%;border-bottom:1px solid #334155\">Scan Type</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_SCAN_TYPE_DISPLAY}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Files Scanned</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_FILES_SCANNED}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Threats Found</td><td style=\"padding:12px 16px;font-size:14px;color:#ef4444;font-weight:700;border-bottom:1px solid #334155\">${H_THREAT_COUNT}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Duration</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_DURATION}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8\">Quarantine</td><td style=\"padding:12px 16px;font-size:14px;color:#f59e0b;font-weight:600\">~/security/quarantine</td></tr>
        </table>
        <!-- Threat severity bar -->
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:20px\"><tr>
            <td style=\"background:#ef4444;height:4px;border-radius:4px\"></td>
        </tr></table>
        <h3 style=\"font-size:15px;color:#ef4444;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase\">Threat Details</h3>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border:1px solid #334155;border-radius:8px;overflow:hidden\">
            <tr style=\"background:#0f172a\"><th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">File</th><th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Original Path</th><th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Threat Detected</th><th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Action</th></tr>
            ${THREAT_TABLE_ROWS}
        </table>
        ${THREAT_INTEL_HTML}
        <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Review the quarantined files and delete them if they are confirmed threats. Log: <code style=\"background:#0f172a;color:#94a3b8;padding:3px 8px;border-radius:4px;font-size:12px;border:1px solid #334155\">${H_LOG_FILE}</code></p>"
        ;;

    error)
        ERROR_DETAILS=""
        if [[ -f "$LOG_FILE" ]]; then
            ERROR_DETAILS=$(tail -20 "$LOG_FILE" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g' || echo "Could not read log file")
        fi
        BODY_CONTENT="
        <p style=\"font-size:15px;color:#e2e8f0;line-height:1.6;margin:0 0 20px 0\">An error occurred during the <strong style=\"color:#00d4ff\">${H_SCAN_TYPE}</strong> scan. The scan may not have completed fully.</p>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden\">
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;width:40%;border-bottom:1px solid #334155\">Scan Type</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_SCAN_TYPE_DISPLAY}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Files Scanned</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_FILES_SCANNED}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Duration</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_DURATION}</td></tr>
            <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8\">Completed</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600\">${H_DATE_STR}</td></tr>
        </table>
        <!-- Error severity bar -->
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:20px\"><tr>
            <td style=\"background:#f59e0b;height:4px;border-radius:4px\"></td>
        </tr></table>
        <h3 style=\"font-size:15px;color:#f59e0b;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase\">Error Details</h3>
        <pre style=\"background:#0f172a;color:#e2e8f0;padding:16px;border-radius:8px;font-size:12px;overflow-x:auto;margin:0 0 16px 0;border:1px solid #334155;font-family:'JetBrains Mono','Cascadia Code','Courier New',monospace;line-height:1.5\">${ERROR_DETAILS}</pre>
        <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Check the full log at: <code style=\"background:#0f172a;color:#94a3b8;padding:3px 8px;border-radius:4px;font-size:12px;border:1px solid #334155\">${H_LOG_FILE}</code></p>"
        ;;
esac

# --- Healthcheck: override BODY_CONTENT with health-focused template ---
# Argument mapping when scan_type=healthcheck:
#   $3 (THREAT_COUNT)   = total issue count (warnings + critical)
#   $4 (FILES_SCANNED)  = health status string: OK | WARNING | CRITICAL
#   $5 (DURATION)       = snapshot duration
#   $6 (LOG_FILE)       = health log path
#   $7 (HEALTH_SUMMARY) = compact text block from --append mode (optional)
#
# Caller sets STATUS to: clean (OK), threats (WARNING/CRITICAL), error (script error)
# Delta trends are read from /var/log/system-health/health-deltas.dat if present.
if [[ "$SCAN_TYPE" == "healthcheck" ]]; then
    HEALTH_STATUS_LABEL=$(html_escape "$FILES_SCANNED")  # e.g. OK / WARNING / CRITICAL
    HEALTH_ISSUE_COUNT=$(html_escape "$THREAT_COUNT")    # total issue count

    # Determine status row colour
    case "$FILES_SCANNED" in
        OK)       HEALTH_ROW_COLOR="#22c55e" ;;
        WARNING)  HEALTH_ROW_COLOR="#f59e0b" ;;
        CRITICAL) HEALTH_ROW_COLOR="#ef4444" ;;
        *)        HEALTH_ROW_COLOR="#94a3b8" ;;
    esac

    # Parse key metrics from the health log file (best-effort, empty on failure)
    HEALTH_GPU_TEMP="" HEALTH_CPU_TEMP="" HEALTH_SDA_HEALTH="" HEALTH_SDA_TEMP=""
    HEALTH_SDA_WEAR="" HEALTH_SDA_REALLOC="" HEALTH_SDB_HEALTH="" HEALTH_SDB_SPARE=""
    HEALTH_SDB_USED="" HEALTH_SELINUX="" HEALTH_FIREWALL="" HEALTH_FIREWALL_ZONE=""
    if [[ -f "$LOG_FILE" ]]; then
        _log_text=$(cat "$LOG_FILE" 2>/dev/null || true)
        HEALTH_GPU_TEMP=$(echo "$_log_text" | grep -i "Temperature:" | grep -i "GPU\|gpu\|Temperature:.*°C" | head -1 | grep -oP '[0-9]+(?=°C)' | head -1 || true)
        # GPU temp from nvidia section
        HEALTH_GPU_TEMP=$(echo "$_log_text" | awk '/GPU: NVIDIA/{f=1} f && /Temperature:/{match($0,/([0-9]+)°C/,a); print a[1]; exit}' || true)
        HEALTH_CPU_TEMP=$(echo "$_log_text" | awk '/CPU.*Thermals/{f=1} f && /Package temp:/{match($0,/([0-9.]+)°C/,a); print a[1]; exit}' || true)
        HEALTH_SDA_HEALTH=$(echo "$_log_text" | awk '/Internal SSD/{f=1} f && /Overall health:/{sub(/.*Overall health: /,""); print; exit}' || true)
        HEALTH_SDA_TEMP=$(echo "$_log_text" | awk '/Internal SSD/{f=1} f && /Temperature:/{match($0,/([0-9]+)°C/,a); print a[1]; exit}' || true)
        HEALTH_SDA_WEAR=$(echo "$_log_text" | awk '/Internal SSD/{f=1} f && /Wear leveling:/{match($0,/([0-9]+) avg/,a); print a[1]; exit}' || true)
        HEALTH_SDA_REALLOC=$(echo "$_log_text" | awk '/Internal SSD/{f=1} f && /Reallocated:/{match($0,/([0-9]+) sectors/,a); print a[1]; exit}' || true)
        HEALTH_SDB_HEALTH=$(echo "$_log_text" | awk '/External NVMe/{f=1} f && /Overall health:/{sub(/.*Overall health: /,""); print; exit}' || true)
        HEALTH_SDB_SPARE=$(echo "$_log_text" | awk '/External NVMe/{f=1} f && /Available spare:/{match($0,/([0-9]+)%/,a); print a[1]; exit}' || true)
        HEALTH_SDB_USED=$(echo "$_log_text" | awk '/External NVMe/{f=1} f && /Percentage used:/{match($0,/([0-9]+)%/,a); print a[1]; exit}' || true)
        HEALTH_SELINUX=$(echo "$_log_text" | grep "SELinux:" | head -1 | sed 's/.*SELinux: //' | xargs || true)
        HEALTH_FIREWALL=$(echo "$_log_text" | grep "Firewall zone:" | head -1 | sed 's/.*Firewall zone: //' | xargs || true)
    fi

    # HTML-escape parsed values
    HEALTH_GPU_TEMP=$(html_escape "${HEALTH_GPU_TEMP:-?}")
    HEALTH_CPU_TEMP=$(html_escape "${HEALTH_CPU_TEMP:-?}")
    HEALTH_SDA_HEALTH=$(html_escape "${HEALTH_SDA_HEALTH:-?}")
    HEALTH_SDA_TEMP=$(html_escape "${HEALTH_SDA_TEMP:-?}")
    HEALTH_SDA_WEAR=$(html_escape "${HEALTH_SDA_WEAR:-?}")
    HEALTH_SDA_REALLOC=$(html_escape "${HEALTH_SDA_REALLOC:-?}")
    HEALTH_SDB_HEALTH=$(html_escape "${HEALTH_SDB_HEALTH:-?}")
    HEALTH_SDB_SPARE=$(html_escape "${HEALTH_SDB_SPARE:-?}")
    HEALTH_SDB_USED=$(html_escape "${HEALTH_SDB_USED:-?}")
    HEALTH_SELINUX=$(html_escape "${HEALTH_SELINUX:-?}")
    HEALTH_FIREWALL=$(html_escape "${HEALTH_FIREWALL:-?}")

    # Delta trends block (read from health-deltas.dat if present)
    DELTA_ROWS=""
    DELTA_FILE="/var/log/system-health/health-deltas.dat"
    if [[ -f "$DELTA_FILE" ]]; then
        while IFS='=' read -r dkey dval; do
            [[ -z "$dkey" || "$dkey" =~ ^# ]] && continue
            dkey_esc=$(html_escape "$dkey")
            dval_esc=$(html_escape "$dval")
            DELTA_ROWS+="<tr style=\"border-bottom:1px solid #1e293b\"><td style=\"padding:8px 12px;font-size:12px;color:#94a3b8;font-family:'JetBrains Mono','Courier New',monospace\">${dkey_esc}</td><td style=\"padding:8px 12px;font-size:12px;color:#e2e8f0;font-weight:600\">${dval_esc}</td></tr>"
        done < "$DELTA_FILE" 2>/dev/null || true
    fi

    DELTA_SECTION=""
    if [[ -n "$DELTA_ROWS" ]]; then
        DELTA_SECTION="
        <h3 style=\"font-size:15px;color:#7eb8da;margin:24px 0 12px 0;letter-spacing:1px;text-transform:uppercase\">Delta Trends</h3>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border:1px solid #334155;border-radius:8px;overflow:hidden\">
            <tr style=\"background:#0f172a\">
                <th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Key</th>
                <th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Last Value</th>
            </tr>
            ${DELTA_ROWS}
        </table>"
    fi

    BODY_CONTENT="
    <p style=\"font-size:15px;color:#e2e8f0;line-height:1.6;margin:0 0 20px 0\">Daily hardware &amp; performance health snapshot completed.</p>
    <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden\">
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;width:40%;border-bottom:1px solid #334155\">Overall Status</td><td style=\"padding:12px 16px;font-size:14px;color:${HEALTH_ROW_COLOR};font-weight:700;border-bottom:1px solid #334155\">${HEALTH_STATUS_LABEL}</td></tr>
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Issues Detected</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${HEALTH_ISSUE_COUNT}</td></tr>
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;border-bottom:1px solid #334155\">Duration</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${H_DURATION}</td></tr>
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8\">Completed</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600\">${H_DATE_STR}</td></tr>
    </table>
    <!-- Status bar -->
    <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px\"><tr>
        <td style=\"background:${HEALTH_ROW_COLOR};height:4px;border-radius:4px\"></td>
    </tr></table>

    <h3 style=\"font-size:15px;color:#7eb8da;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase\">Drive Health</h3>
    <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border:1px solid #334155;border-radius:8px;overflow:hidden\">
        <tr style=\"background:#0f172a\">
            <th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Drive</th>
            <th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Health</th>
            <th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Temp</th>
            <th style=\"padding:10px 12px;font-size:11px;color:#00d4ff;text-align:left;text-transform:uppercase;letter-spacing:1px\">Key Metrics</th>
        </tr>
        <tr style=\"border-bottom:1px solid #334155;background:#1e293b\">
            <td style=\"padding:10px 12px;font-size:13px;color:#e2e8f0\">sda (SK hynix 256G)</td>
            <td style=\"padding:10px 12px;font-size:13px;color:#22c55e;font-weight:600\">${HEALTH_SDA_HEALTH}</td>
            <td style=\"padding:10px 12px;font-size:13px;color:#e2e8f0\">${HEALTH_SDA_TEMP}°C</td>
            <td style=\"padding:10px 12px;font-size:13px;color:#94a3b8\">Wear: ${HEALTH_SDA_WEAR} | Realloc: ${HEALTH_SDA_REALLOC}</td>
        </tr>
        <tr style=\"background:#1e293b\">
            <td style=\"padding:10px 12px;font-size:13px;color:#e2e8f0\">sdb (WD SN580E 2TB)</td>
            <td style=\"padding:10px 12px;font-size:13px;color:#22c55e;font-weight:600\">${HEALTH_SDB_HEALTH}</td>
            <td style=\"padding:10px 12px;font-size:13px;color:#e2e8f0\">N/A</td>
            <td style=\"padding:10px 12px;font-size:13px;color:#94a3b8\">Spare: ${HEALTH_SDB_SPARE}% | Used: ${HEALTH_SDB_USED}%</td>
        </tr>
    </table>

    <h3 style=\"font-size:15px;color:#7eb8da;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase\">Thermals</h3>
    <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden\">
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;width:50%;border-bottom:1px solid #334155\">GPU (GTX 1060)</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${HEALTH_GPU_TEMP}°C</td></tr>
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8\">CPU Package (i7-7700HQ)</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600\">${HEALTH_CPU_TEMP}°C</td></tr>
    </table>

    <h3 style=\"font-size:15px;color:#7eb8da;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase\">Security Services</h3>
    <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden\">
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8;width:50%;border-bottom:1px solid #334155\">SELinux</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #334155\">${HEALTH_SELINUX}</td></tr>
        <tr style=\"background:#0f172a\"><td style=\"padding:12px 16px;font-size:14px;color:#94a3b8\">Firewall Zone</td><td style=\"padding:12px 16px;font-size:14px;color:#e2e8f0;font-weight:600\">${HEALTH_FIREWALL}</td></tr>
    </table>

    ${DELTA_SECTION}

    <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Full log: <code style=\"background:#0f172a;color:#94a3b8;padding:3px 8px;border-radius:4px;font-size:12px;border:1px solid #334155\">${H_LOG_FILE}</code></p>"
fi

# --- Compose and send HTML email ---
{
    cat << EMAILEOF
To: ${TO_EMAIL}
Subject: ${SUBJECT}
Content-Type: text/html; charset=UTF-8
X-Mailer: bazzite-security
MIME-Version: 1.0

<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table style="max-width:640px;margin:0 auto;background:#1e293b;border-collapse:collapse;width:100%;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.3)">
    <!-- Header with shield logo -->
    <tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);padding:32px 32px 20px 32px;text-align:center">
        <!-- Shield SVG inline -->
        <div style="margin:0 auto 16px auto;width:48px;height:48px">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48"><path d="M24 4L6 12v12c0 11.1 7.7 21.5 18 24 10.3-2.5 18-12.9 18-24V12L24 4z" fill="none" stroke="#00d4ff" stroke-width="2.5"/><path d="M24 4L6 12v12c0 11.1 7.7 21.5 18 24 10.3-2.5 18-12.9 18-24V12L24 4z" fill="#00d4ff" opacity="0.1"/><path d="M20 24l4 4 8-8" fill="none" stroke="#00d4ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <h1 style="margin:0;font-size:22px;letter-spacing:3px;color:#00d4ff;font-weight:700">BAZZITE SECURITY</h1>
        <p style="margin:6px 0 0 0;font-size:12px;color:#64748b;letter-spacing:1px">AUTOMATED THREAT MONITORING</p>
    </td></tr>
    <!-- Status Banner with gradient -->
    <tr><td style="background:${BANNER_COLOR};padding:18px 32px;text-align:center;border-top:2px solid rgba(255,255,255,0.1);border-bottom:2px solid rgba(0,0,0,0.2)">
        <span style="font-size:24px;color:#ffffff;font-weight:700;text-shadow:0 2px 4px rgba(0,0,0,0.2)">${BANNER_ICON} ${BANNER_TEXT}</span>
    </td></tr>
    <!-- Body -->
    <tr><td style="padding:32px;background:#1e293b">
        ${BODY_CONTENT}
    </td></tr>
$(if [[ -n "$HEALTH_SUMMARY" ]]; then cat <<HEALTHEOF
    <!-- Health Summary -->
    <tr><td style="padding:0 32px">
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;border-radius:8px;overflow:hidden">
            <tr><td style="background:#0f172a;padding:12px 16px;border-bottom:1px solid #334155">
                <span style="font-size:13px;font-weight:700;color:#94a3b8;letter-spacing:1px;text-transform:uppercase">System Health Snapshot</span>
            </td></tr>
            <tr><td style="background:#0f172a;padding:16px">
                <pre style="margin:0;font-family:'Cascadia Code','JetBrains Mono','Courier New',monospace;font-size:12px;color:#94a3b8;white-space:pre-wrap;line-height:1.5">${HEALTH_SUMMARY}</pre>
            </td></tr>
        </table>
    </td></tr>
HEALTHEOF
fi)
    <!-- Footer -->
    <tr><td style="padding:24px 32px;text-align:center;border-top:1px solid #334155;background:#0f172a">
        <p style="margin:0 0 4px 0;font-size:11px;color:#475569">Bazzite Security &middot; Acer Predator G3-571 &middot; $(date +%Y)</p>
        <p style="margin:0;font-size:10px;color:#334155">ClamAV + AI Threat Intelligence &middot; Automated Report</p>
    </td></tr>
</table>
<!-- Email spacer -->
<div style="height:32px"></div>
</body>
</html>
EMAILEOF
} | if command -v gpg &>/dev/null && gpg --list-keys "$TO_EMAIL" &>/dev/null; then
    # Encrypt with recipient's GPG key if available
    gpg --batch --yes --armor --encrypt --recipient "$TO_EMAIL" | \
        msmtp --file=/home/lch/.msmtprc "$TO_EMAIL"
else
    msmtp --file=/home/lch/.msmtprc --read-recipients
fi
