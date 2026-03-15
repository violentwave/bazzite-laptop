#!/bin/bash
# system-health-snapshot.sh — Hardware & performance health monitoring
# Part of: bazzite-laptop security & monitoring project
# Location: /usr/local/bin/system-health-snapshot.sh
#
# Collects SMART disk health, GPU state, CPU thermals, storage/ZRAM stats,
# and key service status. Writes timestamped logs with delta tracking to
# detect degradation trends. Integrates with the existing security tray
# app and email alert infrastructure.
#
# Usage:
#   system-health-snapshot.sh              Interactive (terminal output + log)
#   system-health-snapshot.sh --email      Force email even if all OK
#   system-health-snapshot.sh --quiet      No terminal output (for timers)
#   system-health-snapshot.sh --append     Compact summary only (for scan email)
#   system-health-snapshot.sh --selftest   Run SMART extended test with sleep inhibit
#
# Exit codes:
#   0 — All OK
#   1 — Warnings detected
#   2 — Critical issues detected
#   3 — Script error

set -uo pipefail

# --- Cleanup temp files on exit ---
trap 'rm -f "${DISK_WARNS_TMP:-}" "${DELTA_TMP:-}" 2>/dev/null' EXIT

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

readonly VERSION="1.0.0"

readonly LOG_DIR="/var/log/system-health"
readonly DELTA_FILE="${LOG_DIR}/health-deltas.dat"
readonly STATUS_FILE="/home/lch/security/.status"
readonly MSMTPRC="/home/lch/.msmtprc"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M')
readonly TIMESTAMP
readonly LOG_FILE="${LOG_DIR}/health-${TIMESTAMP}.log"
readonly LATEST_LINK="${LOG_DIR}/health-latest.log"

# Dynamic device lookup — avoids hardcoded /dev/sdX that changes with device ordering
# Internal SSD: resolve from LUKS UUID to parent disk device for SMART checks
_LUKS_PART=$(blkid -U "luks-ec338b68-2489-477e-bd89-592d308f450c" 2>/dev/null) || true
_DEV_SDA=""
if [[ -n "$_LUKS_PART" ]]; then
    _SDA_PARENT=$(lsblk -no pkname "$_LUKS_PART" 2>/dev/null | head -1)
    [[ -n "$_SDA_PARENT" ]] && _DEV_SDA="/dev/${_SDA_PARENT}"
fi
readonly DEV_SDA="$_DEV_SDA"
readonly SDA_LABEL="Internal SSD (${DEV_SDA:-not found} — SK hynix 256GB SATA)"

# External NVMe: resolve from mount point to parent disk device for SMART checks
_SDB_PART=$(findmnt -no SOURCE /run/media/lch/SteamLibrary 2>/dev/null) || true
_DEV_SDB=""
if [[ -n "$_SDB_PART" ]]; then
    _SDB_PARENT=$(lsblk -no pkname "$_SDB_PART" 2>/dev/null | head -1)
    if [[ -n "$_SDB_PARENT" ]]; then
        _DEV_SDB="/dev/${_SDB_PARENT}"
    else
        _DEV_SDB="$_SDB_PART"
    fi
fi
readonly DEV_SDB="$_DEV_SDB"
readonly SDB_LABEL="External NVMe (${DEV_SDB:-not found} — WD SN580E 2TB USB)"

# ── Thresholds ──
# SMART (sda — SATA SSD)
readonly THRESH_REALLOC=20               # Reallocated sector count
readonly THRESH_UNCORRECT=100            # Offline uncorrectable sectors
readonly THRESH_WEAR=500                 # Wear leveling cycles
# SMART (sdb — NVMe)
readonly THRESH_NVME_SPARE=20            # Available spare % (warn if BELOW)
readonly THRESH_NVME_USED=80             # Percentage used (warn if ABOVE)
# Thermal
readonly THRESH_GPU_TEMP=85              # GPU temperature °C
readonly THRESH_CPU_TEMP=90              # CPU package temperature °C
# Storage
readonly THRESH_DISK_PCT=85              # Filesystem usage %
readonly THRESH_ZRAM_PCT=80              # ZRAM utilization %

# ── Terminal colors ──
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
BLD='\033[1m'
RST='\033[0m'

# ─────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────

SEND_EMAIL=false
QUIET=false
APPEND_MODE=false
RUN_SELFTEST=false

for arg in "$@"; do
    case "$arg" in
        --email)    SEND_EMAIL=true ;;
        --quiet)    QUIET=true ;;
        --append)   APPEND_MODE=true; QUIET=true ;;
        --selftest) RUN_SELFTEST=true ;;
        --version)
            echo "system-health-snapshot.sh v${VERSION}"
            exit 0
            ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--email] [--quiet] [--append] [--selftest] [--version]"
            echo "  --email      Send email alert (always sends on warnings)"
            echo "  --quiet      Suppress terminal output (timer/cron use)"
            echo "  --append     Compact summary for embedding in scan emails"
            echo "  --selftest   Run SMART extended self-test with sleep inhibit"
            echo "  --version    Print version and exit"
            exit 0
            ;;
        *) echo "Unknown option: $arg"; exit 3 ;;
    esac
done

# ─────────────────────────────────────────────────────────────
# Lockfile — prevent concurrent runs from corrupting deltas/logs
# ─────────────────────────────────────────────────────────────

readonly LOCK_FILE="${LOG_DIR}/.health-snapshot.lock"
mkdir -p "$LOG_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "Another health snapshot is already running — skipping." >&2
    exit 0
fi

# ─────────────────────────────────────────────────────────────
# Self-test mode (runs test then exits — separate from snapshot)
# ─────────────────────────────────────────────────────────────

if [[ "$RUN_SELFTEST" == true ]]; then
    # Guard: smartctl must be installed for self-test mode
    if ! command -v smartctl &>/dev/null; then
        echo "Error: smartctl not installed (need smartmontools)" >&2
        exit 3
    fi
    if [[ -z "$DEV_SDA" || ! -b "$DEV_SDA" ]]; then
        echo "Error: Internal SSD not found — cannot run SMART self-test" >&2
        exit 3
    fi
    echo "=== SMART Extended Self-Test ==="
    echo "This will take ~20 minutes. Sleep/suspend will be blocked."
    echo ""

    # Check if test already running
    CURRENT=$(smartctl -c "$DEV_SDA" 2>/dev/null | grep "remaining")
    if [[ -n "$CURRENT" ]]; then
        REMAIN=$(echo "$CURRENT" | grep -oP '[0-9]+%')
        echo "A test is already running (${REMAIN} remaining)."
        echo "Waiting for completion..."
        systemd-inhibit --what=sleep --who="smartctl" \
            --why="SMART self-test in progress" --mode=block \
            bash -c "
                while true; do
                    R=\$(smartctl -c $DEV_SDA 2>/dev/null | grep 'remaining' | grep -oP '[0-9]+%')
                    if [ -z \"\$R\" ]; then
                        echo ''
                        echo 'Test complete!'
                        smartctl -l selftest $DEV_SDA
                        break
                    else
                        echo \"\$(date +%H:%M:%S) — \${R} remaining...\"
                        sleep 60
                    fi
                done
            "
    else
        echo "Starting extended test on ${DEV_SDA}..."
        systemd-inhibit --what=sleep --who="smartctl" \
            --why="SMART extended self-test" --mode=block \
            bash -c "
                smartctl -t long $DEV_SDA
                echo 'Test started. Polling every 60 seconds...'
                echo ''
                sleep 30
                while true; do
                    R=\$(smartctl -c $DEV_SDA 2>/dev/null | grep 'remaining' | grep -oP '[0-9]+%')
                    if [ -z \"\$R\" ]; then
                        echo ''
                        echo 'Test complete!'
                        smartctl -l selftest $DEV_SDA
                        break
                    else
                        echo \"\$(date +%H:%M:%S) — \${R} remaining...\"
                        sleep 60
                    fi
                done
            "
    fi
    exit 0
fi

# ─────────────────────────────────────────────────────────────
# Core functions
# ─────────────────────────────────────────────────────────────

WARNINGS=()
CRITICAL=()

log() {
    echo "$1" >> "$LOG_FILE"
    [[ "$QUIET" == false ]] && echo "$1"
}

tlog() {
    local plain="$1" colored="$2"
    echo "$plain" >> "$LOG_FILE"
    [[ "$QUIET" == false ]] && echo -e "$colored"
}

section() {
    local bar="══════════════════════════════════════════════════════════════"
    tlog "" ""
    tlog "$bar" "${BLD}${bar}${RST}"
    tlog "  $1" "  ${BLD}$1${RST}"
    tlog "$bar" "${BLD}${bar}${RST}"
}

ok()   { tlog "  ✔ $1" "  ${GRN}✔ $1${RST}"; }
warn() { WARNINGS+=("$1"); tlog "  ⚠ WARNING: $1" "  ${YLW}⚠ WARNING: $1${RST}"; }
crit() { CRITICAL+=("$1");  tlog "  ✖ CRITICAL: $1" "  ${RED}✖ CRITICAL: $1${RST}"; }
info() { log "  · $1"; }

# Padded info for SMART sections — label padded to 18 chars
pinfo() {
    local label="$1" value="$2"
    log "  · $(printf '%-18s' "$label")${value}"
}

# Delta tracking — persistent key-value store for trend detection
# Returns empty string (not error) when file missing or key not found
delta_read() {
    local key="$1"
    if [[ -f "$DELTA_FILE" ]]; then
        grep "^${key}=" "$DELTA_FILE" 2>/dev/null | tail -1 | cut -d= -f2 || true
    fi
}

DELTA_TMP=""
delta_write() {
    local key="$1" val="$2"
    DELTA_TMP=$(mktemp "${DELTA_FILE}.XXXXXX")
    if [[ -f "$DELTA_FILE" ]]; then
        grep -v "^${key}=" "$DELTA_FILE" > "$DELTA_TMP" 2>/dev/null || true
    else
        : > "$DELTA_TMP"
    fi
    echo "${key}=${val}" >> "$DELTA_TMP"
    mv -f "$DELTA_TMP" "$DELTA_FILE"
    DELTA_TMP=""
}

# Compare current vs previous value, flag if growing
delta_check() {
    local label="$1" key="$2" current="$3" level="${4:-warn}"
    local prev
    prev=$(delta_read "$key")
    if [[ -n "$prev" && -n "$current" && "$current" =~ ^[0-9]+$ && "$prev" =~ ^[0-9]+$ ]]; then
        local delta=$((current - prev))
        if [[ $delta -gt 0 ]]; then
            if [[ "$level" == "crit" ]]; then
                crit "${label} INCREASED by ${delta} since last check (${prev} → ${current})"
            else
                warn "${label} INCREASED by ${delta} since last check (${prev} → ${current})"
            fi
            delta_write "$key" "$current"
            return 1
        else
            ok "${label} stable at ${current}"
        fi
    fi
    [[ -n "$current" ]] && delta_write "$key" "$current"
    return 0
}

# ─────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────

mkdir -p "$LOG_DIR"

# Pre-check: verify log directory is writable before proceeding
if ! touch "${LOG_FILE}" 2>/dev/null; then
    echo "Error: Cannot write to ${LOG_DIR} — check permissions or disk space" >&2
    exit 3
fi

# Initialize cross-section variables to safe defaults so set -u won't
# crash in email/append sections when a drive is disconnected or a
# tool is missing
SDA_HEALTH="" SDA_TEMP="" SDA_WEAR="" SDA_REALLOC="" SDA_ATA_ERRORS=""
SDB_HEALTH="" SDB_TEMP="" SDB_SPARE="" SDB_USED=""
GPU_TEMP="" GPU_PSTATE=""

log "System Health Snapshot"
log "$(date '+%A %B %d, %Y — %I:%M:%S %p %Z')"
log "Host: $(hostname) | Kernel: $(uname -r)"
log "Uptime: $(uptime -p)"

# ═════════════════════════════════════════════════════════════
# 1. SMART — Internal SSD
# ═════════════════════════════════════════════════════════════

section "$SDA_LABEL"

if command -v smartctl &>/dev/null && [[ -b "$DEV_SDA" ]]; then
    SDA_RAW=$(smartctl -a "$DEV_SDA" 2>&1) || true

    # Overall health
    SDA_HEALTH=$(echo "$SDA_RAW" | grep -i "SMART overall-health" | awk -F': ' '{print $2}' | xargs)
    if [[ "$SDA_HEALTH" == "PASSED" ]]; then
        ok "Overall health: PASSED"
    else
        crit "Overall health: ${SDA_HEALTH:-UNKNOWN}"
    fi

    # Parse SMART attributes by ID
    sda_attr() { echo "$SDA_RAW" | awk -v id="$1" '$1 == id {print $NF}'; }

    SDA_REALLOC=$(sda_attr 5)
    SDA_HOURS=$(sda_attr 9)
    SDA_CYCLES=$(sda_attr 12)
    SDA_WEAR=$(sda_attr 177)
    SDA_UNCORRECT=$(sda_attr 198)
    SDA_REPORTED=$(sda_attr 187)
    SDA_POWERLOSS=$(sda_attr 174)
    SDA_TEMP=$(echo "$SDA_RAW" | awk '$1 == 194 {for(i=10;i<=NF;i++){if($i~/^[0-9]+$/){print $i; exit}}}')
    SDA_WRITES=$(sda_attr 241)
    SDA_READS=$(sda_attr 242)
    SDA_MIN_ERASE=$(sda_attr 168)
    SDA_MAX_ERASE=$(sda_attr 169)
    SDA_PROG_FAIL=$(sda_attr 171)
    SDA_ERASE_FAIL=$(sda_attr 172)
    SDA_ATA_ERRORS=$(echo "$SDA_RAW" | grep "ATA Error Count:" | awk '{print $4}')

    pinfo "Power-on:"         "${SDA_HOURS:-?}h | ${SDA_CYCLES:-?} cycles"
    pinfo "Temperature:"      "${SDA_TEMP:-?}°C"
    pinfo "Total writes:"     "${SDA_WRITES:-?} GB | reads: ${SDA_READS:-?} GB"
    pinfo "Wear leveling:"    "${SDA_WEAR:-?} avg cycles (min ${SDA_MIN_ERASE:-?} / max ${SDA_MAX_ERASE:-?})"
    pinfo "Reallocated:"      "${SDA_REALLOC:-?} sectors"
    pinfo "Offline uncorrect:" "${SDA_UNCORRECT:-?}"
    pinfo "Reported uncorrect:" "${SDA_REPORTED:-?}"
    pinfo "ATA errors:"       "${SDA_ATA_ERRORS:-?} (cumulative)"
    pinfo "Unexpected power:" "${SDA_POWERLOSS:-?} losses"
    pinfo "Program fails:"    "${SDA_PROG_FAIL:-?} | Erase fails: ${SDA_ERASE_FAIL:-?}"

    # ── Delta checks (trend detection) ──
    delta_check "Reallocated sectors" "sda.realloc" "$SDA_REALLOC" "crit"
    delta_check "ATA error count" "sda.ata_errors" "$SDA_ATA_ERRORS" "warn"
    delta_check "Offline uncorrectable" "sda.uncorrect" "$SDA_UNCORRECT" "crit"
    delta_check "Reported uncorrectable" "sda.reported" "$SDA_REPORTED" "warn"

    # ── Absolute threshold checks ──
    [[ -n "$SDA_REALLOC" && "$SDA_REALLOC" -ge "$THRESH_REALLOC" ]] \
        && warn "Reallocated sectors (${SDA_REALLOC}) ≥ threshold (${THRESH_REALLOC})"
    [[ -n "$SDA_UNCORRECT" && "$SDA_UNCORRECT" -ge "$THRESH_UNCORRECT" ]] \
        && crit "Offline uncorrectable (${SDA_UNCORRECT}) ≥ threshold (${THRESH_UNCORRECT})"
    [[ -n "$SDA_WEAR" && "$SDA_WEAR" -ge "$THRESH_WEAR" ]] \
        && warn "Wear leveling (${SDA_WEAR}) approaching end-of-life (${THRESH_WEAR})"

    # ── Self-test result ──
    SELFTEST_LINE=$(smartctl -l selftest "$DEV_SDA" 2>/dev/null | grep "^#  *1" || true)
    if [[ -n "$SELFTEST_LINE" ]]; then
        if echo "$SELFTEST_LINE" | grep -qi "completed without error"; then
            ok "Last self-test: PASSED"
        elif echo "$SELFTEST_LINE" | grep -qi "error\|fail"; then
            crit "Last SMART self-test reported errors"
        elif echo "$SELFTEST_LINE" | grep -qi "aborted"; then
            warn "Last SMART self-test was aborted (use --selftest to re-run)"
        fi
    fi
else
    warn "smartctl not available or ${DEV_SDA} not found"
fi

# ═════════════════════════════════════════════════════════════
# 2. SMART — External NVMe
# ═════════════════════════════════════════════════════════════

section "$SDB_LABEL"

if command -v smartctl &>/dev/null && [[ -b "$DEV_SDB" ]]; then
    SDB_RAW=$(smartctl -a "$DEV_SDB" 2>&1) || true
    SDB_HEALTH=$(echo "$SDB_RAW" | grep -i "SMART overall-health" | awk -F': ' '{print $2}' | xargs)

    if [[ "$SDB_HEALTH" == "PASSED" ]]; then
        ok "Overall health: PASSED"
    elif [[ -z "$SDB_HEALTH" ]]; then
        warn "Could not read SMART data (drive may be disconnected)"
    else
        crit "Overall health: ${SDB_HEALTH}"
    fi

    # NVMe health info parsing
    nvme_val() { echo "$SDB_RAW" | grep "^${1}:" | head -1 | awk -F': *' '{print $2}' | tr -d '% ,'; }

    SDB_TEMP=$(echo "$SDB_RAW" | grep "^Temperature:" | head -1 | grep -oP '[0-9]+' | head -1)
    SDB_SPARE=$(nvme_val "Available Spare")
    SDB_USED=$(nvme_val "Percentage Used")
    SDB_HOURS=$(nvme_val "Power On Hours")
    SDB_CYCLES=$(nvme_val "Power Cycles")
    SDB_UNSAFE=$(nvme_val "Unsafe Shutdowns")
    SDB_MEDIA_ERR=$(echo "$SDB_RAW" | grep "Media and Data Integrity Errors:" | awk '{print $NF}')
    SDB_ERR_LOG=$(echo "$SDB_RAW" | grep "Error Information Log Entries:" | awk '{print $NF}')

    pinfo "Temperature:"      "${SDB_TEMP:-?}°C"
    pinfo "Available spare:"  "${SDB_SPARE:-?}%"
    pinfo "Percentage used:"  "${SDB_USED:-?}%"
    pinfo "Power-on:"         "${SDB_HOURS:-?}h | ${SDB_CYCLES:-?} cycles"
    pinfo "Unsafe shutdowns:" "${SDB_UNSAFE:-?}"
    pinfo "Media errors:"     "${SDB_MEDIA_ERR:-?}"
    pinfo "Error log entries:" "${SDB_ERR_LOG:-?}"

    [[ -n "$SDB_SPARE" && "$SDB_SPARE" -le "$THRESH_NVME_SPARE" ]] \
        && crit "Available spare (${SDB_SPARE}%) ≤ threshold (${THRESH_NVME_SPARE}%)"
    [[ -n "$SDB_USED" && "$SDB_USED" -ge "$THRESH_NVME_USED" ]] \
        && warn "Percentage used (${SDB_USED}%) ≥ threshold (${THRESH_NVME_USED}%)"
    [[ -n "$SDB_MEDIA_ERR" && "$SDB_MEDIA_ERR" -gt 0 ]] \
        && crit "Media integrity errors detected: ${SDB_MEDIA_ERR}"

    delta_check "NVMe media errors" "sdb.media_errors" "$SDB_MEDIA_ERR" "crit"
    delta_check "NVMe error log" "sdb.err_log" "$SDB_ERR_LOG" "warn"
else
    info "Drive not connected — skipping"
fi

# ═════════════════════════════════════════════════════════════
# 3. GPU — NVIDIA GTX 1060 Mobile
# ═════════════════════════════════════════════════════════════

section "GPU: NVIDIA GTX 1060 Mobile 6GB"

if command -v nvidia-smi &>/dev/null; then
    GPU_CSV=$(nvidia-smi \
        --query-gpu=temperature.gpu,power.draw,memory.used,memory.total,pstate,fan.speed,clocks.gr,clocks.mem \
        --format=csv,noheader,nounits 2>&1) || true

    # Validate CSV has expected 8 fields before parsing
    GPU_FIELD_COUNT=$(echo "$GPU_CSV" | tr -cd ',' | wc -c)
    if [[ -n "$GPU_CSV" && ! "$GPU_CSV" =~ "Failed" && ! "$GPU_CSV" =~ "error" && "$GPU_FIELD_COUNT" -ge 7 ]]; then
        IFS=',' read -r GPU_TEMP GPU_POWER GPU_VRAM_USED GPU_VRAM_TOTAL \
                       GPU_PSTATE GPU_FAN GPU_CLK GPU_MCLK <<< "$GPU_CSV"
        # Trim whitespace
        GPU_TEMP="${GPU_TEMP// /}"; GPU_POWER="${GPU_POWER// /}"
        GPU_VRAM_USED="${GPU_VRAM_USED// /}"; GPU_VRAM_TOTAL="${GPU_VRAM_TOTAL// /}"
        GPU_PSTATE="${GPU_PSTATE// /}"; GPU_FAN="${GPU_FAN// /}"
        GPU_CLK="${GPU_CLK// /}"; GPU_MCLK="${GPU_MCLK// /}"

        pinfo "Temperature:"      "${GPU_TEMP}°C"
        pinfo "Power draw:"       "${GPU_POWER} W"
        pinfo "VRAM:"             "${GPU_VRAM_USED} / ${GPU_VRAM_TOTAL} MiB"
        pinfo "Perf state:"       "${GPU_PSTATE}"
        pinfo "Fan:"              "${GPU_FAN}%"
        pinfo "Clocks:"           "${GPU_CLK} MHz core / ${GPU_MCLK} MHz mem"

        if [[ "$GPU_TEMP" =~ ^[0-9]+$ && "$GPU_TEMP" -ge "$THRESH_GPU_TEMP" ]]; then
            warn "GPU temperature (${GPU_TEMP}°C) ≥ threshold (${THRESH_GPU_TEMP}°C)"
        else
            ok "GPU temperature: ${GPU_TEMP}°C"
        fi
    else
        warn "nvidia-smi query failed: ${GPU_CSV}"
    fi

    # Check for NVIDIA XID errors (hardware faults) in kernel log
    XID_COUNT=$(dmesg 2>/dev/null | grep -c "NVRM: Xid" || true)
    if [[ "$XID_COUNT" -gt 0 ]]; then
        warn "NVIDIA XID errors in dmesg: ${XID_COUNT} (possible GPU hardware issue)"
        dmesg 2>/dev/null | grep "NVRM: Xid" | tail -3 | while read -r line; do
            info "  ${line}"
        done
    else
        ok "No NVIDIA XID errors in dmesg"
    fi

    # GPU switching mode
    if command -v supergfxctl &>/dev/null; then
        GPU_MODE=$(supergfxctl -g 2>/dev/null || echo "unknown")
        pinfo "supergfxctl mode:" "${GPU_MODE}"
    fi
else
    warn "nvidia-smi not found"
fi

# ═════════════════════════════════════════════════════════════
# 4. CPU & Thermals
# ═════════════════════════════════════════════════════════════

section "CPU & Thermals (i7-7700HQ)"

PKG_TEMP=""

if command -v sensors &>/dev/null; then
    SENSORS_OUT=$(sensors 2>&1) || true

    # Package temperature
    PKG_TEMP=$(echo "$SENSORS_OUT" | grep "Package id 0:" | grep -oP '\+\K[0-9.]+' | head -1)
    if [[ -n "$PKG_TEMP" ]]; then
        pinfo "Package temp:"    "${PKG_TEMP}°C"
        PKG_INT=${PKG_TEMP%.*}
        if [[ "$PKG_INT" -ge "$THRESH_CPU_TEMP" ]]; then
            warn "CPU package temp (${PKG_TEMP}°C) ≥ threshold (${THRESH_CPU_TEMP}°C)"
        else
            ok "CPU temperature: ${PKG_TEMP}°C"
        fi
    fi

    # Per-core temps — skip if no core lines found
    CORE_LINES=$(echo "$SENSORS_OUT" | grep "Core " || true)
    if [[ -n "$CORE_LINES" ]]; then
        while IFS= read -r line; do
            [[ -z "$line" ]] && continue
            CORE_NAME=$(echo "$line" | cut -d: -f1 | xargs)
            CORE_TEMP=$(echo "$line" | grep -oP '\+\K[0-9.]+' | head -1)
            pinfo "${CORE_NAME}:" "${CORE_TEMP:-?}°C"
        done <<< "$CORE_LINES"
    fi

    # Fan speeds
    FAN_LINE=$(echo "$SENSORS_OUT" | grep -i "fan" | head -1)
    [[ -n "$FAN_LINE" ]] && info "Fan: ${FAN_LINE}"
else
    # Fallback: sysfs thermal zones
    for tz in /sys/class/thermal/thermal_zone*/; do
        [[ -f "${tz}type" && -f "${tz}temp" ]] || continue
        TZ_TYPE=$(cat "${tz}type" 2>/dev/null || true)
        TZ_TEMP=$(cat "${tz}temp" 2>/dev/null || true)
        [[ -n "$TZ_TEMP" ]] && info "${TZ_TYPE}: $((TZ_TEMP / 1000))°C"
    done
    warn "lm-sensors not available (using sysfs thermal zones)"
fi

# ═════════════════════════════════════════════════════════════
# 5. Storage & ZRAM
# ═════════════════════════════════════════════════════════════

section "Storage & ZRAM"

# ── Filesystem usage ──
log "  Filesystem usage:"

# Collect disk warnings outside subshell
DISK_WARNS_TMP=$(mktemp)
df -h --output=target,size,used,avail,pcent -x tmpfs -x devtmpfs -x efivarfs -x overlay 2>/dev/null | \
while IFS= read -r line; do
    info "  $line"
    PCT=$(echo "$line" | awk '{print $NF}' | tr -d '%')
    MOUNT=$(echo "$line" | awk '{print $1}')
    if [[ "$PCT" =~ ^[0-9]+$ && "$PCT" -ge "$THRESH_DISK_PCT" ]]; then
        echo "${MOUNT}:${PCT}" >> "$DISK_WARNS_TMP"
    fi
done
if [[ -s "$DISK_WARNS_TMP" ]]; then
    while IFS=: read -r mount pct; do
        warn "Disk usage on ${mount} is ${pct}% (threshold: ${THRESH_DISK_PCT}%)"
    done < "$DISK_WARNS_TMP"
fi
rm -f "$DISK_WARNS_TMP"

# ── Inode usage (sneaky failure mode) ──
log ""
log "  Inode usage:"
INODE_OUT=$(df -i --output=target,itotal,iused,iavail,ipcent / /boot 2>/dev/null || true)
if [[ -n "$INODE_OUT" ]]; then
    while IFS= read -r line; do
        info "  $line"
    done <<< "$INODE_OUT"
else
    info "  (inode data not available)"
fi

# ── ZRAM ──
log ""
log "  ZRAM swap:"
if [[ -f /sys/block/zram0/mm_stat ]]; then
    read -r ORIG COMP MEM _ _ _ _ <<< "$(cat /sys/block/zram0/mm_stat)"
    ORIG_MB=$((ORIG / 1048576))
    COMP_MB=$((COMP / 1048576))
    MEM_MB=$((MEM / 1048576))
    if [[ "$ORIG_MB" -eq 0 || "$COMP_MB" -eq 0 ]]; then
        RATIO="N/A (no swap pressure)"
    else
        RATIO=$(echo "scale=2; $ORIG / $COMP" | bc 2>/dev/null || echo "?")
    fi

    info "Original: ${ORIG_MB} MB | Compressed: ${COMP_MB} MB | Mem used: ${MEM_MB} MB"
    if [[ "$RATIO" =~ ^[0-9] ]]; then
        info "Compression ratio: ${RATIO}:1"
    else
        info "Compression ratio: ${RATIO}"
    fi

    ZRAM_TOTAL=$(cat /sys/block/zram0/disksize 2>/dev/null || echo 0)
    if [[ "$ZRAM_TOTAL" -gt 0 ]]; then
        ZRAM_PCT=$((ORIG * 100 / ZRAM_TOTAL))
        ZRAM_TOTAL_MB=$((ZRAM_TOTAL / 1048576))
        info "ZRAM utilization: ${ZRAM_PCT}% of ${ZRAM_TOTAL_MB} MB"
        [[ "$ZRAM_PCT" -ge "$THRESH_ZRAM_PCT" ]] \
            && warn "ZRAM usage (${ZRAM_PCT}%) ≥ threshold (${THRESH_ZRAM_PCT}%)"
    fi
else
    info "ZRAM stats not available"
fi

# ── Swappiness sanity check ──
SWAPPINESS=$(cat /proc/sys/vm/swappiness 2>/dev/null || echo "?")
info "vm.swappiness: ${SWAPPINESS}"
[[ "$SWAPPINESS" != "180" ]] && warn "vm.swappiness is ${SWAPPINESS}, expected 180 for Bazzite ZRAM"

# ── TRIM status ──
TRIM_STATUS=$(systemctl is-active fstrim.timer 2>/dev/null || echo "unknown")
info "fstrim.timer: ${TRIM_STATUS}"

# ═════════════════════════════════════════════════════════════
# 6. Key Services
# ═════════════════════════════════════════════════════════════

section "Key Services"

svc_check() {
    local svc="$1" label="$2" required="${3:-true}"
    local state
    state=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    if [[ "$state" == "active" ]]; then
        ok "${label}: active"
    elif [[ "$required" == true ]]; then
        warn "${label} (${svc}): ${state}"
    else
        info "${label}: ${state} (optional)"
    fi
}

svc_check "firewalld.service"          "Firewall"            true
svc_check "clamav-freshclam.service"   "ClamAV signatures"   true
svc_check "supergfxd.service"          "GPU switching"       true
svc_check "thermald.service"           "Thermal management"  true
svc_check "systemd-resolved.service"   "DNS resolver"        true
svc_check "usbguard.service"           "USB guard"           true
svc_check "fstrim.timer"               "SSD TRIM timer"      true
svc_check "system-health.timer"        "Health snapshot timer" true
svc_check "smartd.service"             "SMART monitoring"    false

# SELinux
SELINUX=$(getenforce 2>/dev/null || echo "unknown")
if [[ "$SELINUX" == "Enforcing" ]]; then
    ok "SELinux: Enforcing"
else
    warn "SELinux: ${SELINUX} (expected Enforcing)"
fi

# Firewall zone
FW_ZONE=$(firewall-cmd --get-default-zone 2>/dev/null || echo "unknown")
if [[ "$FW_ZONE" == "drop" ]]; then
    ok "Firewall zone: drop"
else
    warn "Firewall zone: ${FW_ZONE} (expected drop)"
fi

# ═════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════

section "SUMMARY"

TOTAL_ISSUES=$(( ${#WARNINGS[@]} + ${#CRITICAL[@]} ))

if [[ ${#CRITICAL[@]} -gt 0 ]]; then
    STATUS="CRITICAL"
    EXIT_CODE=2
    tlog "  Status: ✖ CRITICAL — ${#CRITICAL[@]} critical, ${#WARNINGS[@]} warnings" \
         "  ${RED}${BLD}Status: ✖ CRITICAL — ${#CRITICAL[@]} critical, ${#WARNINGS[@]} warnings${RST}"
elif [[ ${#WARNINGS[@]} -gt 0 ]]; then
    STATUS="WARNING"
    EXIT_CODE=1
    tlog "  Status: ⚠ WARNING — ${#WARNINGS[@]} issue(s) detected" \
         "  ${YLW}${BLD}Status: ⚠ WARNING — ${#WARNINGS[@]} issue(s) detected${RST}"
else
    STATUS="OK"
    EXIT_CODE=0
    tlog "  Status: ✔ ALL OK — No issues detected" \
         "  ${GRN}${BLD}Status: ✔ ALL OK — No issues detected${RST}"
fi

if [[ ${#CRITICAL[@]} -gt 0 ]]; then
    log ""; log "  Critical:"
    for c in "${CRITICAL[@]}"; do tlog "    ✖ $c" "    ${RED}✖ $c${RST}"; done
fi
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    log ""; log "  Warnings:"
    for w in "${WARNINGS[@]}"; do tlog "    ⚠ $w" "    ${YLW}⚠ $w${RST}"; done
fi

log ""
log "  Log: ${LOG_FILE}"
log "  Completed: $(date '+%I:%M:%S %p %Z')"

# ── Reprint executive summary to terminal ──
if [[ "$QUIET" == false ]]; then
    echo ""
    if [[ "$STATUS" == "CRITICAL" ]]; then
        echo -e "${RED}${BLD}━━━ ✖ CRITICAL — ${#CRITICAL[@]} critical, ${#WARNINGS[@]} warnings ━━━${RST}"
    elif [[ "$STATUS" == "WARNING" ]]; then
        echo -e "${YLW}${BLD}━━━ ⚠ WARNING — ${#WARNINGS[@]} issue(s) detected ━━━${RST}"
    else
        echo -e "${GRN}${BLD}━━━ ✔ ALL OK — No issues detected ━━━${RST}"
    fi
fi

# Symlink latest
ln -sf "$LOG_FILE" "$LATEST_LINK"

# ═════════════════════════════════════════════════════════════
# Update tray status (~/security/.status)
# ═════════════════════════════════════════════════════════════

if [[ -d "$(dirname "$STATUS_FILE")" ]]; then
    python3 -c '
import json, os, sys
path = sys.argv[1]
try:
    with open(path, "r") as f:
        st = json.load(f)
except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
    st = {}

st["health_status"]     = sys.argv[2]
st["health_issues"]     = int(sys.argv[3])
st["health_warnings"]   = int(sys.argv[4])
st["health_critical"]   = int(sys.argv[5])
st["health_last_check"] = sys.argv[6]
st["health_log"]        = sys.argv[7]

import tempfile
tmp = None
try:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        json.dump(st, f, indent=2)
    os.rename(tmp, path)
except OSError:
    if tmp:
        try:
            os.unlink(tmp)
        except OSError:
            pass
' "$STATUS_FILE" "$STATUS" "$TOTAL_ISSUES" "${#WARNINGS[@]}" "${#CRITICAL[@]}" \
        "$(date '+%Y-%m-%d %I:%M %p')" "$LOG_FILE" \
        2>/dev/null || true
    chown lch:lch "$STATUS_FILE" 2>/dev/null || true
fi

# ═════════════════════════════════════════════════════════════
# Output modes
# ═════════════════════════════════════════════════════════════

if [[ "$APPEND_MODE" == true ]]; then
    # Compact summary for embedding in ClamAV scan emails
    echo ""
    echo "── System Health ──────────────────────────────"
    if [[ "$STATUS" == "OK" ]]; then
        echo "✔ All systems healthy"
    else
        echo "Status: ${STATUS} — ${TOTAL_ISSUES} issue(s)"
        for c in "${CRITICAL[@]}"; do echo "  ✖ $c"; done
        for w in "${WARNINGS[@]}"; do echo "  ⚠ $w"; done
    fi
    echo "SDA: ${SDA_TEMP:-?}°C | Wear: ${SDA_WEAR:-?} | Realloc: ${SDA_REALLOC:-?} | ATA: ${SDA_ATA_ERRORS:-?}"
    [[ -b "$DEV_SDB" ]] && echo "SDB: ${SDB_TEMP:-?}°C | Spare: ${SDB_SPARE:-?}% | Used: ${SDB_USED:-?}%"
    echo "GPU: ${GPU_TEMP:-?}°C | CPU: ${PKG_TEMP:-?}°C"
    echo "───────────────────────────────────────────────"
fi

# ═════════════════════════════════════════════════════════════
# Email alert
# ═════════════════════════════════════════════════════════════

if [[ "$APPEND_MODE" == false && ( "$SEND_EMAIL" == true || "$STATUS" != "OK" ) ]]; then
    if [[ -f "$MSMTPRC" ]]; then
        EMAIL_TO=$(grep "^from" "$MSMTPRC" | awk '{print $2}')
        if [[ -n "$EMAIL_TO" ]]; then
            SUBJECT="[Bazzite Health] ${STATUS} — $(date '+%b %d %I:%M %p')"

            case "$STATUS" in
                CRITICAL) COLOR="#dc3545"; ICON="🔴" ;;
                WARNING)  COLOR="#ffc107"; ICON="🟡" ;;
                *)        COLOR="#28a745"; ICON="🟢" ;;
            esac

            # shellcheck disable=SC2015
            {
                echo "Subject: ${SUBJECT}"
                echo "Content-Type: text/html; charset=utf-8"
                echo "From: ${EMAIL_TO}"
                echo "To: ${EMAIL_TO}"
                echo ""
                cat <<HTMLEOF
<html><body style="font-family: 'Cascadia Code', monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px;">
<div style="max-width: 620px; margin: 0 auto;">
<h2 style="color: ${COLOR};">${ICON} System Health: ${STATUS}</h2>
<p style="color: #888;">$(date '+%A %B %d, %Y — %I:%M %p %Z') | $(hostname)</p>
<hr style="border-color: #333;">

<h3 style="color: #7eb8da;">💾 Drive Health</h3>
<table style="border-collapse: collapse; width: 100%; font-size: 13px;">
<tr style="background: #2a2a4a;">
  <th style="padding: 8px; text-align: left; color: #aaa;">Drive</th>
  <th style="padding: 8px; color: #aaa;">Health</th>
  <th style="padding: 8px; color: #aaa;">Temp</th>
  <th style="padding: 8px; color: #aaa;">Key Metric</th>
</tr>
<tr>
  <td style="padding: 8px;">sda (hynix 256G)</td>
  <td style="padding: 8px;">${SDA_HEALTH:-?}</td>
  <td style="padding: 8px;">${SDA_TEMP:-?}°C</td>
  <td style="padding: 8px;">Wear: ${SDA_WEAR:-?} | Realloc: ${SDA_REALLOC:-?} | ATA: ${SDA_ATA_ERRORS:-?}</td>
</tr>
$(if [[ -b "$DEV_SDB" ]]; then cat <<SDB_ROW
<tr>
  <td style="padding: 8px;">sdb (WD 2TB NVMe)</td>
  <td style="padding: 8px;">${SDB_HEALTH:-?}</td>
  <td style="padding: 8px;">${SDB_TEMP:-?}°C</td>
  <td style="padding: 8px;">Spare: ${SDB_SPARE:-?}% | Used: ${SDB_USED:-?}%</td>
</tr>
SDB_ROW
fi)
</table>

<h3 style="color: #7eb8da;">🌡 Thermals</h3>
<p>GPU: ${GPU_TEMP:-?}°C (${GPU_PSTATE:-?}) | CPU: ${PKG_TEMP:-?}°C</p>

$(if [[ $TOTAL_ISSUES -gt 0 ]]; then
    echo "<h3 style=\"color: ${COLOR};\">⚡ Issues (${TOTAL_ISSUES})</h3><ul>"
    for c in "${CRITICAL[@]}"; do echo "<li style=\"color: #dc3545;\">✖ ${c}</li>"; done
    for w in "${WARNINGS[@]}"; do echo "<li style=\"color: #ffc107;\">⚠ ${w}</li>"; done
    echo "</ul>"
fi)

<hr style="border-color: #333;">
<p style="color: #555; font-size: 11px;">Log: ${LOG_FILE} | Uptime: $(uptime -p)</p>
</div></body></html>
HTMLEOF
            } | msmtp --file="$MSMTPRC" "$EMAIL_TO" 2>/dev/null && {
                [[ "$QUIET" == false ]] && log "  Email sent to ${EMAIL_TO}"
            } || {
                [[ "$QUIET" == false ]] && log "  Email send failed (check msmtp)"
            }
        fi
    fi
fi

exit "$EXIT_CODE"
