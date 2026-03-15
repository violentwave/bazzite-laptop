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

HOSTNAME="$(hostname)"
DATE_STR="$(date '+%B %d, %Y at %I:%M %p')"

# Capitalize scan type for display (handles "healthcheck" → "Healthcheck")
SCAN_TYPE_DISPLAY="${SCAN_TYPE^}"

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
        filename=$(basename "$filepath")
        threatname=$(echo "$line" | sed 's/^.*: //' | sed 's/ FOUND$//')
        THREAT_TABLE_ROWS+="<tr style=\"border-bottom:1px solid #e2e8f0;\"><td style=\"padding:10px 12px;font-family:'Courier New',monospace;font-size:13px;color:#1e293b\">${filename}</td><td style=\"padding:10px 12px;font-size:13px;color:#64748b;word-break:break-all\">${filepath}</td><td style=\"padding:10px 12px;font-size:13px;color:#ef4444;font-weight:600\">${threatname}</td><td style=\"padding:10px 12px;font-size:13px;color:#22c55e\">Quarantined</td></tr>"
    done < <(grep "FOUND$" "$LOG_FILE" 2>/dev/null || true)
fi

# --- Build body content based on status ---
BODY_CONTENT=""

case "$STATUS" in
    clean)
        BODY_CONTENT="
        <p style=\"font-size:15px;color:#1e293b;line-height:1.6;margin:0 0 20px 0\">Your scheduled <strong>${SCAN_TYPE}</strong> scan completed successfully with no threats detected.</p>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px\">
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b;width:40%\">Scan Type</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${SCAN_TYPE_DISPLAY}</td></tr>
            <tr style=\"background:#ffffff\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Files Scanned</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${FILES_SCANNED}</td></tr>
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Threats Found</td><td style=\"padding:10px 16px;font-size:14px;color:#22c55e;font-weight:600\">0</td></tr>
            <tr style=\"background:#ffffff\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Duration</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${DURATION}</td></tr>
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Completed</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${DATE_STR}</td></tr>
        </table>
        <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Your system remains protected. Virus signatures are kept up to date automatically before each scan.</p>"
        ;;

    threats)
        BODY_CONTENT="
        <p style=\"font-size:15px;color:#1e293b;line-height:1.6;margin:0 0 20px 0\"><strong>${THREAT_COUNT} threat(s)</strong> were detected during the <strong>${SCAN_TYPE}</strong> scan. Infected files have been moved to quarantine.</p>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px\">
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b;width:40%\">Scan Type</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${SCAN_TYPE_DISPLAY}</td></tr>
            <tr style=\"background:#ffffff\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Files Scanned</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${FILES_SCANNED}</td></tr>
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Threats Found</td><td style=\"padding:10px 16px;font-size:14px;color:#ef4444;font-weight:600\">${THREAT_COUNT}</td></tr>
            <tr style=\"background:#ffffff\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Duration</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${DURATION}</td></tr>
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Quarantine</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">~/security/quarantine</td></tr>
        </table>
        <h3 style=\"font-size:16px;color:#ef4444;margin:0 0 12px 0\">Threat Details</h3>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;border:1px solid #e2e8f0\">
            <tr style=\"background:#1e293b\"><th style=\"padding:10px 12px;font-size:12px;color:#f8fafc;text-align:left;text-transform:uppercase;letter-spacing:0.5px\">File</th><th style=\"padding:10px 12px;font-size:12px;color:#f8fafc;text-align:left;text-transform:uppercase;letter-spacing:0.5px\">Original Path</th><th style=\"padding:10px 12px;font-size:12px;color:#f8fafc;text-align:left;text-transform:uppercase;letter-spacing:0.5px\">Threat Detected</th><th style=\"padding:10px 12px;font-size:12px;color:#f8fafc;text-align:left;text-transform:uppercase;letter-spacing:0.5px\">Action</th></tr>
            ${THREAT_TABLE_ROWS}
        </table>
        <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Review the quarantined files and delete them if they are confirmed threats. Log file: <code style=\"background:#f1f5f9;padding:2px 6px;border-radius:3px;font-size:13px\">${LOG_FILE}</code></p>"
        ;;

    error)
        ERROR_DETAILS=""
        if [[ -f "$LOG_FILE" ]]; then
            ERROR_DETAILS=$(tail -20 "$LOG_FILE" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g' || echo "Could not read log file")
        fi
        BODY_CONTENT="
        <p style=\"font-size:15px;color:#1e293b;line-height:1.6;margin:0 0 20px 0\">An error occurred during the <strong>${SCAN_TYPE}</strong> scan. The scan may not have completed fully.</p>
        <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px\">
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b;width:40%\">Scan Type</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${SCAN_TYPE_DISPLAY}</td></tr>
            <tr style=\"background:#ffffff\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Files Scanned</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${FILES_SCANNED}</td></tr>
            <tr style=\"background:#f1f5f9\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Duration</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${DURATION}</td></tr>
            <tr style=\"background:#ffffff\"><td style=\"padding:10px 16px;font-size:14px;color:#64748b\">Completed</td><td style=\"padding:10px 16px;font-size:14px;color:#1e293b;font-weight:600\">${DATE_STR}</td></tr>
        </table>
        <h3 style=\"font-size:16px;color:#f59e0b;margin:0 0 12px 0\">Error Details</h3>
        <pre style=\"background:#1e293b;color:#e2e8f0;padding:16px;border-radius:6px;font-size:13px;overflow-x:auto;margin:0 0 16px 0\">${ERROR_DETAILS}</pre>
        <p style=\"font-size:14px;color:#64748b;line-height:1.6;margin:0\">Check the full log at: <code style=\"background:#f1f5f9;padding:2px 6px;border-radius:3px;font-size:13px\">${LOG_FILE}</code></p>"
        ;;
esac

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
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table style="max-width:600px;margin:0 auto;background:#ffffff;border-collapse:collapse;width:100%">
    <!-- Header -->
    <tr><td style="background:#1a1a2e;padding:24px 32px;text-align:center">
        <h1 style="margin:0;font-size:20px;letter-spacing:2px;color:#00d4ff;font-weight:700">BAZZITE SECURITY</h1>
    </td></tr>
    <!-- Status Banner -->
    <tr><td style="background:${BANNER_COLOR};padding:16px 32px;text-align:center">
        <span style="font-size:22px;color:#ffffff;font-weight:700">${BANNER_ICON} ${BANNER_TEXT}</span>
    </td></tr>
    <!-- Body -->
    <tr><td style="padding:32px;background:#f8fafc">
        ${BODY_CONTENT}
    </td></tr>
$(if [[ -n "$HEALTH_SUMMARY" ]]; then cat <<HEALTHEOF
    <!-- Health Summary -->
    <tr><td style="padding:16px 32px;background:#f1f5f9;border-top:1px solid #e2e8f0">
        <pre style="margin:0;font-family:'Cascadia Code','Courier New',monospace;font-size:12px;color:#475569;white-space:pre-wrap">${HEALTH_SUMMARY}</pre>
    </td></tr>
HEALTHEOF
fi)
    <!-- Footer -->
    <tr><td style="padding:20px 32px;text-align:center;border-top:1px solid #e2e8f0">
        <p style="margin:0;font-size:12px;color:#94a3b8">Bazzite Security &middot; Acer Predator G3-571</p>
    </td></tr>
</table>
</body>
</html>
EMAILEOF
} | msmtp --file=/home/lch/.msmtprc --read-recipients
