#!/bin/bash
# system-health-test.sh — Validation suite for system health monitoring
# Part of: bazzite-laptop security & monitoring project
# Location: /usr/local/bin/system-health-test.sh
#
# Verifies that all health monitoring components are correctly installed,
# configured, and functional. Matches the pattern of bazzite-security-test.sh.
#
# Usage: sudo system-health-test.sh

set -uo pipefail

PASS=0
FAIL=0
WARN=0
TOTAL=0

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
BLD='\033[1m'
RST='\033[0m'

result() {
    TOTAL=$((TOTAL + 1))
    local num
    num=$(printf "%2d" "$TOTAL")
    case "$1" in
        PASS) PASS=$((PASS + 1)); echo -e "  ${GRN}[PASS]${RST} ${num}. $2" ;;
        FAIL) FAIL=$((FAIL + 1)); echo -e "  ${RED}[FAIL]${RST} ${num}. $2" ;;
        WARN) WARN=$((WARN + 1)); echo -e "  ${YLW}[WARN]${RST} ${num}. $2" ;;
    esac
}

echo ""
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"
echo -e "${BLD}  System Health Monitoring — Validation Suite${RST}"
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"
echo "  $(date '+%A %B %d, %Y — %I:%M %p %Z')"
echo ""

# ── 1. Script exists and is executable ──
if [[ -x /usr/local/bin/system-health-snapshot.sh ]]; then
    result PASS "system-health-snapshot.sh installed and executable"
else
    result FAIL "system-health-snapshot.sh not found or not executable at /usr/local/bin/"
fi

# ── 2. Log directory exists ──
if [[ -d /var/log/system-health ]]; then
    result PASS "Log directory /var/log/system-health/ exists"
else
    result FAIL "Log directory /var/log/system-health/ missing"
fi

# ── 3. Logrotate config ──
if [[ -f /etc/logrotate.d/system-health ]]; then
    result PASS "Logrotate config installed"
else
    result FAIL "Logrotate config missing at /etc/logrotate.d/system-health"
fi

# ── 4. Systemd timer active ──
TIMER_STATE=$(systemctl is-active system-health.timer 2>/dev/null || echo "inactive")
if [[ "$TIMER_STATE" == "active" ]]; then
    result PASS "system-health.timer is active"
else
    result FAIL "system-health.timer is ${TIMER_STATE}"
fi

# ── 5. Systemd timer enabled ──
TIMER_ENABLED=$(systemctl is-enabled system-health.timer 2>/dev/null || echo "disabled")
if [[ "$TIMER_ENABLED" == "enabled" ]]; then
    result PASS "system-health.timer is enabled (survives reboot)"
else
    result FAIL "system-health.timer is ${TIMER_ENABLED}"
fi

# ── 6. Systemd service unit exists ──
if systemctl cat system-health.service &>/dev/null; then
    result PASS "system-health.service unit found"
else
    result FAIL "system-health.service unit missing"
fi

# ── 7. smartctl available ──
if command -v smartctl &>/dev/null; then
    result PASS "smartctl available: $(smartctl --version | head -1)"
else
    result FAIL "smartctl not found — install smartmontools"
fi

# ── 8. nvidia-smi available ──
if command -v nvidia-smi &>/dev/null; then
    result PASS "nvidia-smi available"
else
    result WARN "nvidia-smi not found (GPU monitoring will be limited)"
fi

# ── 9. lm-sensors available ──
if command -v sensors &>/dev/null; then
    result PASS "lm-sensors available"
else
    result WARN "lm-sensors not found (will use thermal zone fallback)"
fi

# ── 10. Internal SSD readable ──
if [[ -b /dev/sda ]]; then
    SDA_HEALTH=$(smartctl -H /dev/sda 2>/dev/null | grep "SMART overall-health" | awk -F': ' '{print $2}' | xargs)
    if [[ "$SDA_HEALTH" == "PASSED" ]]; then
        result PASS "Internal SSD (sda) SMART readable — health: PASSED"
    elif [[ -n "$SDA_HEALTH" ]]; then
        result WARN "Internal SSD (sda) SMART readable — health: ${SDA_HEALTH}"
    else
        result FAIL "Cannot read SMART from /dev/sda (permission issue?)"
    fi
else
    result FAIL "/dev/sda not found"
fi

# ── 11. External NVMe readable (if connected) ──
if [[ -b /dev/sdb ]]; then
    SDB_HEALTH=$(smartctl -H /dev/sdb 2>/dev/null | grep "SMART overall-health" | awk -F': ' '{print $2}' | xargs)
    if [[ "$SDB_HEALTH" == "PASSED" ]]; then
        result PASS "External NVMe (sdb) SMART readable — health: PASSED"
    elif [[ -n "$SDB_HEALTH" ]]; then
        result WARN "External NVMe (sdb) SMART readable — health: ${SDB_HEALTH}"
    else
        result WARN "Cannot read SMART from /dev/sdb"
    fi
else
    result WARN "External NVMe (sdb) not connected — skipping"
fi

# ── 12. KDE desktop entries ──
DESK_COUNT=0
for f in security-health-snapshot.desktop security-health-logs.desktop; do
    [[ -f "/home/lch/.local/share/applications/$f" ]] && DESK_COUNT=$((DESK_COUNT + 1))
done
if [[ $DESK_COUNT -eq 2 ]]; then
    result PASS "KDE Security menu entries installed (${DESK_COUNT}/2)"
elif [[ $DESK_COUNT -gt 0 ]]; then
    result WARN "Only ${DESK_COUNT}/2 KDE menu entries found"
else
    result FAIL "No KDE Security menu entries for health monitoring"
fi

# ── 13. Tray status integration ──
STATUS_FILE="/home/lch/security/.status"
if [[ -f "$STATUS_FILE" ]]; then
    if python3 -c "import json; json.load(open('${STATUS_FILE}'))" 2>/dev/null; then
        HAS_HEALTH=$(python3 -c "
import json
with open('${STATUS_FILE}') as f:
    st = json.load(f)
print('yes' if 'health_status' in st else 'no')
" 2>/dev/null || echo "no")
        if [[ "$HAS_HEALTH" == "yes" ]]; then
            result PASS "Tray status file has health data"
        else
            result WARN "Tray status file exists but no health data yet (run snapshot first)"
        fi
    else
        result WARN "Tray status file exists but is not valid JSON"
    fi
else
    result FAIL "Tray status file not found at ${STATUS_FILE}"
fi

# ── 14. Email infrastructure ──
if [[ -f /home/lch/.msmtprc ]]; then
    if command -v msmtp &>/dev/null; then
        result PASS "Email infrastructure: msmtp + config present"
    else
        result WARN "msmtprc exists but msmtp command not found"
    fi
else
    result WARN "No msmtprc — health email alerts will not send"
fi

# ── 15. Dry run — execute snapshot and check exit code ──
echo ""
echo -e "  ${BLD}Running dry health snapshot...${RST}"
if /usr/local/bin/system-health-snapshot.sh --quiet 2>/dev/null; then
    result PASS "Health snapshot executed successfully (exit 0 — all OK)"
else
    EXIT=$?
    case $EXIT in
        1) result WARN "Health snapshot found warnings (exit 1)" ;;
        2) result WARN "Health snapshot found critical issues (exit 2)" ;;
        *) result FAIL "Health snapshot failed (exit ${EXIT})" ;;
    esac
fi

# ── 16. Log file created ──
LATEST="/var/log/system-health/health-latest.log"
if [[ -L "$LATEST" && -f "$LATEST" ]]; then
    result PASS "Log created: $(readlink -f "$LATEST")"
else
    result FAIL "No health-latest.log symlink after dry run"
fi

# ═══════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════

echo ""
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"
echo -e "  Results: ${GRN}${PASS} passed${RST} | ${RED}${FAIL} failed${RST} | ${YLW}${WARN} warnings${RST} | ${TOTAL} total"
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"

if [[ $FAIL -eq 0 ]]; then
    echo -e "  ${GRN}${BLD}✔ System health monitoring is operational${RST}"
else
    echo -e "  ${RED}${BLD}✖ ${FAIL} component(s) need attention${RST}"
fi
echo ""

[[ $FAIL -gt 0 ]] && exit 1
exit 0
