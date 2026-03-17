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
TRAY_SCRIPT_QT="/var/home/lch/projects/bazzite-laptop/tray/security_tray_qt.py"
LCH_UID="$(id -u lch)"

# --- Colors (256-color for richer output) ---
RED='\033[38;5;196m'
GRN='\033[38;5;46m'
YLW='\033[38;5;220m'
CYN='\033[38;5;51m'
BLU='\033[38;5;39m'
WHT='\033[38;5;255m'
GRY='\033[38;5;245m'
DRK='\033[38;5;238m'
BLD='\033[1m'
DIM='\033[2m'
RST='\033[0m'

# Background colors for status badges
BG_GRN='\033[48;5;22m'
BG_RED='\033[48;5;52m'
BG_YLW='\033[48;5;58m'

# --- Counters ---
PASS=0
FAIL=0
WARN=0
TOTAL=0
START_TIME=$(date +%s)
SECTION_START=$START_TIME  # updated by section_header()

# --- Section results tracking (for per-section summary) ---
declare -A SECTION_PASS SECTION_FAIL SECTION_WARN SECTION_TOTAL
CURRENT_SECTION=""

# --- Progress bar helper ---
progress_bar() {
    local pass=$1 fail=$2 warn=$3 total=$4 width=${5:-40}
    [[ $total -eq 0 ]] && return
    local pass_w=$(( pass * width / total ))
    local fail_w=$(( fail * width / total ))
    local warn_w=$(( warn * width / total ))
    # Ensure at least 1 char for non-zero counts
    [[ $pass -gt 0 && $pass_w -eq 0 ]] && pass_w=1
    [[ $fail -gt 0 && $fail_w -eq 0 ]] && fail_w=1
    [[ $warn -gt 0 && $warn_w -eq 0 ]] && warn_w=1
    # Adjust to fit width — shrink in priority order to avoid infinite loop
    local used=$(( pass_w + fail_w + warn_w ))
    while [[ $used -gt $width ]]; do
        if   [[ $pass_w -gt 0 ]]; then pass_w=$((pass_w - 1))
        elif [[ $fail_w -gt 1 ]]; then fail_w=$((fail_w - 1))
        elif [[ $warn_w -gt 1 ]]; then warn_w=$((warn_w - 1))
        else break
        fi
        used=$(( pass_w + fail_w + warn_w ))
    done
    local empty_w=$(( width - pass_w - fail_w - warn_w ))
    local bar=""
    local i
    for ((i=0; i<pass_w; i++)); do bar+="${GRN}█"; done
    for ((i=0; i<warn_w; i++)); do bar+="${YLW}█"; done
    for ((i=0; i<fail_w; i++)); do bar+="${RED}█"; done
    for ((i=0; i<empty_w; i++)); do bar+="${DRK}░"; done
    echo -ne "${bar}${RST}"
}


result() {
    TOTAL=$((TOTAL + 1))
    # Track per-section
    if [[ -n "$CURRENT_SECTION" ]]; then
        SECTION_TOTAL[$CURRENT_SECTION]=$(( ${SECTION_TOTAL[$CURRENT_SECTION]:-0} + 1 ))
    fi
    local num icon
    num=$(printf "%2d" "$TOTAL")
    case "$1" in
        PASS)
            PASS=$((PASS + 1))
            [[ -n "$CURRENT_SECTION" ]] && SECTION_PASS[$CURRENT_SECTION]=$(( ${SECTION_PASS[$CURRENT_SECTION]:-0} + 1 ))
            icon="${BG_GRN}${GRN}${BLD} PASS ${RST}"
            echo -e "  ${icon} ${WHT}${num}.${RST} ${GRY}$2${RST}"
            ;;
        FAIL)
            FAIL=$((FAIL + 1))
            [[ -n "$CURRENT_SECTION" ]] && SECTION_FAIL[$CURRENT_SECTION]=$(( ${SECTION_FAIL[$CURRENT_SECTION]:-0} + 1 ))
            icon="${BG_RED}${RED}${BLD} FAIL ${RST}"
            echo -e "  ${icon} ${WHT}${num}.${RST} ${WHT}${BLD}$2${RST}"
            ;;
        WARN)
            WARN=$((WARN + 1))
            [[ -n "$CURRENT_SECTION" ]] && SECTION_WARN[$CURRENT_SECTION]=$(( ${SECTION_WARN[$CURRENT_SECTION]:-0} + 1 ))
            icon="${BG_YLW}${YLW}${BLD} WARN ${RST}"
            echo -e "  ${icon} ${WHT}${num}.${RST} ${YLW}$2${RST}"
            ;;
    esac
    [[ -n "${3:-}" ]] && echo -e "              ${DIM}$3${RST}"
}

section_header() {
    local num="$1" title="$2" icon="$3"
    CURRENT_SECTION="$title"
    SECTION_START=$(date +%s)
    echo ""
    echo -e "  ${CYN}${icon}${RST} ${BLD}${WHT}Section ${num}: ${title}${RST}"
    echo -e "  ${DRK}$(printf '%.0s─' {1..52})${RST}"
}

section_footer() {
    local elapsed=$(( $(date +%s) - SECTION_START ))
    local sp=${SECTION_PASS[$CURRENT_SECTION]:-0}
    local sf=${SECTION_FAIL[$CURRENT_SECTION]:-0}
    local sw=${SECTION_WARN[$CURRENT_SECTION]:-0}
    local st=${SECTION_TOTAL[$CURRENT_SECTION]:-0}
    echo -e "  ${DRK}$(printf '%.0s·' {1..52})${RST}"
    echo -ne "  ${GRY}${sp}/${st} passed${RST}  "
    progress_bar "$sp" "$sf" "$sw" "$st" 20
    echo -e "  ${DIM}${elapsed}s${RST}"
}

[[ -t 1 ]] && clear
echo ""
echo -e "  ${CYN}${BLD}┌──────────────────────────────────────────────────────────┐${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${BLU}${BLD}╔═╗╔═╗╔═╗╦ ╦╦═╗╦╔╦╗╦ ╦${RST}  ${GRY}Integration Test Suite${RST}    ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${BLU}${BLD}╚═╗║╣ ║  ║ ║╠╦╝║ ║ ╚╦╝${RST}  ${GRY}v2.0 — $(date '+%Y-%m-%d')${RST}       ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${BLU}${BLD}╚═╝╚═╝╚═╝╚═╝╩╚═╩ ╩  ╩${RST}                             ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${GRY}Host:${RST}  ${WHT}$(hostname)${RST}$(printf '%*s' $((36 - ${#HOSTNAME})) '')${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${GRY}Date:${RST}  ${WHT}$(date '+%a %b %d, %Y  %I:%M %p')${RST}              ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${GRY}Tests:${RST} ${WHT}29 checks across 8 sections${RST}                   ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}└──────────────────────────────────────────────────────────┘${RST}"
echo ""

# ═══════════════════════════════════════════════════════════
# SECTION 1: Tray App
# ═══════════════════════════════════════════════════════════
section_header 1 "Tray App" "🖥"

# [01] Tray app is running (single instance) — legacy or Qt tray
TRAY_COUNT=$(pgrep -c -f "bazzite-security-tray[.]py" 2>/dev/null || echo "0")
QT_TRAY_COUNT=$(pgrep -c -f "security_tray_qt[.]py" 2>/dev/null || echo "0")
TOTAL_TRAY=$(( TRAY_COUNT + QT_TRAY_COUNT ))
if [[ "$TOTAL_TRAY" -eq 1 ]]; then
    if [[ "$QT_TRAY_COUNT" -eq 1 ]]; then
        TRAY_PID=$(pgrep -f "security_tray_qt[.]py" | head -1)
        result PASS "Qt tray running (single instance)" "PID: $TRAY_PID"
    else
        TRAY_PID=$(pgrep -f "bazzite-security-tray[.]py" | head -1)
        result PASS "Tray running (single instance)" "PID: $TRAY_PID"
    fi
elif [[ "$TOTAL_TRAY" -gt 1 ]]; then
    result FAIL "Multiple tray instances running" "Count: $TOTAL_TRAY — kill extras"
else
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

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 2: Icons
# ═══════════════════════════════════════════════════════════
section_header 2 "Icons" "🎨"

# [06] All 7 SVG icons exist and are valid XML
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

# [07] Symlinks in status/ are valid
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

# [08] Symlinks in apps/ are valid
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

# [09] index.theme exists for user hicolor
if [[ -f "$ICON_INDEX" ]]; then
    result PASS "hicolor index.theme exists" "$ICON_INDEX"
else
    result FAIL "hicolor index.theme missing" "Icons won't resolve in KDE without it"
fi

# [10] All 7 SVG icons exist in the hicolor scalable/status directory
HICOLOR_SVG_DIR="$USER_HOME/.local/share/icons/hicolor/scalable/status"
HICOLOR_ICONS_OK=true
HICOLOR_ICONS_BAD=""
for icon in $ICON_NAMES; do
    svg="$HICOLOR_SVG_DIR/${icon}.svg"
    if [[ ! -e "$svg" ]]; then
        HICOLOR_ICONS_OK=false
        HICOLOR_ICONS_BAD+=" ${icon}(missing)"
    fi
done
if $HICOLOR_ICONS_OK; then
    result PASS "All 7 SVG icons present in hicolor directory" "$HICOLOR_SVG_DIR"
else
    result FAIL "Missing icons in hicolor:$HICOLOR_ICONS_BAD" "Run: sudo ./scripts/deploy.sh"
fi

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 3: Desktop Entries & Menu
# ═══════════════════════════════════════════════════════════
section_header 3 "Desktop Entries & Menu" "📋"

# [11] All desktop entries pass validation
DESKTOP_OK=true
DESKTOP_BAD=""
for f in "$DESKTOP_DIR"/security-*.desktop; do
    [[ -f "$f" ]] || continue
    errors=$(desktop-file-validate "$f" 2>&1 | grep -v "hint:" || true)
    if [[ -n "$errors" ]]; then
        DESKTOP_OK=false
        DESKTOP_BAD+=" $(basename "$f")"
    fi
done
if $DESKTOP_OK; then
    COUNT=$(find "$DESKTOP_DIR" -name "security-*.desktop" | wc -l)
    result PASS "All desktop entries valid" "$COUNT entries pass desktop-file-validate"
else
    result FAIL "Desktop entries with errors:$DESKTOP_BAD"
fi

# [12] Menu file is valid XML
if [[ -f "$MENU_FILE" ]]; then
    if python3 -c "import xml.etree.ElementTree as ET; ET.parse('$MENU_FILE')" 2>/dev/null; then
        result PASS "security.menu is valid XML" "$MENU_FILE"
    else
        result FAIL "security.menu has invalid XML"
    fi
else
    result FAIL "security.menu not deployed" "$MENU_FILE"
fi

# [13] Directory entry deployed
if [[ -f "$DIRECTORY_DIR/security-directory.desktop" ]]; then
    result PASS "Directory entry deployed" "$DIRECTORY_DIR/security-directory.desktop"
else
    result FAIL "Directory entry missing from desktop-directories/"
fi

# [14] Autostart entry deployed and correct
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

# [15] All .desktop Icon= absolute paths resolve to actual files
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

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 4: Systemd Timers
# ═══════════════════════════════════════════════════════════
section_header 4 "Systemd Timers" "⏱"

# [16] All timers active
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

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 5: Script Deployment
# ═══════════════════════════════════════════════════════════
section_header 5 "Script Deployment" "📦"

# [17] All scripts deployed and match repo
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

# [18] Tray Python script deployed
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

# [19] PySide6 Qt tray module imports successfully
if [[ -f "$TRAY_SCRIPT_QT" ]]; then
    QT_IMPORT_OUT=$(su -c "source /var/home/lch/projects/bazzite-laptop/.venv/bin/activate && python -c 'from tray.security_tray_qt import SecurityTrayQt'" lch 2>&1)
    QT_IMPORT_EXIT=$?
    if [[ $QT_IMPORT_EXIT -eq 0 ]]; then
        result PASS "PySide6 Qt tray imports successfully" "$TRAY_SCRIPT_QT"
    else
        result FAIL "Qt tray import failed" "$(echo "$QT_IMPORT_OUT" | tail -1)"
    fi
else
    result WARN "Qt tray script not found" "$TRAY_SCRIPT_QT"
fi

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 6: Supporting Infrastructure
# ═══════════════════════════════════════════════════════════
section_header 6 "Infrastructure" "🔧"

# [20] Email config reachable
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

# [21] Quarantine directory correct perms
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

# [22] .status has both ClamAV and health keys
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

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 7: Quarantine Security
# ═══════════════════════════════════════════════════════════
section_header 7 "Quarantine Security" "🛡"

# [23] Path traversal blocked in quarantine-release.sh
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

section_footer

# ═══════════════════════════════════════════════════════════
# SECTION 8: System Security Services
# ═══════════════════════════════════════════════════════════
section_header 8 "Security Services" "🔒"

# [24] clamd service is inactive by default
if systemctl is-active --quiet clamd@scan 2>/dev/null; then
    result FAIL "clamd service is active" "Should be inactive until a scan starts"
else
    result PASS "clamd service is inactive by default"
fi

# [25] Firewall active, zone=drop
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

# [26] SELinux enforcing
SELINUX_MODE=$(getenforce 2>/dev/null || echo "unknown")
if [[ "$SELINUX_MODE" == "Enforcing" ]]; then
    result PASS "SELinux enforcing"
else
    result WARN "SELinux mode=$SELINUX_MODE" "Expected: Enforcing"
fi

# [27] USBGuard active
if systemctl is-active --quiet usbguard 2>/dev/null; then
    result PASS "USBGuard active"
else
    result WARN "USBGuard not running"
fi

# [28] ClamAV signatures fresh (< 7 days)
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

# [29] msmtp binary available
if command -v msmtp &>/dev/null; then
    result PASS "msmtp binary available"
else
    result WARN "msmtp not installed" "Email alerts won't work"
fi

section_footer

# ═══════════════════════════════════════════════════════════
# SUMMARY REPORT
# ═══════════════════════════════════════════════════════════
ELAPSED=$(( $(date +%s) - START_TIME ))
SCORE=$(( TOTAL > 0 ? (PASS * 100) / TOTAL : 0 ))

echo ""
echo -e "  ${CYN}${BLD}┌──────────────────────────────────────────────────────────┐${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${WHT}${BLD}RESULTS SUMMARY${RST}                                        ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}├──────────────────────────────────────────────────────────┤${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"

# Score gauge with large indicator
if [[ $SCORE -ge 90 ]]; then
    GRADE_COLOR="$GRN"; GRADE="A"; GRADE_LABEL="EXCELLENT"
elif [[ $SCORE -ge 80 ]]; then
    GRADE_COLOR="$GRN"; GRADE="B"; GRADE_LABEL="GOOD"
elif [[ $SCORE -ge 70 ]]; then
    GRADE_COLOR="$YLW"; GRADE="C"; GRADE_LABEL="FAIR"
elif [[ $SCORE -ge 60 ]]; then
    GRADE_COLOR="$YLW"; GRADE="D"; GRADE_LABEL="NEEDS WORK"
else
    GRADE_COLOR="$RED"; GRADE="F"; GRADE_LABEL="CRITICAL"
fi

echo -e "  ${CYN}${BLD}│${RST}   ${GRADE_COLOR}${BLD}  ╔═══╗${RST}                                              ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}   ${GRADE_COLOR}${BLD}  ║ ${GRADE} ║${RST}  ${WHT}${BLD}Score: ${SCORE}%${RST} ${GRY}(${GRADE_LABEL})${RST}                       ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}   ${GRADE_COLOR}${BLD}  ╚═══╝${RST}                                              ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"

# Overall progress bar
echo -ne "  ${CYN}${BLD}│${RST}   "
progress_bar "$PASS" "$FAIL" "$WARN" "$TOTAL" 44
echo -e "       ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"

# Stats line
printf "  ${CYN}${BLD}│${RST}   ${GRN}■${RST} Passed: %-4s ${RED}■${RST} Failed: %-4s ${YLW}■${RST} Warnings: %-4s    ${CYN}${BLD}│${RST}\n" "$PASS" "$FAIL" "$WARN"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"

# Per-section breakdown
echo -e "  ${CYN}${BLD}├──────────────────────────────────────────────────────────┤${RST}"
echo -e "  ${CYN}${BLD}│${RST}  ${WHT}${BLD}PER-SECTION BREAKDOWN${RST}                                  ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"

for section in "Tray App" "Icons" "Desktop Entries & Menu" "Systemd Timers" "Script Deployment" "Infrastructure" "Quarantine Security" "Security Services"; do
    sp=${SECTION_PASS[$section]:-0}
    sf=${SECTION_FAIL[$section]:-0}
    sw=${SECTION_WARN[$section]:-0}
    st=${SECTION_TOTAL[$section]:-0}
    [[ $st -eq 0 ]] && continue
    spct=$(( st > 0 ? (sp * 100) / st : 0 ))
    if [[ $sf -gt 0 ]]; then
        scolor="$RED"
        sdot="●"
    elif [[ $sw -gt 0 ]]; then
        scolor="$YLW"
        sdot="●"
    else
        scolor="$GRN"
        sdot="●"
    fi
    # Pad section name to 22 chars
    padded_name=$(printf "%-22s" "$section")
    echo -ne "  ${CYN}${BLD}│${RST}   ${scolor}${sdot}${RST} ${GRY}${padded_name}${RST} "
    progress_bar "$sp" "$sf" "$sw" "$st" 12
    printf " %3s%%  ${GRY}%d/%d${RST}" "$spct" "$sp" "$st"
    echo -e "  ${CYN}${BLD}│${RST}"
done

echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}├──────────────────────────────────────────────────────────┤${RST}"

# Final verdict
if [[ $FAIL -eq 0 && $WARN -eq 0 ]]; then
    echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
    echo -e "  ${CYN}${BLD}│${RST}   ${GRN}${BLD}✔  SYSTEM INTEGRATION: ALL CLEAR${RST}                       ${CYN}${BLD}│${RST}"
    echo -e "  ${CYN}${BLD}│${RST}   ${GRY}All ${TOTAL} checks passed. System is fully operational.${RST}   ${CYN}${BLD}│${RST}"
elif [[ $FAIL -eq 0 ]]; then
    echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
    echo -e "  ${CYN}${BLD}│${RST}   ${YLW}${BLD}⚠  SYSTEM OPERATIONAL${RST} ${GRY}with ${WARN} warning(s)${RST}                 ${CYN}${BLD}│${RST}"
    echo -e "  ${CYN}${BLD}│${RST}   ${GRY}Core functionality intact. Review warnings above.${RST}     ${CYN}${BLD}│${RST}"
else
    echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
    echo -e "  ${CYN}${BLD}│${RST}   ${RED}${BLD}✖  ${FAIL} INTEGRATION ISSUE(S) NEED ATTENTION${RST}              ${CYN}${BLD}│${RST}"
    echo -e "  ${CYN}${BLD}│${RST}   ${GRY}Review FAIL items above and run deploy.sh.${RST}             ${CYN}${BLD}│${RST}"
fi

echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
printf "  ${CYN}${BLD}│${RST}   ${GRY}Duration: %ds${RST}$(printf '%*s' $((43 - ${#ELAPSED})) '')${CYN}${BLD}│${RST}\n" "$ELAPSED"
echo -e "  ${CYN}${BLD}│${RST}                                                          ${CYN}${BLD}│${RST}"
echo -e "  ${CYN}${BLD}└──────────────────────────────────────────────────────────┘${RST}"
echo ""

[[ $FAIL -gt 0 ]] && exit 1
exit 0
