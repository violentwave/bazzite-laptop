#!/bin/bash
# integration-test.sh — Full integration test of the security system
# Tests the entire security system end-to-end on the live system.
# Unlike bazzite-security-test.sh (ClamAV focus) and system-health-test.sh
# (health focus), this tests the INTEGRATION between all components.
#
# Usage: sudo integration-test.sh
# Some tests need root, some test user-level features.

set -uo pipefail

# --- Root check ---
if [[ $EUID -ne 0 ]]; then
    echo "Error: Must run as root (sudo)" >&2
    exit 1
fi

# --- Configuration ---
USER_HOME="/home/lch"
STATUS_FILE="$USER_HOME/security/.status"
LOCK_FILE="$USER_HOME/security/.tray.lock"
ICON_DIR="$USER_HOME/security/icons/hicolor/scalable/status"
ICON_LINK_STATUS="$USER_HOME/.local/share/icons/hicolor/scalable/status"
ICON_LINK_APPS="$USER_HOME/.local/share/icons/hicolor/scalable/apps"
ICON_INDEX="$USER_HOME/.local/share/icons/hicolor/index.theme"
DESKTOP_DIR="$USER_HOME/.local/share/applications"
DIRECTORY_DIR="$USER_HOME/.local/share/desktop-directories"
MENU_FILE="$USER_HOME/.config/menus/applications-merged/security.menu"
AUTOSTART_FILE="$USER_HOME/.config/autostart/bazzite-security-tray.desktop"
TRAY_SCRIPT="$USER_HOME/security/bazzite-security-tray.py"
LCH_UID="$(id -u lch)"

# --- Colors ---
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
BLD='\033[1m'
DIM='\033[2m'
RST='\033[0m'

# --- Counters ---
PASS=0
FAIL=0
WARN=0
TOTAL=0

result() {
    TOTAL=$((TOTAL + 1))
    local num
    num=$(printf "%2d" "$TOTAL")
    case "$1" in
        PASS) PASS=$((PASS + 1)); echo -e "  ${GRN}[PASS]${RST} ${num}. $2" ;;
        FAIL) FAIL=$((FAIL + 1)); echo -e "  ${RED}[FAIL]${RST} ${num}. $2" ;;
        WARN) WARN=$((WARN + 1)); echo -e "  ${YLW}[WARN]${RST} ${num}. $2" ;;
    esac
    [[ -n "${3:-}" ]] && echo -e "         ${DIM}$3${RST}"
}

echo ""
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"
echo -e "${BLD}  Security System Integration Test${RST}"
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"
echo "  $(date '+%A %B %d, %Y — %I:%M %p %Z')"
echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 1: Tray App
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 1: Tray App${RST}"
echo ""

# [01] Tray app is running (single instance)
TRAY_COUNT=$(pgrep -c -f "bazzite-security-tray" 2>/dev/null || echo "0")
if [[ "$TRAY_COUNT" -eq 1 ]]; then
    TRAY_PID=$(pgrep -f "bazzite-security-tray" | head -1)
    result PASS "Tray running (single instance)" "PID: $TRAY_PID"
elif [[ "$TRAY_COUNT" -gt 1 ]]; then
    result FAIL "Multiple tray instances running" "Count: $TRAY_COUNT — kill extras"
elif [[ "$TRAY_COUNT" -eq 0 ]]; then
    result FAIL "Tray not running" "Start: /usr/local/bin/start-security-tray.sh"
fi

# [02] .status file readable/writable by lch
if [[ -f "$STATUS_FILE" ]]; then
    OWNER=$(stat -c '%U:%G' "$STATUS_FILE")
    if [[ "$OWNER" == "lch:lch" ]]; then
        result PASS ".status owned by lch:lch" "$STATUS_FILE"
    else
        result FAIL ".status wrong ownership" "Owner: $OWNER (expected lch:lch)"
    fi
else
    result FAIL ".status file missing" "$STATUS_FILE"
fi

# [03] .status is valid JSON with expected keys
if [[ -f "$STATUS_FILE" ]]; then
    if python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
required = ['state', 'result', 'timestamp']
missing = [k for k in required if k not in d]
if missing:
    print('missing:' + ','.join(missing))
    sys.exit(1)
print('ok:' + d.get('state','?') + '/' + d.get('result','?'))
" "$STATUS_FILE" 2>/dev/null; then
        STATUS_INFO=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
print(d.get('state','?') + '/' + d.get('result','?'))
" "$STATUS_FILE" 2>/dev/null)
        result PASS ".status valid JSON with required keys" "State: $STATUS_INFO"
    else
        result FAIL ".status missing required keys"
    fi
else
    result FAIL ".status file missing (skipping JSON check)"
fi

# [04] start-security-tray.sh deployed and executable
if [[ -x /usr/local/bin/start-security-tray.sh ]]; then
    result PASS "start-security-tray.sh deployed" "/usr/local/bin/start-security-tray.sh"
else
    result FAIL "start-security-tray.sh not deployed or not executable"
fi

# [05] Lock file exists (tray is holding it)
if [[ -f "$LOCK_FILE" ]]; then
    result PASS "Tray lock file exists" "$LOCK_FILE"
else
    if [[ "$TRAY_COUNT" -ge 1 ]]; then
        result FAIL "Tray running but no lock file" "$LOCK_FILE"
    else
        result WARN "No lock file (tray not running)" "$LOCK_FILE"
    fi
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 2: Icons
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 2: Icons${RST}"
echo ""

# [05] All 7 SVG icons exist and are valid XML
ICON_NAMES="bazzite-sec-green bazzite-sec-teal bazzite-sec-blue bazzite-sec-yellow bazzite-sec-red bazzite-sec-blank bazzite-sec-health-warn"
ICONS_OK=true
ICONS_BAD=""
for icon in $ICON_NAMES; do
    svg="$ICON_DIR/${icon}.svg"
    if [[ ! -f "$svg" ]]; then
        ICONS_OK=false
        ICONS_BAD+=" ${icon}(missing)"
    elif ! python3 -c "import xml.etree.ElementTree as ET; ET.parse('$svg')" 2>/dev/null; then
        ICONS_OK=false
        ICONS_BAD+=" ${icon}(invalid-xml)"
    fi
done
if $ICONS_OK; then
    result PASS "All 7 SVG icons valid" "$ICON_DIR"
else
    result FAIL "Icon issues:$ICONS_BAD"
fi

# [06] Symlinks in status/ are valid
LINKS_OK=true
LINKS_BAD=""
for icon in $ICON_NAMES; do
    link="$ICON_LINK_STATUS/${icon}.svg"
    if [[ -L "$link" && -e "$link" ]]; then
        : # ok
    elif [[ -L "$link" ]]; then
        LINKS_OK=false
        LINKS_BAD+=" ${icon}(broken)"
    else
        LINKS_OK=false
        LINKS_BAD+=" ${icon}(missing)"
    fi
done
if $LINKS_OK; then
    result PASS "Icon symlinks valid (status/)" "$ICON_LINK_STATUS"
else
    result FAIL "Broken symlinks:$LINKS_BAD"
fi

# [07] Symlinks in apps/ are valid
LINKS_OK=true
LINKS_BAD=""
for icon in $ICON_NAMES; do
    link="$ICON_LINK_APPS/${icon}.svg"
    if [[ -L "$link" && -e "$link" ]]; then
        : # ok
    elif [[ -L "$link" ]]; then
        LINKS_OK=false
        LINKS_BAD+=" ${icon}(broken)"
    else
        LINKS_OK=false
        LINKS_BAD+=" ${icon}(missing)"
    fi
done
if $LINKS_OK; then
    result PASS "Icon symlinks valid (apps/)" "$ICON_LINK_APPS"
else
    result FAIL "Broken symlinks:$LINKS_BAD"
fi

# [08] index.theme exists for user hicolor
if [[ -f "$ICON_INDEX" ]]; then
    result PASS "hicolor index.theme exists" "$ICON_INDEX"
else
    result FAIL "hicolor index.theme missing" "Icons won't resolve in KDE without it"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 3: Desktop Entries & Menu
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 3: Desktop Entries & Menu${RST}"
echo ""

# [09] All desktop entries pass validation
DESKTOP_OK=true
DESKTOP_BAD=""
for f in "$DESKTOP_DIR"/security-*.desktop; do
    name=$(basename "$f")
    errors=$(desktop-file-validate "$f" 2>&1 | grep -v "hint:" || true)
    if [[ -n "$errors" ]]; then
        DESKTOP_OK=false
        DESKTOP_BAD+=" $name"
    fi
done
if $DESKTOP_OK; then
    COUNT=$(find "$DESKTOP_DIR" -name "security-*.desktop" | wc -l)
    result PASS "All desktop entries valid" "$COUNT entries pass desktop-file-validate"
else
    result FAIL "Desktop entries with errors:$DESKTOP_BAD"
fi

# [10] Menu file is valid XML
if [[ -f "$MENU_FILE" ]]; then
    if python3 -c "import xml.etree.ElementTree as ET; ET.parse('$MENU_FILE')" 2>/dev/null; then
        result PASS "security.menu is valid XML" "$MENU_FILE"
    else
        result FAIL "security.menu has invalid XML"
    fi
else
    result FAIL "security.menu not deployed" "$MENU_FILE"
fi

# [11] Directory entry deployed
if [[ -f "$DIRECTORY_DIR/security-directory.desktop" ]]; then
    result PASS "Directory entry deployed" "$DIRECTORY_DIR/security-directory.desktop"
else
    result FAIL "Directory entry missing from desktop-directories/"
fi

# [12] Autostart entry deployed and correct
if [[ -f "$AUTOSTART_FILE" ]]; then
    EXEC_LINE=$(grep "^Exec=" "$AUTOSTART_FILE" | cut -d= -f2-)
    if [[ "$EXEC_LINE" == "/usr/local/bin/start-security-tray.sh" ]]; then
        result PASS "Autostart entry correct" "Exec=$EXEC_LINE"
    else
        result WARN "Autostart Exec may be outdated" "Exec=$EXEC_LINE"
    fi
else
    result FAIL "Autostart entry missing" "$AUTOSTART_FILE"
fi

# [13] All .desktop Icon= absolute paths resolve to actual files
ICONS_MISSING=""
for f in "$DESKTOP_DIR"/security-*.desktop; do
    [[ -f "$f" ]] || continue
    icon_val=$(grep '^Icon=' "$f" 2>/dev/null | cut -d= -f2)
    if [[ "$icon_val" == /* ]] && [[ ! -f "$icon_val" ]]; then
        ICONS_MISSING+=" $(basename "$f")"
    fi
done
if [[ -z "$ICONS_MISSING" ]]; then
    result PASS "All .desktop absolute Icon= paths resolve"
else
    result FAIL "Missing icon files:$ICONS_MISSING"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 4: Systemd Timers
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 4: Systemd Timers${RST}"
echo ""

# [13] All timers active
TIMERS_OK=true
TIMERS_BAD=""
for timer in clamav-quick.timer clamav-deep.timer clamav-healthcheck.timer system-health.timer; do
    if systemctl is-active --quiet "$timer" 2>/dev/null; then
        : # ok
    else
        TIMERS_OK=false
        STATE=$(systemctl is-active "$timer" 2>/dev/null || echo "not-found")
        TIMERS_BAD+=" ${timer}($STATE)"
    fi
done
if $TIMERS_OK; then
    result PASS "All 4 systemd timers active"
else
    result FAIL "Inactive timers:$TIMERS_BAD"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 5: Script Deployment
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 5: Script Deployment${RST}"
echo ""

# [14] All scripts deployed and match repo
SCRIPTS="clamav-scan.sh clamav-alert.sh clamav-healthcheck.sh quarantine-release.sh bazzite-security-test.sh system-health-snapshot.sh system-health-test.sh start-security-tray.sh"
SCRIPTS_OK=true
SCRIPTS_BAD=""
for script in $SCRIPTS; do
    REPO="/var/home/lch/projects/bazzite-laptop/scripts/$script"
    DEPLOYED="/usr/local/bin/$script"
    if [[ ! -f "$DEPLOYED" ]]; then
        SCRIPTS_OK=false
        SCRIPTS_BAD+=" ${script}(not-deployed)"
    elif [[ -f "$REPO" ]] && ! diff -q "$REPO" "$DEPLOYED" &>/dev/null; then
        SCRIPTS_OK=false
        SCRIPTS_BAD+=" ${script}(mismatch)"
    fi
done
if $SCRIPTS_OK; then
    result PASS "All scripts deployed and matching repo"
else
    result FAIL "Script issues:$SCRIPTS_BAD" "Run: sudo ./scripts/deploy.sh"
fi

# [15] Tray Python script deployed
if [[ -f "$TRAY_SCRIPT" ]]; then
    REPO_TRAY="/var/home/lch/projects/bazzite-laptop/tray/bazzite-security-tray.py"
    if [[ -f "$REPO_TRAY" ]] && diff -q "$REPO_TRAY" "$TRAY_SCRIPT" &>/dev/null; then
        result PASS "Tray Python script deployed and matches repo"
    elif [[ -f "$REPO_TRAY" ]]; then
        result WARN "Tray script deployed but differs from repo"
    else
        result PASS "Tray Python script deployed" "$TRAY_SCRIPT"
    fi
else
    result FAIL "Tray script missing" "$TRAY_SCRIPT"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 6: Supporting Infrastructure
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 6: Infrastructure${RST}"
echo ""

# [16] Email config reachable
if [[ -f "$USER_HOME/.msmtprc" ]]; then
    PERMS=$(stat -c '%a' "$USER_HOME/.msmtprc")
    if [[ "$PERMS" == "600" ]]; then
        result PASS "Email config present with correct perms" "600 $USER_HOME/.msmtprc"
    else
        result WARN "Email config present but perms=$PERMS" "Expected 600"
    fi
else
    result WARN "No email config" "Email alerts won't send without $USER_HOME/.msmtprc"
fi

# [17] Quarantine directory correct perms
if [[ -d "$USER_HOME/security/quarantine" ]]; then
    Q_PERMS=$(stat -c '%a' "$USER_HOME/security/quarantine")
    Q_OWNER=$(stat -c '%U:%G' "$USER_HOME/security/quarantine")
    if [[ "$Q_PERMS" == "750" && "$Q_OWNER" == "root:lch" ]]; then
        result PASS "Quarantine dir perms correct" "$Q_OWNER $Q_PERMS"
    else
        result WARN "Quarantine dir perms" "owner=$Q_OWNER perms=$Q_PERMS (expected root:lch 750)"
    fi
else
    result FAIL "Quarantine directory missing"
fi

# [18] .status has both ClamAV and health keys
if [[ -f "$STATUS_FILE" ]]; then
    KEYS_CHECK=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
scan = 'state' in d and 'result' in d
health = 'health_status' in d
if scan and health:
    print('both')
elif scan:
    print('scan-only')
elif health:
    print('health-only')
else:
    print('neither')
" "$STATUS_FILE" 2>/dev/null || echo "error")
    case "$KEYS_CHECK" in
        both) result PASS ".status has both ClamAV and health keys" ;;
        scan-only) result WARN ".status missing health keys" "Run: sudo system-health-snapshot.sh" ;;
        health-only) result WARN ".status missing scan keys" "Run: sudo clamav-scan.sh quick" ;;
        *) result FAIL ".status missing expected keys" ;;
    esac
else
    result FAIL ".status file missing"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 7: Quarantine Security
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 7: Quarantine Security${RST}"
echo ""

# Path traversal blocked in quarantine-release.sh
if [[ -x "/usr/local/bin/quarantine-release.sh" ]]; then
    TRAVERSAL_OUTPUT=$(/usr/local/bin/quarantine-release.sh "../../etc/passwd" /tmp 2>&1)
    TRAVERSAL_EXIT=$?
    if [[ $TRAVERSAL_EXIT -ne 0 ]]; then
        result PASS "Path traversal blocked in quarantine-release.sh"
    else
        result FAIL "Path traversal NOT blocked" "../../etc/passwd was accepted"
    fi
else
    result WARN "quarantine-release.sh not deployed" "Cannot test path traversal"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 8: System Security Services
# ═══════════════════════════════════════════════════════════
echo -e "  ${BLD}Section 8: Security Services${RST}"
echo ""

# Firewall active, zone=drop
if systemctl is-active --quiet firewalld 2>/dev/null; then
    DEFAULT_ZONE=$(firewall-cmd --get-default-zone 2>/dev/null)
    if [[ "$DEFAULT_ZONE" == "drop" ]]; then
        result PASS "Firewall active, default zone=drop"
    else
        result WARN "Firewall active but zone=$DEFAULT_ZONE" "Expected: drop"
    fi
else
    result FAIL "Firewall not running"
fi

# SELinux enforcing
SELINUX_MODE=$(getenforce 2>/dev/null || echo "unknown")
if [[ "$SELINUX_MODE" == "Enforcing" ]]; then
    result PASS "SELinux enforcing"
else
    result WARN "SELinux mode=$SELINUX_MODE" "Expected: Enforcing"
fi

# USBGuard active
if systemctl is-active --quiet usbguard 2>/dev/null; then
    result PASS "USBGuard active"
else
    result WARN "USBGuard not running"
fi

# ClamAV signatures fresh (< 7 days)
SIG_DIR="/var/lib/clamav"
if [[ -d "$SIG_DIR" ]]; then
    NEWEST_SIG=$(find "$SIG_DIR" \( -name "*.cvd" -o -name "*.cld" \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    if [[ -n "$NEWEST_SIG" ]]; then
        SIG_AGE_DAYS=$(( ($(date +%s) - $(stat -c '%Y' "$NEWEST_SIG")) / 86400 ))
        if [[ "$SIG_AGE_DAYS" -le 7 ]]; then
            result PASS "ClamAV signatures fresh" "${SIG_AGE_DAYS}d old ($(basename "$NEWEST_SIG"))"
        else
            result WARN "ClamAV signatures stale" "${SIG_AGE_DAYS} days old"
        fi
    else
        result FAIL "No ClamAV signature files found" "$SIG_DIR"
    fi
else
    result FAIL "ClamAV signature directory missing" "$SIG_DIR"
fi

# msmtp binary available
if command -v msmtp &>/dev/null; then
    result PASS "msmtp binary available"
else
    result WARN "msmtp not installed" "Email alerts won't work"
fi

echo ""

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"
echo -e "  Results: ${GRN}${PASS} passed${RST} | ${RED}${FAIL} failed${RST} | ${YLW}${WARN} warnings${RST} | ${TOTAL} total"
echo -e "${BLD}═══════════════════════════════════════════════════════════${RST}"

if [[ $FAIL -eq 0 && $WARN -eq 0 ]]; then
    echo -e "  ${GRN}${BLD}✔ Full system integration: ALL CLEAR${RST}"
elif [[ $FAIL -eq 0 ]]; then
    echo -e "  ${YLW}${BLD}✔ System operational with ${WARN} warning(s)${RST}"
else
    echo -e "  ${RED}${BLD}✖ ${FAIL} integration issue(s) need attention${RST}"
fi
echo ""

[[ $FAIL -gt 0 ]] && exit 1
exit 0
