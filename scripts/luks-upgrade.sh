#!/bin/bash
# luks-upgrade.sh — Guided LUKS KDF upgrade from PBKDF2 to Argon2id
# For: /dev/sda3 (LUKS UUID: luks-ec338b68-2489-477e-bd89-592d308f450c)
# This is a ONE-TIME guide script. It explains each step and asks for confirmation.
# Run manually: chmod +x luks-upgrade.sh && sudo ./luks-upgrade.sh
set -uo pipefail

# --- Configuration ---
# Source device UUIDs from central config (keeps identifiers out of git history)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UUID_CONF="${SCRIPT_DIR}/../configs/device-uuids.conf"
if [[ -f "$UUID_CONF" ]]; then
    # shellcheck source=../configs/device-uuids.conf
    source "$UUID_CONF"
else
    # Fallback to deployed location
    UUID_CONF="/etc/bazzite-security/device-uuids.conf"
    if [[ -f "$UUID_CONF" ]]; then
        source "$UUID_CONF"
    else
        echo "Error: device-uuids.conf not found" >&2
        exit 1
    fi
fi
# Dynamic device lookup — avoids hardcoded /dev/sdX that changes with device ordering
# Note: color vars not yet defined, so use plain echo for early-exit error
LUKS_DEVICE=$(blkid -U "$LUKS_UUID" 2>/dev/null) || {
    echo "Error: LUKS device with UUID ${LUKS_UUID} not found. Is the drive connected?" >&2
    exit 1
}
BACKUP_DIR="/home/lch/security/luks-backup"
BACKUP_FILE="${BACKUP_DIR}/luks-header-$(date +%Y%m%d).bak"

# --- Audit logging ---
AUDIT_LOG="/var/log/security-audit.log"
audit_log() {
    local msg="$1"
    local log_dir
    log_dir=$(dirname "$AUDIT_LOG")
    if [[ ! -d "$log_dir" ]]; then
        mkdir -p "$log_dir" 2>/dev/null || {
            echo "audit_log: cannot create ${log_dir}" >&2
            return
        }
    fi
    if [[ -e "$AUDIT_LOG" && ! -w "$AUDIT_LOG" ]]; then
        echo "audit_log: ${AUDIT_LOG} is not writable" >&2
        return
    fi
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    local user="${SUDO_USER:-$(whoami)}"
    echo "${ts} [luks-upgrade] [${user}] ${msg}" >> "$AUDIT_LOG"
}

# --- Colors ---
BCYAN='\e[1;36m'
GREEN='\e[0;32m'
BGREEN='\e[1;32m'
RED='\e[0;31m'
BRED='\e[1;31m'
YELLOW='\e[0;33m'
BYELLOW='\e[1;33m'
BWHITE='\e[1;37m'
DIM='\e[2m'
RESET='\e[0m'

# --- Helpers ---
abort() {
    echo ""
    echo -e "  ${BRED}ABORTED:${RESET} $1"
    echo ""
    exit 1
}

success() {
    echo -e "  ${GREEN}[OK]${RESET} $1"
}

warn() {
    echo -e "  ${BYELLOW}[!!]${RESET} $1"
}

fail() {
    echo -e "  ${RED}[FAIL]${RESET} $1"
}

info() {
    echo -e "  ${DIM}$1${RESET}"
}

confirm() {
    local prompt="$1"
    echo ""
    echo -e "  ${BYELLOW}${prompt}${RESET}"
    echo -ne "  ${BWHITE}Type 'yes' to continue: ${RESET}"
    read -r answer
    if [[ "$answer" != "yes" ]]; then
        abort "User did not confirm. No changes were made."
    fi
}

separator() {
    echo ""
    echo -e "  ${DIM}──────────────────────────────────────────────${RESET}"
    echo ""
}

# --- Must run as root ---
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root (sudo).${RESET}"
    echo "Usage: sudo ./luks-upgrade.sh"
    exit 1
fi

# ===========================
# BANNER
# ===========================
echo ""
echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}LUKS UPGRADE${RESET}                   ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}│${RESET}  ${DIM}LUKS KDF Upgrade · PBKDF2 → Argon2id${RESET}${BCYAN}│${RESET}"
echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"
echo ""
echo -e "  ${DIM}This script will guide you through upgrading the key derivation${RESET}"
echo -e "  ${DIM}function on your LUKS-encrypted internal SSD from PBKDF2 to${RESET}"
echo -e "  ${DIM}Argon2id, which is more resistant to GPU-based brute force attacks.${RESET}"
echo ""
echo -e "  ${DIM}Device: ${LUKS_DEVICE}${RESET}"
echo -e "  ${DIM}UUID:   ${LUKS_UUID}${RESET}"
audit_log "Script started — LUKS device resolved to ${LUKS_DEVICE} (UUID: ${LUKS_UUID})"
separator

# ===========================
# PRE-FLIGHT CHECKS
# ===========================
echo -e "  ${BCYAN}PRE-FLIGHT CHECKS${RESET}"
echo ""

# Check device exists
if [[ -b "$LUKS_DEVICE" ]]; then
    success "${LUKS_DEVICE} exists"
else
    fail "${LUKS_DEVICE} does not exist"
    abort "LUKS device not found. Is the drive connected?"
fi

# Check it's a LUKS device
if cryptsetup isLuks "$LUKS_DEVICE" 2>/dev/null; then
    success "${LUKS_DEVICE} is a LUKS device"
else
    fail "${LUKS_DEVICE} is NOT a LUKS device"
    abort "Device is not LUKS-encrypted. Wrong partition?"
fi

# Show current LUKS info
echo ""
echo -e "  ${BWHITE}Current LUKS header:${RESET}"
echo ""
cryptsetup luksDump "$LUKS_DEVICE" 2>/dev/null | head -20 | while IFS= read -r line; do
    echo -e "    ${DIM}${line}${RESET}"
done

# Check current KDF
echo ""
CURRENT_KDF=$(cryptsetup luksDump "$LUKS_DEVICE" 2>/dev/null | grep -i "PBKDF:" | head -1 | awk '{print $2}')

if [[ -z "$CURRENT_KDF" ]]; then
    # LUKS1 doesn't show PBKDF: line the same way
    CURRENT_KDF=$(cryptsetup luksDump "$LUKS_DEVICE" 2>/dev/null | grep -i "MK iterations:" | head -1)
    if [[ -n "$CURRENT_KDF" ]]; then
        info "Detected LUKS1 format (uses PBKDF2 by default)"
        CURRENT_KDF="pbkdf2"
    else
        warn "Could not determine current KDF"
        CURRENT_KDF="unknown"
    fi
fi

echo -e "  ${BWHITE}Current KDF:${RESET} ${CURRENT_KDF}"
audit_log "KDF check: current KDF is ${CURRENT_KDF}"

if [[ "${CURRENT_KDF,,}" == "argon2id" ]]; then
    echo ""
    success "Already using Argon2id — no upgrade needed!"
    audit_log "Already using Argon2id — no upgrade needed, exiting"
    echo ""
    echo -e "  ${DIM}Your LUKS encryption is already using the recommended KDF.${RESET}"
    echo -e "  ${DIM}No changes are necessary.${RESET}"
    echo ""
    exit 0
fi

# Check disk space for header backup (LUKS2 headers are typically ~16MB)
AVAIL_KB=$(df --output=avail /home/lch 2>/dev/null | tail -1 | tr -d ' ')
if [[ -n "$AVAIL_KB" ]] && (( AVAIL_KB > 20480 )); then
    success "Sufficient disk space for header backup (${AVAIL_KB}K available)"
else
    warn "Low disk space — header backup needs ~16MB"
fi

separator

# ===========================
# STEP 1 — LUKS HEADER BACKUP
# ===========================
echo -e "  ${BCYAN}STEP 1 — LUKS HEADER BACKUP${RESET}"
echo ""
echo -e "  ${BWHITE}Before making any changes, we must back up the LUKS header.${RESET}"
echo ""
echo -e "  ${DIM}This backup allows you to restore the LUKS header if anything${RESET}"
echo -e "  ${DIM}goes wrong during the upgrade. Without it, data recovery would${RESET}"
echo -e "  ${DIM}be impossible if the header is corrupted.${RESET}"
echo ""
echo -e "  ${DIM}Command: cryptsetup luksHeaderBackup ${LUKS_DEVICE} \\${RESET}"
echo -e "  ${DIM}         --header-backup-file ${BACKUP_FILE}${RESET}"

confirm "Create LUKS header backup now?"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create the backup
echo ""
echo -e "  ${YELLOW}Backing up LUKS header...${RESET}"

if cryptsetup luksHeaderBackup "$LUKS_DEVICE" --header-backup-file "$BACKUP_FILE" 2>&1; then
    # Verify backup exists and is non-zero
    if [[ -f "$BACKUP_FILE" ]] && [[ -s "$BACKUP_FILE" ]]; then
        BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || echo "unknown")
        success "Header backup created: ${BACKUP_FILE} (${BACKUP_SIZE} bytes)"
        # Restrict permissions — this file can unlock the drive
        chmod 400 "$BACKUP_FILE"
        success "Backup permissions set to read-only (400)"
    else
        fail "Backup file is empty or missing"
        abort "Header backup failed. No changes have been made to your drive."
    fi
else
    fail "cryptsetup luksHeaderBackup failed"
    abort "Header backup failed. No changes have been made to your drive."
fi

echo ""
echo -e "  ${BRED}┌─────────────────────────────────────────────────────────────────┐${RESET}"
echo -e "  ${BRED}│${RESET}  ${BRED}WARNING: CRITICAL BACKUP${RESET}                                       ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}                                                                  ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  Store a copy of this backup on a ${BWHITE}separate physical drive${RESET}.      ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  If the LUKS header is corrupted and you don't have this         ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  backup, ${BRED}ALL DATA ON THE INTERNAL DRIVE IS PERMANENTLY LOST${RESET}.     ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}                                                                  ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  Backup location: ${DIM}${BACKUP_FILE}${RESET}  ${BRED}│${RESET}"
echo -e "  ${BRED}└─────────────────────────────────────────────────────────────────┘${RESET}"

confirm "I understand. I will copy this backup to a separate physical drive."

separator

# ===========================
# STEP 2 — UPGRADE KDF TO ARGON2ID
# ===========================
echo -e "  ${BCYAN}STEP 2 — UPGRADE KDF TO ARGON2ID${RESET}"
echo ""
echo -e "  ${BWHITE}What this does:${RESET}"
echo -e "  ${DIM}Converts the key derivation function from PBKDF2 to Argon2id.${RESET}"
echo -e "  ${DIM}Argon2id is memory-hard, making it significantly more resistant${RESET}"
echo -e "  ${DIM}to GPU-based and ASIC-based brute force attacks on your passphrase.${RESET}"
echo ""
echo -e "  ${DIM}Command: cryptsetup luksConvertKey ${LUKS_DEVICE} --pbkdf argon2id${RESET}"
echo ""
echo -e "  ${YELLOW}You will be prompted to enter your LUKS passphrase.${RESET}"

confirm "Upgrade KDF to Argon2id now? (This modifies the LUKS header)"

echo ""
echo -e "  ${YELLOW}Converting key slot to Argon2id...${RESET}"
echo ""

if cryptsetup luksConvertKey "$LUKS_DEVICE" --pbkdf argon2id; then
    echo ""
    success "KDF successfully upgraded to Argon2id"
    audit_log "KDF upgrade SUCCESS — converted to Argon2id on ${LUKS_DEVICE}"
else
    echo ""
    fail "luksConvertKey failed"
    audit_log "KDF upgrade FAILED — luksConvertKey returned error on ${LUKS_DEVICE}"
    echo ""
    echo -e "  ${YELLOW}The upgrade did not complete. Your drive should still work with${RESET}"
    echo -e "  ${YELLOW}the existing PBKDF2 key. If you have issues, restore the header:${RESET}"
    echo -e "  ${DIM}  sudo cryptsetup luksHeaderRestore ${LUKS_DEVICE} \\${RESET}"
    echo -e "  ${DIM}       --header-backup-file ${BACKUP_FILE}${RESET}"
    echo ""
    exit 1
fi

separator

# ===========================
# POST-UPGRADE VERIFICATION
# ===========================
echo -e "  ${BCYAN}POST-UPGRADE VERIFICATION${RESET}"
echo ""

# Show updated LUKS info
echo -e "  ${BWHITE}Updated LUKS header:${RESET}"
echo ""
cryptsetup luksDump "$LUKS_DEVICE" 2>/dev/null | head -20 | while IFS= read -r line; do
    echo -e "    ${DIM}${line}${RESET}"
done

# Verify Argon2id is active
echo ""
NEW_KDF=$(cryptsetup luksDump "$LUKS_DEVICE" 2>/dev/null | grep -i "PBKDF:" | head -1)

if echo "$NEW_KDF" | grep -qi "argon2id"; then
    success "Verified: Argon2id is now active"
    echo -e "    ${DIM}${NEW_KDF}${RESET}"
else
    warn "Could not verify Argon2id in LUKS dump"
    echo -e "    ${DIM}PBKDF line: ${NEW_KDF:-not found}${RESET}"
    echo -e "  ${YELLOW}Run 'sudo cryptsetup luksDump ${LUKS_DEVICE} | grep -i pbkdf' to check manually.${RESET}"
fi

separator

# ===========================
# SUMMARY
# ===========================
echo -e "  ${BGREEN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BGREEN}│${RESET}  ${BWHITE}UPGRADE COMPLETE${RESET}                     ${BGREEN}│${RESET}"
echo -e "  ${BGREEN}└──────────────────────────────────────┘${RESET}"
echo ""
echo -e "  ${BWHITE}What was done:${RESET}"
echo -e "  ${GREEN}[1]${RESET} LUKS header backed up to:"
echo -e "      ${DIM}${BACKUP_FILE}${RESET}"
echo -e "  ${GREEN}[2]${RESET} KDF upgraded from PBKDF2 to Argon2id"
echo -e "      ${DIM}Device: ${LUKS_DEVICE}${RESET}"
echo ""
echo -e "  ${BYELLOW}Reminder:${RESET} Copy the header backup to a separate physical drive:"
echo -e "  ${DIM}  cp ${BACKUP_FILE} /mnt/backup/${RESET}"
echo ""
echo -e "  ${DIM}Your system will use the new KDF at next boot when you enter${RESET}"
echo -e "  ${DIM}your LUKS passphrase. No further action is needed.${RESET}"
audit_log "Script completed successfully"
echo ""
