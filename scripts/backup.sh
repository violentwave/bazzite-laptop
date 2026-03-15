#!/bin/bash
# shellcheck disable=SC2015
# backup.sh — Flat backup of entire Bazzite laptop state to USB flash drive
# Deploy to: /mnt/backup/backup.sh (on BazziteBackup partition)
# Usage: sudo bash /mnt/backup/backup.sh
# Creates /mnt/backup/latest/ with everything organized by clear naming
set -uo pipefail

# --- Configuration ---
# Dynamic device lookup — avoids hardcoded /dev/sdX that changes with device ordering
FLASH_DEV=$(findfs LABEL=BazziteBackup 2>/dev/null) || FLASH_DEV=""
MOUNT_POINT="/mnt/backup"
BACKUP_DIR="${MOUNT_POINT}/latest"
LUKS_REDUNDANT="${MOUNT_POINT}/luks-header-backup"
HOME_DIR="/home/lch"
MIN_FREE_GB=5
ERRORS=0
WARNINGS=0

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
ok()   { echo -e "  ${GREEN}[OK]${RESET} $1"; }
warn() { echo -e "  ${BYELLOW}[!!]${RESET} $1"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo -e "  ${RED}[FAIL]${RESET} $1"; ERRORS=$((ERRORS + 1)); }
info() { echo -e "  ${DIM}$1${RESET}"; }
phase() {
    echo ""
    echo -e "  ${BCYAN}$1${RESET}"
    echo ""
}

separator() {
    echo ""
    echo -e "  ${DIM}----------------------------------------------${RESET}"
    echo ""
}

# Use rsync if available, otherwise cp -a
COPY_CMD="cp -a"
command -v rsync &>/dev/null && COPY_CMD="rsync"

# Copy helper: uses rsync when available, falls back to cp -a
safe_copy() {
    local src="$1"
    local dst="$2"
    shift 2
    local extra_flags=("$@")

    if [[ "$COPY_CMD" == "rsync" ]]; then
        rsync -a --info=progress2 "${extra_flags[@]}" "$src" "$dst" 2>&1 || {
            fail "Failed to copy ${src}"
            return 1
        }
    else
        cp -a "$src" "$dst" 2>&1 || {
            fail "Failed to copy ${src}"
            return 1
        }
    fi
    return 0
}

# Copy a single file if it exists
copy_file() {
    local src="$1"
    local dst="$2"
    local label="${3:-$(basename "$dst")}"
    if [[ -f "$src" ]]; then
        mkdir -p "$(dirname "$dst")"
        cp -a "$src" "$dst" 2>/dev/null && ok "$label" || fail "$label"
    else
        warn "$label not found at ${src}"
    fi
}

# Copy a directory if it exists
copy_dir() {
    local src="$1"
    local dst="$2"
    local label="${3:-$(basename "$dst")/}"
    shift 3 2>/dev/null || true
    local extra_flags=("$@")
    if [[ -d "$src" ]]; then
        mkdir -p "$dst"
        safe_copy "${src}/" "$dst" "${extra_flags[@]}" && ok "$label" || fail "$label"
    else
        warn "$label not found at ${src}"
    fi
}

# Get free space on flash drive in GB
get_free_gb() {
    df --output=avail -BG "$MOUNT_POINT" 2>/dev/null | tail -1 | tr -d ' G'
}

# Get directory size in human readable
dir_size() {
    du -sh "$1" 2>/dev/null | awk '{print $1}' || echo "?"
}

# Count files in directory
file_count() {
    find "$1" -type f 2>/dev/null | wc -l || echo "0"
}

# --- Must run as root ---
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root (sudo).${RESET}"
    echo "Usage: sudo bash /mnt/backup/backup.sh"
    exit 1
fi

# ===========================
# BANNER
# ===========================
echo ""
echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE BACKUP${RESET}                 ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}│${RESET}  ${DIM}System Backup · $(date '+%b %d, %Y %I:%M %p')${RESET} ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"

# ===========================
# PRE-FLIGHT: FLASH DRIVE
# ===========================
phase "PRE-FLIGHT CHECKS"

if [[ -z "$FLASH_DEV" || ! -b "$FLASH_DEV" ]]; then
    echo -e "  ${BRED}BazziteBackup partition not found.${RESET}"
    echo ""
    echo -ne "  ${BYELLOW}Plug in the flash drive and press Enter (or Ctrl+C to abort): ${RESET}"
    read -r
    FLASH_DEV=$(findfs LABEL=BazziteBackup 2>/dev/null) || FLASH_DEV=""
    if [[ -z "$FLASH_DEV" || ! -b "$FLASH_DEV" ]]; then
        fail "BazziteBackup partition still not found. Aborting."
        exit 1
    fi
fi
ok "${FLASH_DEV} found (label: BazziteBackup)"

# Mount if not already mounted
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    ok "${MOUNT_POINT} already mounted"
else
    info "Mounting ${FLASH_DEV} to ${MOUNT_POINT}..."
    mkdir -p "$MOUNT_POINT"
    if mount "$FLASH_DEV" "$MOUNT_POINT" 2>&1; then
        ok "Mounted ${FLASH_DEV} to ${MOUNT_POINT}"
    else
        fail "Could not mount ${FLASH_DEV}. Aborting."
        exit 1
    fi
fi

FREE_GB=$(get_free_gb)
info "Free space on flash drive: ${FREE_GB}GB"

separator

# ===========================
# PREPARE BACKUP DIRECTORY
# ===========================
phase "PREPARING BACKUP DIRECTORY"

if [[ -d "$BACKUP_DIR" ]]; then
    info "Removing old latest/..."
    rm -rf "$BACKUP_DIR"
    ok "Removed old latest/"
fi

mkdir -p "$BACKUP_DIR"
ok "Created fresh latest/"

separator

# ===========================
# CRITICAL FILES
# ===========================
phase "CRITICAL FILES"

# LUKS header backup
if compgen -G "${HOME_DIR}/security/luks-backup/luks-header-"*.bak >/dev/null 2>&1; then
    LUKS_SRC=$(find "${HOME_DIR}/security/luks-backup/" -name "luks-header-*.bak" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    cp -a "$LUKS_SRC" "${BACKUP_DIR}/luks-header.bak" \
        && { chmod 400 "${BACKUP_DIR}/luks-header.bak"; chown root:root "${BACKUP_DIR}/luks-header.bak"; ok "luks-header.bak (from ${LUKS_SRC})"; } \
        || fail "luks-header.bak"
else
    info "No existing LUKS header backup found, creating one..."
    # Dynamic device lookup for LUKS partition
    LUKS_PART=$(blkid -U "luks-ec338b68-2489-477e-bd89-592d308f450c" 2>/dev/null) || LUKS_PART=""
    if [[ -n "$LUKS_PART" ]] && cryptsetup luksHeaderBackup "$LUKS_PART" --header-backup-file "${BACKUP_DIR}/luks-header.bak" 2>/dev/null; then
        chmod 400 "${BACKUP_DIR}/luks-header.bak"
        chown root:root "${BACKUP_DIR}/luks-header.bak"
        ok "luks-header.bak (fresh from ${LUKS_PART})"
    else
        warn "Could not back up LUKS header — LUKS partition not found or cryptsetup failed"
    fi
fi

# Kernel args
cat /proc/cmdline > "${BACKUP_DIR}/cmdline.txt" 2>/dev/null && ok "cmdline.txt" || fail "cmdline.txt"

# rpm-ostree status
rpm-ostree status > "${BACKUP_DIR}/rpm-ostree-status.txt" 2>/dev/null && ok "rpm-ostree-status.txt" || fail "rpm-ostree-status.txt"

# Flatpak list
flatpak list --app --columns=application > "${BACKUP_DIR}/flatpak-list.txt" 2>/dev/null && ok "flatpak-list.txt" || fail "flatpak-list.txt"

# Enabled services
systemctl list-unit-files --state=enabled --no-pager > "${BACKUP_DIR}/enabled-services.txt" 2>/dev/null && ok "enabled-services.txt" || fail "enabled-services.txt"

# Disabled services (ones we intentionally disabled)
{
    echo "# Services intentionally disabled for security hardening"
    echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    for svc in avahi-daemon.service avahi-daemon.socket ModemManager.service sssd.service sssd-kcm.socket mdmonitor.service qemu-guest-agent.service raid-check.timer; do
        state=$(systemctl is-enabled "$svc" 2>/dev/null || echo "not-found")
        printf "%-40s %s\n" "$svc" "$state"
    done
    echo ""
    echo "# Wildcard groups:"
    for pattern in 'virt*' 'vbox*' 'vmtools*' 'vgauth*' 'iscsi*'; do
        systemctl list-unit-files "$pattern" --no-pager 2>/dev/null | grep -v "^$" | grep -v "^UNIT" | grep -v "unit files listed"
    done
} > "${BACKUP_DIR}/disabled-services.txt" 2>/dev/null && ok "disabled-services.txt" || fail "disabled-services.txt"

# Firewall rules
firewall-cmd --list-all > "${BACKUP_DIR}/firewall-rules.txt" 2>/dev/null && ok "firewall-rules.txt" || fail "firewall-rules.txt"

# Firewall log-denied setting
firewall-cmd --get-log-denied > "${BACKUP_DIR}/firewall-log-denied.txt" 2>/dev/null && ok "firewall-log-denied.txt" || fail "firewall-log-denied.txt"

# Open ports
ss -tlnp > "${BACKUP_DIR}/open-ports.txt" 2>/dev/null && ok "open-ports.txt" || fail "open-ports.txt"

# DNS status
resolvectl status > "${BACKUP_DIR}/dns-status.txt" 2>/dev/null && ok "dns-status.txt" || fail "dns-status.txt"

# Backup timestamp
date '+%Y-%m-%d %H:%M:%S' > "${BACKUP_DIR}/backup-timestamp.txt"
hostname >> "${BACKUP_DIR}/backup-timestamp.txt"
ok "backup-timestamp.txt"

separator

# ===========================
# SYSTEM CONFIGS FROM /etc/
# ===========================
phase "SYSTEM CONFIGS (/etc/)"

copy_file "/etc/gamemode.ini" "${BACKUP_DIR}/etc-gamemode.ini"
copy_file "/etc/environment" "${BACKUP_DIR}/etc-environment"
copy_file "/etc/freshclam.conf" "${BACKUP_DIR}/etc-freshclam.conf"

# USBGuard rules
if [[ -f "/etc/usbguard/rules.conf" ]]; then
    cp -a "/etc/usbguard/rules.conf" "${BACKUP_DIR}/etc-usbguard-rules.conf" && ok "etc-usbguard-rules.conf" || fail "etc-usbguard-rules.conf"
else
    warn "etc-usbguard-rules.conf not found (USBGuard may not be configured)"
fi

# Directory copies
copy_dir "/etc/systemd/resolved.conf.d" "${BACKUP_DIR}/resolved.conf.d" "resolved.conf.d/"
copy_dir "/etc/sysctl.d" "${BACKUP_DIR}/sysctl.d" "sysctl.d/"
copy_dir "/etc/udev/rules.d" "${BACKUP_DIR}/rules.d" "rules.d/"
copy_dir "/etc/firewalld" "${BACKUP_DIR}/firewalld" "firewalld/"

# Systemd units (clamav timers and services)
mkdir -p "${BACKUP_DIR}/systemd-units"
for unit in /etc/systemd/system/clamav-*.timer /etc/systemd/system/clamav-*.service \
            /etc/systemd/system/system-health.service /etc/systemd/system/system-health.timer; do
    [[ -f "$unit" ]] && cp -a "$unit" "${BACKUP_DIR}/systemd-units/" 2>/dev/null
done
UNIT_COUNT=$(find "${BACKUP_DIR}/systemd-units" -type f 2>/dev/null | wc -l)
if [[ "$UNIT_COUNT" -gt 0 ]]; then
    ok "systemd-units/ (${UNIT_COUNT} files)"
else
    warn "No systemd units found in /etc/systemd/system/"
fi

# Logrotate
if [[ -f "/etc/logrotate.d/clamav-scans" ]]; then
    cp -a "/etc/logrotate.d/clamav-scans" "${BACKUP_DIR}/logrotate-clamav-scans" && ok "logrotate-clamav-scans" || fail "logrotate-clamav-scans"
else
    warn "logrotate-clamav-scans not found"
fi
if [[ -f "/etc/logrotate.d/system-health" ]]; then
    cp -a "/etc/logrotate.d/system-health" "${BACKUP_DIR}/logrotate-system-health" && ok "logrotate-system-health" || fail "logrotate-system-health"
else
    warn "logrotate-system-health not found"
fi

separator

# ===========================
# SCRIPTS
# ===========================
phase "SCRIPTS (/usr/local/bin/)"

if [[ -d "/usr/local/bin" ]] && [[ -n "$(ls -A /usr/local/bin/ 2>/dev/null)" ]]; then
    mkdir -p "${BACKUP_DIR}/scripts"
    cp -a /usr/local/bin/* "${BACKUP_DIR}/scripts/" 2>/dev/null && ok "scripts/ (from /usr/local/bin/)" || fail "scripts/"
else
    warn "/usr/local/bin/ is empty or doesn't exist"
fi

separator

# ===========================
# USER CONFIGS
# ===========================
phase "USER CONFIGS"

# msmtprc (restrict permissions — contains email credentials)
copy_file "${HOME_DIR}/.msmtprc" "${BACKUP_DIR}/msmtprc"
chmod 600 "${BACKUP_DIR}/msmtprc" 2>/dev/null

# MangoHud
copy_dir "${HOME_DIR}/.config/MangoHud" "${BACKUP_DIR}/MangoHud" "MangoHud/"

# Claude Code settings
if [[ -d "${HOME_DIR}/.claude" ]]; then
    mkdir -p "${BACKUP_DIR}/dot-claude"
    # Copy settings files, not the entire directory (skip ephemeral data)
    for f in settings.json settings.local.json; do
        [[ -f "${HOME_DIR}/.claude/${f}" ]] && cp -a "${HOME_DIR}/.claude/${f}" "${BACKUP_DIR}/dot-claude/" 2>/dev/null
    done
    # Copy projects directory if it exists
    [[ -d "${HOME_DIR}/.claude/projects" ]] && cp -a "${HOME_DIR}/.claude/projects" "${BACKUP_DIR}/dot-claude/" 2>/dev/null
    ok "dot-claude/"
else
    # shellcheck disable=SC2088
    warn "~/.claude/ not found"
fi

# KDE Security menu files
mkdir -p "${BACKUP_DIR}/kde-security-menu"
for desktop_file in "${HOME_DIR}/.local/share/applications/security-"*.desktop; do
    [[ -f "$desktop_file" ]] && cp -a "$desktop_file" "${BACKUP_DIR}/kde-security-menu/" 2>/dev/null
done
if [[ -f "${HOME_DIR}/.config/menus/applications-merged/security.menu" ]]; then
    cp -a "${HOME_DIR}/.config/menus/applications-merged/security.menu" "${BACKUP_DIR}/kde-security-menu/" 2>/dev/null
fi
if [[ -f "${HOME_DIR}/.local/share/desktop-directories/security-directory.desktop" ]]; then
    cp -a "${HOME_DIR}/.local/share/desktop-directories/security-directory.desktop" "${BACKUP_DIR}/kde-security-menu/" 2>/dev/null
fi
MENU_COUNT=$(find "${BACKUP_DIR}/kde-security-menu" -type f 2>/dev/null | wc -l)
ok "kde-security-menu/ (${MENU_COUNT} files)"

# Entire ~/security/ folder
copy_dir "${HOME_DIR}/security" "${BACKUP_DIR}/security" "security/" --exclude=".status.tmp"

separator

# ===========================
# GAME SAVES (compatdata)
# ===========================
phase "GAME SAVES (Steam compatdata)"

COMPATDATA="${HOME_DIR}/.local/share/Steam/steamapps/compatdata"

if [[ -d "$COMPATDATA" ]]; then
    COMPAT_SIZE_HUMAN=$(dir_size "$COMPATDATA")
    info "compatdata size: ${COMPAT_SIZE_HUMAN}"

    FREE_GB=$(get_free_gb)
    if [[ "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
        warn "Only ${FREE_GB}GB free — skipping compatdata (need ${MIN_FREE_GB}GB free)"
    else
        mkdir -p "${BACKUP_DIR}/compatdata"
        info "Copying compatdata (this may take a while)..."
        safe_copy "${COMPATDATA}/" "${BACKUP_DIR}/compatdata/" \
            --exclude="__pycache__" --exclude="*.pyc" --exclude="*.tmp" --exclude=".cache" \
            && ok "compatdata/ (${COMPAT_SIZE_HUMAN})" \
            || fail "compatdata/"
    fi
else
    warn "Steam compatdata not found at ${COMPATDATA}"
fi

separator

# ===========================
# FLATPAK DATA
# ===========================
phase "FLATPAK DATA (~/.var/app/)"

FLATPAK_DATA="${HOME_DIR}/.var/app"

if [[ -d "$FLATPAK_DATA" ]]; then
    FLATPAK_SIZE_HUMAN=$(dir_size "$FLATPAK_DATA")
    # shellcheck disable=SC2088
    info "~/.var/app/ size: ${FLATPAK_SIZE_HUMAN}"

    FREE_GB=$(get_free_gb)
    if [[ "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
        warn "Only ${FREE_GB}GB free — skipping flatpak data (need ${MIN_FREE_GB}GB free)"
    else
        mkdir -p "${BACKUP_DIR}/flatpak-data"
        info "Copying flatpak data (excluding caches, this may take a while)..."
        safe_copy "${FLATPAK_DATA}/" "${BACKUP_DIR}/flatpak-data/" \
            --exclude="*/cache/*" --exclude="*/Cache/*" --exclude="*/.cache/*" \
            --exclude="*/Code Cache/*" --exclude="*/GPUCache/*" --exclude="*/ShaderCache/*" \
            --exclude="__pycache__" --exclude="*.pyc" --exclude="*.tmp" \
            && ok "flatpak-data/ (cache excluded)" \
            || fail "flatpak-data/"
    fi
else
    # shellcheck disable=SC2088
    warn "~/.var/app/ not found"
fi

separator

# ===========================
# PROJECT FILES
# ===========================
phase "PROJECT FILES (~/projects/bazzite-laptop/)"

if [[ -d "${HOME_DIR}/projects/bazzite-laptop" ]]; then
    copy_dir "${HOME_DIR}/projects/bazzite-laptop" "${BACKUP_DIR}/bazzite-laptop" "bazzite-laptop/" \
        --exclude=".git" --exclude="__pycache__" --exclude="*.pyc" --exclude="*.tmp" --exclude=".cache"
else
    # shellcheck disable=SC2088
    warn "~/projects/bazzite-laptop/ not found"
fi

separator

# ===========================
# REDUNDANT LUKS HEADER COPY
# ===========================
phase "REDUNDANT LUKS HEADER COPY"

mkdir -p "$LUKS_REDUNDANT"
if [[ -f "${BACKUP_DIR}/luks-header.bak" ]]; then
    cp -a "${BACKUP_DIR}/luks-header.bak" "${LUKS_REDUNDANT}/luks-header.bak" 2>/dev/null \
        && { chmod 400 "${LUKS_REDUNDANT}/luks-header.bak"; chown root:root "${LUKS_REDUNDANT}/luks-header.bak"; ok "Redundant LUKS header saved to ${LUKS_REDUNDANT}/"; } \
        || fail "Could not copy redundant LUKS header"
else
    warn "No LUKS header to copy"
fi

separator

# ===========================
# SUMMARY
# ===========================
phase "BACKUP SUMMARY"

TOTAL_SIZE=$(dir_size "$BACKUP_DIR")
TOTAL_COUNT=$(file_count "$BACKUP_DIR")
FREE_GB=$(get_free_gb)

echo -e "  ${BGREEN}┌─────────────────────────────────────────────┐${RESET}"
echo -e "  ${BGREEN}│${RESET}  ${BWHITE}BACKUP COMPLETE${RESET}                              ${BGREEN}│${RESET}"
echo -e "  ${BGREEN}└─────────────────────────────────────────────┘${RESET}"
echo ""
echo -e "  ${BWHITE}Total files:${RESET}  ${TOTAL_COUNT}"
echo -e "  ${BWHITE}Total size:${RESET}   ${TOTAL_SIZE}"
echo -e "  ${BWHITE}Free space:${RESET}   ${FREE_GB}GB remaining on flash drive"
echo -e "  ${BWHITE}Location:${RESET}     ${BACKUP_DIR}/"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo -e "  ${RED}Errors: ${ERRORS}${RESET}  |  ${YELLOW}Warnings: ${WARNINGS}${RESET}"
    echo -e "  ${DIM}Review errors above. Re-run to retry failed items.${RESET}"
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "  ${YELLOW}Warnings: ${WARNINGS}${RESET} (no errors)"
    echo -e "  ${DIM}Warnings are usually missing optional files — check above.${RESET}"
else
    echo -e "  ${GREEN}No errors or warnings.${RESET}"
fi

echo ""
echo -e "  ${DIM}Flash drive was NOT unmounted. When done:${RESET}"
echo -e "  ${DIM}  sudo umount ${MOUNT_POINT}${RESET}"
echo ""
