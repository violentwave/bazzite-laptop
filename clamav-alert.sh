#!/bin/bash
# ClamAV email alert wrapper using msmtp
# Deploy to: /usr/local/bin/clamav-alert.sh (chmod +x)
# Usage: echo "body" | clamav-alert.sh "Subject line"
#    or: clamav-alert.sh "Subject line" "Body text"
set -euo pipefail

SUBJECT="${1:?Usage: $0 \"subject\" [\"body\"]}"
TO_EMAIL="${CLAMAV_ALERT_EMAIL:-$(grep '^from ' ~/.msmtprc 2>/dev/null | awk '{print $2}')}"
HOSTNAME="$(hostname)"

if [[ -z "$TO_EMAIL" ]]; then
    echo "Error: No recipient address. Set CLAMAV_ALERT_EMAIL or configure 'from' in ~/.msmtprc" >&2
    exit 1
fi

if [[ -n "${2:-}" ]]; then
    BODY="$2"
else
    BODY="$(cat)"
fi

{
    echo "To: ${TO_EMAIL}"
    echo "Subject: ${SUBJECT}"
    echo "X-Mailer: clamav-alert"
    echo ""
    echo "$BODY"
    echo ""
    echo "-- Sent from ${HOSTNAME}"
} | msmtp --read-recipients
