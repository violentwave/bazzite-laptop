#!/bin/bash
# update-backup.sh — Comprehensive system state backup to USB flash drive
# Captures the entire Bazzite laptop configuration in layered structure
# Usage: sudo ./update-backup.sh
# Flash drive: /dev/sdc3 mounted at /mnt/backup
# Safe to run multiple times (idempotent). Rotates one previous backup.
set -uo pipefail

# --- Configuration ---
FLASH_DEV="/dev/sdc3"
MOUNT_POINT="/mnt/backup"
BACKUP_DIR="${MOUNT_POINT}/latest"
PREVIOUS_DIR="${MOUNT_POINT}/previous"
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
if command -v rsync &>/dev/null; then
    COPY_CMD="rsync"
fi

# Copy helper: uses rsync with progress when available, falls back to cp -a
# Usage: safe_copy <src> <dst> [extra rsync flags...]
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
    if [[ -f "$src" ]]; then
        mkdir -p "$(dirname "$dst")"
        cp -a "$src" "$dst" 2>/dev/null && ok "$(basename "$src")" || fail "$(basename "$src")"
    else
        warn "$(basename "$src") not found at ${src}"
    fi
}

# Copy a directory if it exists
copy_dir() {
    local src="$1"
    local dst="$2"
    shift 2
    local extra_flags=("$@")
    if [[ -d "$src" ]]; then
        mkdir -p "$dst"
        safe_copy "${src}/" "$dst" "${extra_flags[@]}" && ok "$(basename "$src")/" || fail "$(basename "$src")/"
    else
        warn "$(basename "$src")/ not found at ${src}"
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
    echo "Usage: sudo ./update-backup.sh"
    exit 1
fi

# ===========================
# BANNER
# ===========================
echo ""
echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE SECURITY SCANNER${RESET}       ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}│${RESET}  ${DIM}System Backup · $(date '+%b %d, %Y %I:%M %p')${RESET} ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"

# ===========================
# PRE-FLIGHT: FLASH DRIVE
# ===========================
phase "PRE-FLIGHT CHECKS"

# Check if device exists
if [[ ! -b "$FLASH_DEV" ]]; then
    echo -e "  ${BRED}Flash drive ${FLASH_DEV} not found.${RESET}"
    echo ""
    echo -ne "  ${BYELLOW}Plug in the flash drive and press Enter (or Ctrl+C to abort): ${RESET}"
    read -r
    if [[ ! -b "$FLASH_DEV" ]]; then
        fail "${FLASH_DEV} still not found. Aborting."
        exit 1
    fi
fi
ok "${FLASH_DEV} found"

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
# ROTATE BACKUPS
# ===========================
phase "ROTATING BACKUPS"

if [[ -d "$BACKUP_DIR" ]]; then
    info "Moving latest/ -> previous/..."
    # Remove old previous if it exists
    if [[ -d "$PREVIOUS_DIR" ]]; then
        rm -rf "$PREVIOUS_DIR"
        info "Removed old previous/"
    fi
    mv "$BACKUP_DIR" "$PREVIOUS_DIR"
    ok "Rotated latest/ to previous/"
else
    info "No existing latest/ to rotate"
fi

mkdir -p "$BACKUP_DIR"
ok "Created fresh latest/"

separator

# ===========================
# LAYER 1 — CRITICAL
# ===========================
phase "LAYER 1 — CRITICAL (LUKS header, kernel args, packages)"

LAYER1="${BACKUP_DIR}/layer1-critical"
mkdir -p "$LAYER1"

# LUKS header backup
if [[ -f "${HOME_DIR}/security/luks-backup/luks-header-"*.bak ]]; then
    LUKS_SRC=$(ls -t "${HOME_DIR}/security/luks-backup/luks-header-"*.bak 2>/dev/null | head -1)
    cp -a "$LUKS_SRC" "${LAYER1}/luks-header.bak" && ok "luks-header.bak (from ${LUKS_SRC})" || fail "luks-header.bak"
else
    # Try generating fresh
    info "No existing LUKS header backup found, creating one..."
    if cryptsetup luksHeaderBackup /dev/sda3 --header-backup-file "${LAYER1}/luks-header.bak" 2>/dev/null; then
        ok "luks-header.bak (fresh from /dev/sda3)"
    else
        warn "Could not back up LUKS header — cryptsetup failed"
    fi
fi

# Kernel args
cat /proc/cmdline > "${LAYER1}/kernel-args.txt" 2>/dev/null && ok "kernel-args.txt" || fail "kernel-args.txt"

# Layered packages
rpm-ostree status > "${LAYER1}/layered-packages.txt" 2>/dev/null && ok "layered-packages.txt" || fail "layered-packages.txt"

# Flatpak list
flatpak list --app --columns=application > "${LAYER1}/flatpak-list.txt" 2>/dev/null && ok "flatpak-list.txt" || fail "flatpak-list.txt"

L1_SIZE=$(dir_size "$LAYER1")
L1_COUNT=$(file_count "$LAYER1")
info "Layer 1: ${L1_COUNT} files, ${L1_SIZE}"

separator

# ===========================
# LAYER 2 — /etc/ CONFIGS
# ===========================
phase "LAYER 2 — SYSTEM CONFIGS (/etc/)"

LAYER2="${BACKUP_DIR}/layer2-etc"
mkdir -p "$LAYER2"

copy_file "/etc/gamemode.ini" "${LAYER2}/gamemode.ini"
copy_file "/etc/environment" "${LAYER2}/environment"
copy_dir "/etc/udev/rules.d" "${LAYER2}/udev-rules"
copy_dir "/etc/sysctl.d" "${LAYER2}/sysctl"

# Systemd units (clamav timers and services)
mkdir -p "${LAYER2}/systemd-units"
for unit in /etc/systemd/system/clamav-*.timer /etc/systemd/system/clamav-*.service; do
    [[ -f "$unit" ]] && cp -a "$unit" "${LAYER2}/systemd-units/" 2>/dev/null
done
UNIT_COUNT=$(find "${LAYER2}/systemd-units" -type f 2>/dev/null | wc -l)
if [[ "$UNIT_COUNT" -gt 0 ]]; then
    ok "systemd-units/ (${UNIT_COUNT} files)"
else
    warn "No clamav systemd units found in /etc/systemd/system/"
fi

# Logrotate
mkdir -p "${LAYER2}/logrotate"
if [[ -f "/etc/logrotate.d/clamav-scans" ]]; then
    cp -a "/etc/logrotate.d/clamav-scans" "${LAYER2}/logrotate/" && ok "logrotate/clamav-scans" || fail "logrotate/clamav-scans"
else
    warn "logrotate/clamav-scans not found"
fi

# Resolved (DNS-over-TLS)
copy_dir "/etc/systemd/resolved.conf.d" "${LAYER2}/resolved"

# freshclam.conf
copy_file "/etc/freshclam.conf" "${LAYER2}/freshclam.conf"

# USBGuard rules
if [[ -f "/etc/usbguard/rules.conf" ]]; then
    cp -a "/etc/usbguard/rules.conf" "${LAYER2}/usbguard-rules.conf" && ok "usbguard-rules.conf" || fail "usbguard-rules.conf"
else
    warn "usbguard-rules.conf not found (USBGuard may not be configured yet)"
fi

# Firewalld
copy_dir "/etc/firewalld" "${LAYER2}/firewalld"

L2_SIZE=$(dir_size "$LAYER2")
L2_COUNT=$(file_count "$LAYER2")
info "Layer 2: ${L2_COUNT} files, ${L2_SIZE}"

separator

# ===========================
# LAYER 3 — SCRIPTS
# ===========================
phase "LAYER 3 — SCRIPTS (/usr/local/bin/)"

LAYER3="${BACKUP_DIR}/layer3-scripts"
mkdir -p "$LAYER3"

if [[ -d "/usr/local/bin" ]] && [[ -n "$(ls -A /usr/local/bin/ 2>/dev/null)" ]]; then
    cp -a /usr/local/bin/* "${LAYER3}/" 2>/dev/null && ok "/usr/local/bin/ contents" || fail "/usr/local/bin/"
else
    warn "/usr/local/bin/ is empty or doesn't exist"
fi

L3_SIZE=$(dir_size "$LAYER3")
L3_COUNT=$(file_count "$LAYER3")
info "Layer 3: ${L3_COUNT} files, ${L3_SIZE}"

separator

# ===========================
# LAYER 4 — USER CONFIGS
# ===========================
phase "LAYER 4 — USER CONFIGS (~/.config, ~/security)"

LAYER4="${BACKUP_DIR}/layer4-user-configs"
mkdir -p "$LAYER4"

# msmtprc
copy_file "${HOME_DIR}/.msmtprc" "${LAYER4}/msmtprc"

# MangoHud
copy_file "${HOME_DIR}/.config/MangoHud/MangoHud.conf" "${LAYER4}/MangoHud.conf"

# KDE security menu files
mkdir -p "${LAYER4}/kde-security-menu"
for desktop_file in "${HOME_DIR}/.local/share/applications/security-"*.desktop; do
    [[ -f "$desktop_file" ]] && cp -a "$desktop_file" "${LAYER4}/kde-security-menu/" 2>/dev/null
done
if [[ -f "${HOME_DIR}/.config/menus/applications-merged/security.menu" ]]; then
    cp -a "${HOME_DIR}/.config/menus/applications-merged/security.menu" "${LAYER4}/kde-security-menu/" 2>/dev/null
fi
if [[ -f "${HOME_DIR}/.local/share/desktop-directories/security-directory.desktop" ]]; then
    cp -a "${HOME_DIR}/.local/share/desktop-directories/security-directory.desktop" "${LAYER4}/kde-security-menu/" 2>/dev/null
fi
MENU_COUNT=$(find "${LAYER4}/kde-security-menu" -type f 2>/dev/null | wc -l)
ok "kde-security-menu/ (${MENU_COUNT} files)"

# Claude settings
if [[ -f "${HOME_DIR}/.claude/settings.json" ]]; then
    mkdir -p "${LAYER4}/claude-settings"
    cp -a "${HOME_DIR}/.claude/settings.json" "${LAYER4}/claude-settings/" && ok "claude-settings/" || fail "claude-settings/"
else
    warn "~/.claude/settings.json not found"
fi

# Entire ~/security/ folder
if [[ -d "${HOME_DIR}/security" ]]; then
    copy_dir "${HOME_DIR}/security" "${LAYER4}/security" --exclude=".status.tmp"
else
    warn "~/security/ not found"
fi

L4_SIZE=$(dir_size "$LAYER4")
L4_COUNT=$(file_count "$LAYER4")
info "Layer 4: ${L4_COUNT} files, ${L4_SIZE}"

separator

# ===========================
# LAYER 5 — GAME SAVES (compatdata)
# ===========================
phase "LAYER 5 — GAME SAVES (Steam compatdata)"

LAYER5="${BACKUP_DIR}/layer5-game-saves"
COMPATDATA="${HOME_DIR}/.local/share/Steam/steamapps/compatdata"

if [[ -d "$COMPATDATA" ]]; then
    COMPAT_SIZE_KB=$(du -sk "$COMPATDATA" 2>/dev/null | awk '{print $1}')
    COMPAT_SIZE_HUMAN=$(dir_size "$COMPATDATA")
    info "compatdata size: ${COMPAT_SIZE_HUMAN}"

    FREE_GB=$(get_free_gb)
    if [[ "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
        warn "Only ${FREE_GB}GB free on flash drive — skipping compatdata backup"
        warn "Need at least ${MIN_FREE_GB}GB free. Free up space and re-run."
    else
        mkdir -p "${LAYER5}/compatdata"
        info "Copying compatdata (this may take a while)..."
        safe_copy "${COMPATDATA}/" "${LAYER5}/compatdata/" \
            --exclude="__pycache__" --exclude="*.pyc" --exclude="*.tmp" \
            && ok "compatdata/ (${COMPAT_SIZE_HUMAN})" \
            || fail "compatdata/"
    fi
else
    warn "Steam compatdata not found at ${COMPATDATA}"
fi

L5_SIZE=$(dir_size "$LAYER5" 2>/dev/null || echo "0")
L5_COUNT=$(file_count "$LAYER5" 2>/dev/null || echo "0")
info "Layer 5: ${L5_COUNT} files, ${L5_SIZE}"

separator

# ===========================
# LAYER 6 — FLATPAK DATA
# ===========================
phase "LAYER 6 — FLATPAK DATA (~/.var/app/)"

LAYER6="${BACKUP_DIR}/layer6-flatpak-data"
FLATPAK_DATA="${HOME_DIR}/.var/app"

if [[ -d "$FLATPAK_DATA" ]]; then
    FLATPAK_SIZE_HUMAN=$(dir_size "$FLATPAK_DATA")
    info "~/.var/app/ size: ${FLATPAK_SIZE_HUMAN}"

    FREE_GB=$(get_free_gb)
    if [[ "$FREE_GB" -lt "$MIN_FREE_GB" ]]; then
        warn "Only ${FREE_GB}GB free on flash drive — skipping flatpak data backup"
        warn "Need at least ${MIN_FREE_GB}GB free. Free up space and re-run."
    else
        mkdir -p "${LAYER6}/var-app"
        info "Copying flatpak data (excluding caches, this may take a while)..."
        safe_copy "${FLATPAK_DATA}/" "${LAYER6}/var-app/" \
            --exclude="*/cache/*" --exclude="*/Cache/*" --exclude="*/Code Cache/*" \
            --exclude="*/GPUCache/*" --exclude="*/ShaderCache/*" \
            --exclude="__pycache__" --exclude="*.pyc" --exclude="*.tmp" \
            && ok "var-app/ (cache excluded)" \
            || fail "var-app/"
    fi
else
    warn "~/.var/app/ not found"
fi

L6_SIZE=$(dir_size "$LAYER6" 2>/dev/null || echo "0")
L6_COUNT=$(file_count "$LAYER6" 2>/dev/null || echo "0")
info "Layer 6: ${L6_COUNT} files, ${L6_SIZE}"

separator

# ===========================
# LAYER 7 — PROJECT FILES
# ===========================
phase "LAYER 7 — PROJECT FILES (~/projects/bazzite-laptop/)"

LAYER7="${BACKUP_DIR}/layer7-project"
mkdir -p "${LAYER7}"

if [[ -d "${HOME_DIR}/projects/bazzite-laptop" ]]; then
    copy_dir "${HOME_DIR}/projects/bazzite-laptop" "${LAYER7}/bazzite-laptop" \
        --exclude=".git" --exclude="__pycache__" --exclude="*.pyc" --exclude="*.tmp"
else
    warn "~/projects/bazzite-laptop/ not found"
fi

L7_SIZE=$(dir_size "$LAYER7")
L7_COUNT=$(file_count "$LAYER7")
info "Layer 7: ${L7_COUNT} files, ${L7_SIZE}"

separator

# ===========================
# LAYER 8 — RESTORE GUIDE
# ===========================
phase "LAYER 8 — GENERATING RESTORE GUIDE"

LAYER8="${BACKUP_DIR}/layer8-restore-guide"
mkdir -p "$LAYER8"

# Extract info for the restore guide
KARGS=$(cat /proc/cmdline 2>/dev/null || echo "(not available)")
LAYERED_PKGS=$(rpm-ostree status 2>/dev/null | grep -A 100 "^●" | grep "LayeredPackages:" | sed 's/.*LayeredPackages: //' || echo "(check layered-packages.txt)")
FLATPAK_APPS=$(flatpak list --app --columns=application 2>/dev/null || echo "(check flatpak-list.txt)")

cat > "${LAYER8}/RESTORE.md" << 'RESTORE_HEADER'
# Bazzite Laptop — System Restore Guide

Auto-generated restore instructions. Follow these steps IN ORDER after a fresh
Bazzite installation to restore the complete system state.

---

## Step 1: Install Layered Packages

```bash
RESTORE_HEADER

# Add actual packages
echo "rpm-ostree install ${LAYERED_PKGS}" >> "${LAYER8}/RESTORE.md"

cat >> "${LAYER8}/RESTORE.md" << 'RESTORE_STEP2'
systemctl reboot
```

Wait for reboot, then continue.

## Step 2: Restore Kernel Arguments

Current kernel arguments at time of backup:
```
RESTORE_STEP2

echo "${KARGS}" >> "${LAYER8}/RESTORE.md"

cat >> "${LAYER8}/RESTORE.md" << 'RESTORE_STEP2B'
```

To add custom kernel arguments (check what's non-default):
```bash
# Example — only add args you previously customized:
# rpm-ostree kargs --append=<key>=<value>
```

## Step 3: Restore /etc/ Configs

```bash
# Gamemode
sudo cp layer2-etc/gamemode.ini /etc/gamemode.ini

# Environment
sudo cp layer2-etc/environment /etc/environment

# Udev rules
sudo cp -a layer2-etc/udev-rules/* /etc/udev/rules.d/

# Sysctl configs
sudo cp -a layer2-etc/sysctl/* /etc/sysctl.d/
sudo sysctl --system

# DNS-over-TLS
sudo mkdir -p /etc/systemd/resolved.conf.d/
sudo cp -a layer2-etc/resolved/* /etc/systemd/resolved.conf.d/
sudo systemctl restart systemd-resolved

# freshclam config
sudo cp layer2-etc/freshclam.conf /etc/freshclam.conf

# Firewalld (restore custom zones/rules)
sudo cp -a layer2-etc/firewalld/* /etc/firewalld/
sudo firewall-cmd --reload

# USBGuard rules (if applicable)
# sudo cp layer2-etc/usbguard-rules.conf /etc/usbguard/rules.conf
```

## Step 4: Restore Systemd Units

```bash
sudo cp layer2-etc/systemd-units/* /etc/systemd/system/
sudo systemctl daemon-reload

# Enable ClamAV timers
sudo systemctl enable clamav-quick.timer
sudo systemctl enable clamav-deep.timer
sudo systemctl start clamav-quick.timer
sudo systemctl start clamav-deep.timer
```

## Step 5: Restore Logrotate Config

```bash
sudo cp layer2-etc/logrotate/clamav-scans /etc/logrotate.d/clamav-scans
```

## Step 6: Restore Scripts

```bash
sudo cp -a layer3-scripts/* /usr/local/bin/
sudo chmod +x /usr/local/bin/*.sh
```

## Step 7: Restore User Configs

```bash
# MangoHud
mkdir -p ~/.config/MangoHud
cp layer4-user-configs/MangoHud.conf ~/.config/MangoHud/

# msmtprc
cp layer4-user-configs/msmtprc ~/.msmtprc
chmod 600 ~/.msmtprc

# Security folder
cp -a layer4-user-configs/security/ ~/security/

# Claude settings
mkdir -p ~/.claude
cp layer4-user-configs/claude-settings/settings.json ~/.claude/

# KDE Security menu
cp layer4-user-configs/kde-security-menu/security-*.desktop ~/.local/share/applications/
mkdir -p ~/.config/menus/applications-merged
cp layer4-user-configs/kde-security-menu/security.menu ~/.config/menus/applications-merged/
mkdir -p ~/.local/share/desktop-directories
cp layer4-user-configs/kde-security-menu/security-directory.desktop ~/.local/share/desktop-directories/
```

## Step 8: Install Flatpak Apps

```bash
RESTORE_STEP2B

# Add flatpak install commands
echo "$FLATPAK_APPS" | while IFS= read -r app; do
    [[ -n "$app" ]] && echo "flatpak install flathub ${app}"
done >> "${LAYER8}/RESTORE.md"

cat >> "${LAYER8}/RESTORE.md" << 'RESTORE_STEP9'
```

## Step 9: Restore Flatpak Data

```bash
# Only after flatpak apps are installed
cp -a layer6-flatpak-data/var-app/* ~/.var/app/
```

## Step 10: Restore Game Saves

```bash
# Only after Steam is set up
cp -a layer5-game-saves/compatdata/* ~/.local/share/Steam/steamapps/compatdata/
```

## Step 11: Restore Project Files

```bash
mkdir -p ~/projects
cp -a layer7-project/bazzite-laptop/ ~/projects/bazzite-laptop/
cd ~/projects/bazzite-laptop && git init
```

## Step 12: Restore LUKS Header (EMERGENCY ONLY)

Only use this if the LUKS header is corrupted:
```bash
sudo cryptsetup luksHeaderRestore /dev/sda3 --header-backup-file layer1-critical/luks-header.bak
```

## Step 13: Final Checks

```bash
# Verify DNS
resolvectl status

# Verify firewall
sudo firewall-cmd --list-all

# Verify sysctl
sysctl vm.swappiness  # Should be 180 for ZRAM

# Verify ClamAV timers
systemctl list-timers clamav-*

# Verify MangoHud
mangohud --version
```

---

RESTORE_STEP9

echo "Backup created: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LAYER8}/RESTORE.md"
echo "Hostname: $(hostname)" >> "${LAYER8}/RESTORE.md"

ok "RESTORE.md generated"

L8_SIZE=$(dir_size "$LAYER8")
info "Layer 8: 1 file, ${L8_SIZE}"

separator

# ===========================
# REDUNDANT LUKS HEADER COPY
# ===========================
phase "REDUNDANT LUKS HEADER COPY"

mkdir -p "$LUKS_REDUNDANT"
if [[ -f "${BACKUP_DIR}/layer1-critical/luks-header.bak" ]]; then
    cp -a "${BACKUP_DIR}/layer1-critical/luks-header.bak" \
        "${LUKS_REDUNDANT}/luks-header-$(date +%Y%m%d).bak" 2>/dev/null \
        && ok "Redundant LUKS header saved to ${LUKS_REDUNDANT}/" \
        || fail "Could not copy redundant LUKS header"
else
    warn "No LUKS header to copy (layer1 backup was skipped)"
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

# Per-layer sizes
printf "  ${DIM}%-35s %10s %8s${RESET}\n" "Layer" "Files" "Size"
printf "  ${DIM}%-35s %10s %8s${RESET}\n" "-----------------------------------" "-----" "-----"
printf "  %-35s %10s %8s\n" "layer1-critical" "$(file_count "${BACKUP_DIR}/layer1-critical" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer1-critical" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer2-etc" "$(file_count "${BACKUP_DIR}/layer2-etc" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer2-etc" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer3-scripts" "$(file_count "${BACKUP_DIR}/layer3-scripts" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer3-scripts" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer4-user-configs" "$(file_count "${BACKUP_DIR}/layer4-user-configs" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer4-user-configs" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer5-game-saves" "$(file_count "${BACKUP_DIR}/layer5-game-saves" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer5-game-saves" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer6-flatpak-data" "$(file_count "${BACKUP_DIR}/layer6-flatpak-data" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer6-flatpak-data" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer7-project" "$(file_count "${BACKUP_DIR}/layer7-project" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer7-project" 2>/dev/null)"
printf "  %-35s %10s %8s\n" "layer8-restore-guide" "$(file_count "${BACKUP_DIR}/layer8-restore-guide" 2>/dev/null)" "$(dir_size "${BACKUP_DIR}/layer8-restore-guide" 2>/dev/null)"
printf "  ${DIM}%-35s %10s %8s${RESET}\n" "-----------------------------------" "-----" "-----"
printf "  ${BWHITE}%-35s %10s %8s${RESET}\n" "TOTAL" "$TOTAL_COUNT" "$TOTAL_SIZE"

echo ""
echo -e "  ${DIM}Flash drive free space: ${FREE_GB}GB remaining${RESET}"
echo -e "  ${DIM}Backup location: ${BACKUP_DIR}/${RESET}"
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
