#!/bin/bash
# shellcheck disable=SC2015
# restore.sh — Restore Bazzite laptop state from flat backup
# Deploy to: /mnt/backup/restore.sh (on BazziteBackup partition)
# Usage: sudo bash /mnt/backup/restore.sh
# Restores from /mnt/backup/latest/ to a fresh Bazzite install
set -uo pipefail

# --- Configuration ---
MOUNT_POINT="/mnt/backup"
BACKUP_DIR="${MOUNT_POINT}/latest"
HOME_DIR="/home/lch"
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

# Prompt for confirmation
confirm() {
    local msg="$1"
    echo ""
    echo -ne "  ${BYELLOW}${msg} [y/N]: ${RESET}"
    read -r answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

# Copy file with error handling
restore_file() {
    local src="$1"
    local dst="$2"
    local label="${3:-$(basename "$dst")}"
    if [[ -f "$src" ]]; then
        mkdir -p "$(dirname "$dst")"
        cp -a "$src" "$dst" 2>/dev/null && ok "$label" || fail "$label"
    else
        warn "$label not found in backup"
    fi
}

# Copy directory with error handling
restore_dir() {
    local src="$1"
    local dst="$2"
    local label="${3:-$(basename "$dst")/}"
    if [[ -d "$src" ]]; then
        mkdir -p "$dst"
        cp -a "$src"/. "$dst/" 2>/dev/null && ok "$label" || fail "$label"
    else
        warn "$label not found in backup"
    fi
}

# --- Must run as root ---
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root (sudo).${RESET}"
    echo "Usage: sudo bash /mnt/backup/restore.sh"
    exit 1
fi

# ===========================
# BANNER
# ===========================
echo ""
echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE RESTORE${RESET}                ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}│${RESET}  ${DIM}System Restore · $(date '+%b %d, %Y %I:%M %p')${RESET}${BCYAN}│${RESET}"
echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"

# ===========================
# PRE-FLIGHT CHECKS
# ===========================
phase "PRE-FLIGHT CHECKS"

if [[ ! -d "$BACKUP_DIR" ]]; then
    echo -e "  ${BRED}Backup not found at ${BACKUP_DIR}${RESET}"
    echo -e "  ${DIM}Make sure the flash drive is mounted at ${MOUNT_POINT}${RESET}"
    exit 1
fi
ok "Backup found at ${BACKUP_DIR}"

# Show backup timestamp
if [[ -f "${BACKUP_DIR}/backup-timestamp.txt" ]]; then
    TIMESTAMP=$(head -1 "${BACKUP_DIR}/backup-timestamp.txt")
    BACKUP_HOST=$(tail -1 "${BACKUP_DIR}/backup-timestamp.txt")
    echo -e "  ${BWHITE}Backup taken:${RESET} ${TIMESTAMP}"
    echo -e "  ${BWHITE}Hostname:${RESET}     ${BACKUP_HOST}"
else
    warn "No backup-timestamp.txt found"
fi

separator

# ===========================
# STEP 1: SHOW WHAT WILL BE RESTORED
# ===========================
phase "STEP 1 — WHAT WILL BE RESTORED"

echo -e "  ${BWHITE}System configs:${RESET} resolved.conf.d, sysctl.d, rules.d, gamemode.ini,"
echo -e "                 environment, freshclam.conf, systemd units, logrotate,"
echo -e "                 usbguard rules, firewalld configs"
echo -e "  ${BWHITE}Scripts:${RESET}        /usr/local/bin/ contents"
echo -e "  ${BWHITE}User configs:${RESET}   msmtprc, MangoHud, Claude settings, KDE Security menu,"
echo -e "                 ~/security/ folder"
[[ -d "${BACKUP_DIR}/compatdata" ]] && echo -e "  ${BWHITE}Game saves:${RESET}     Steam compatdata"
[[ -d "${BACKUP_DIR}/flatpak-data" ]] && echo -e "  ${BWHITE}Flatpak data:${RESET}   ~/.var/app/ contents"
[[ -d "${BACKUP_DIR}/bazzite-laptop" ]] && echo -e "  ${BWHITE}Project:${RESET}        ~/projects/bazzite-laptop/"

if ! confirm "Proceed with restore?"; then
    echo -e "  ${DIM}Aborted.${RESET}"
    exit 0
fi

separator

# ===========================
# STEP 2: SYSTEM CONFIGS
# ===========================
phase "STEP 2 — SYSTEM CONFIGS"

if ! confirm "Restore system configs to /etc/?"; then
    info "Skipping system configs"
else
    restore_dir "${BACKUP_DIR}/resolved.conf.d" "/etc/systemd/resolved.conf.d" "resolved.conf.d/"
    restore_dir "${BACKUP_DIR}/sysctl.d" "/etc/sysctl.d" "sysctl.d/"
    restore_dir "${BACKUP_DIR}/rules.d" "/etc/udev/rules.d" "rules.d/"
    restore_file "${BACKUP_DIR}/etc-gamemode.ini" "/etc/gamemode.ini" "gamemode.ini"
    restore_file "${BACKUP_DIR}/etc-environment" "/etc/environment" "environment"
    restore_file "${BACKUP_DIR}/etc-freshclam.conf" "/etc/freshclam.conf" "freshclam.conf"

    # Systemd units
    if [[ -d "${BACKUP_DIR}/systemd-units" ]] && [[ -n "$(ls -A "${BACKUP_DIR}/systemd-units/" 2>/dev/null)" ]]; then
        cp -a "${BACKUP_DIR}/systemd-units/"* /etc/systemd/system/ 2>/dev/null && ok "systemd-units/" || fail "systemd-units/"
    else
        warn "No systemd units in backup"
    fi

    # Logrotate
    restore_file "${BACKUP_DIR}/logrotate-clamav-scans" "/etc/logrotate.d/clamav-scans" "logrotate-clamav-scans"
    restore_file "${BACKUP_DIR}/logrotate-system-health" "/etc/logrotate.d/system-health" "logrotate-system-health"

    # USBGuard rules
    if [[ -f "${BACKUP_DIR}/etc-usbguard-rules.conf" ]]; then
        mkdir -p /etc/usbguard
        cp -a "${BACKUP_DIR}/etc-usbguard-rules.conf" /etc/usbguard/rules.conf 2>/dev/null && ok "usbguard rules.conf" || fail "usbguard rules.conf"
    else
        info "No USBGuard rules in backup (skipping)"
    fi

    # Firewalld
    restore_dir "${BACKUP_DIR}/firewalld" "/etc/firewalld" "firewalld/"
fi

separator

# ===========================
# STEP 3: SCRIPTS
# ===========================
phase "STEP 3 — SCRIPTS"

if ! confirm "Restore scripts to /usr/local/bin/?"; then
    info "Skipping scripts"
else
    if [[ -d "${BACKUP_DIR}/scripts" ]] && [[ -n "$(ls -A "${BACKUP_DIR}/scripts/" 2>/dev/null)" ]]; then
        cp -a "${BACKUP_DIR}/scripts/"* /usr/local/bin/ 2>/dev/null && ok "scripts -> /usr/local/bin/" || fail "scripts/"
        chmod +x /usr/local/bin/*.sh 2>/dev/null
        ok "chmod +x /usr/local/bin/*.sh"
    else
        warn "No scripts in backup"
    fi
fi

separator

# ===========================
# STEP 4: USER CONFIGS
# ===========================
phase "STEP 4 — USER CONFIGS (as lch)"

if ! confirm "Restore user configs for lch?"; then
    info "Skipping user configs"
else
    # msmtprc
    if [[ -f "${BACKUP_DIR}/msmtprc" ]]; then
        cp -a "${BACKUP_DIR}/msmtprc" "${HOME_DIR}/.msmtprc" 2>/dev/null && ok ".msmtprc" || fail ".msmtprc"
        chmod 600 "${HOME_DIR}/.msmtprc"
    else
        warn "msmtprc not found in backup"
    fi

    # MangoHud
    mkdir -p "${HOME_DIR}/.config/MangoHud"
    restore_dir "${BACKUP_DIR}/MangoHud" "${HOME_DIR}/.config/MangoHud" "MangoHud/"

    # Claude Code settings
    if [[ -d "${BACKUP_DIR}/dot-claude" ]]; then
        mkdir -p "${HOME_DIR}/.claude"
        cp -a "${BACKUP_DIR}/dot-claude"/. "${HOME_DIR}/.claude/" 2>/dev/null && ok "dot-claude/" || fail "dot-claude/"
    else
        warn "dot-claude/ not found in backup"
    fi

    # KDE Security menu
    if [[ -d "${BACKUP_DIR}/kde-security-menu" ]]; then
        mkdir -p "${HOME_DIR}/.local/share/applications"
        mkdir -p "${HOME_DIR}/.local/share/desktop-directories"
        mkdir -p "${HOME_DIR}/.config/menus/applications-merged"

        # .desktop shortcut files
        for f in "${BACKUP_DIR}/kde-security-menu/security-"*.desktop; do
            [[ -f "$f" ]] || continue
            fname=$(basename "$f")
            if [[ "$fname" == "security-directory.desktop" ]]; then
                cp -a "$f" "${HOME_DIR}/.local/share/desktop-directories/" 2>/dev/null
            else
                cp -a "$f" "${HOME_DIR}/.local/share/applications/" 2>/dev/null
            fi
        done

        # .menu file
        if [[ -f "${BACKUP_DIR}/kde-security-menu/security.menu" ]]; then
            cp -a "${BACKUP_DIR}/kde-security-menu/security.menu" "${HOME_DIR}/.config/menus/applications-merged/" 2>/dev/null
        fi

        ok "kde-security-menu/"
    else
        warn "kde-security-menu/ not found in backup"
    fi

    # Security folder
    restore_dir "${BACKUP_DIR}/security" "${HOME_DIR}/security" "security/"
fi

separator

# ===========================
# STEP 5: GAME SAVES
# ===========================
phase "STEP 5 — GAME SAVES"

if [[ -d "${BACKUP_DIR}/compatdata" ]]; then
    if ! confirm "Restore Steam game saves (compatdata)?"; then
        info "Skipping game saves"
    else
        STEAM_COMPAT="${HOME_DIR}/.local/share/Steam/steamapps/compatdata"
        mkdir -p "$STEAM_COMPAT"
        cp -a "${BACKUP_DIR}/compatdata"/. "$STEAM_COMPAT/" 2>/dev/null && ok "compatdata/" || fail "compatdata/"
    fi
else
    info "No game saves in backup (skipping)"
fi

separator

# ===========================
# STEP 6: FLATPAK DATA
# ===========================
phase "STEP 6 — FLATPAK DATA"

if [[ -d "${BACKUP_DIR}/flatpak-data" ]]; then
    if ! confirm "Restore flatpak data (~/.var/app/)?"; then
        info "Skipping flatpak data"
    else
        mkdir -p "${HOME_DIR}/.var/app"
        cp -a "${BACKUP_DIR}/flatpak-data"/. "${HOME_DIR}/.var/app/" 2>/dev/null && ok "flatpak-data/" || fail "flatpak-data/"
    fi
else
    info "No flatpak data in backup (skipping)"
fi

separator

# ===========================
# STEP 7: PROJECT FILES
# ===========================
phase "STEP 7 — PROJECT FILES"

if [[ -d "${BACKUP_DIR}/bazzite-laptop" ]]; then
    if ! confirm "Restore ~/projects/bazzite-laptop/?"; then
        info "Skipping project files"
    else
        mkdir -p "${HOME_DIR}/projects"
        restore_dir "${BACKUP_DIR}/bazzite-laptop" "${HOME_DIR}/projects/bazzite-laptop" "bazzite-laptop/"
    fi
else
    info "No project files in backup (skipping)"
fi

separator

# ===========================
# STEP 8: FIX OWNERSHIP
# ===========================
phase "STEP 8 — FIXING OWNERSHIP"

info "Setting ownership to lch:lch..."

for path in \
    "${HOME_DIR}/.config" \
    "${HOME_DIR}/.claude" \
    "${HOME_DIR}/.local" \
    "${HOME_DIR}/.var" \
    "${HOME_DIR}/security" \
    "${HOME_DIR}/projects" \
    "${HOME_DIR}/.msmtprc"; do
    if [[ -e "$path" ]]; then
        chown -R lch:lch "$path" 2>/dev/null && ok "$(basename "$path")" || fail "chown $(basename "$path")"
    fi
done

separator

# ===========================
# STEP 9: MANUAL STEPS
# ===========================
phase "STEP 9 — MANUAL STEPS REQUIRED"

echo -e "  ${BRED}The following steps must be done manually:${RESET}"
echo ""

echo -e "  ${BWHITE}1. Install layered packages:${RESET}"
echo -e "     ${DIM}rpm-ostree install clamav clamav-freshclam gamemode msmtp usbguard${RESET}"
echo ""

echo -e "  ${BWHITE}2. Check kernel args (compare with cmdline.txt):${RESET}"
echo -e "     ${DIM}rpm-ostree kargs --append=nvidia-drm.modeset=1${RESET}"
echo ""

echo -e "  ${BWHITE}3. Reboot to apply rpm-ostree changes:${RESET}"
echo -e "     ${DIM}systemctl reboot${RESET}"
echo ""

echo -e "  ${BWHITE}4. After reboot — apply firewall:${RESET}"
echo -e "     ${DIM}sudo firewall-cmd --set-default-zone=drop${RESET}"
echo -e "     ${DIM}sudo firewall-cmd --permanent --zone=drop --add-service=dhcpv6-client${RESET}"
echo -e "     ${DIM}sudo firewall-cmd --set-log-denied=all${RESET}"
echo -e "     ${DIM}sudo firewall-cmd --runtime-to-permanent${RESET}"
echo -e "     ${DIM}sudo firewall-cmd --reload${RESET}"
echo ""

echo -e "  ${BWHITE}5. Disable services:${RESET}"
echo -e "     ${DIM}sudo systemctl disable --now sshd cups avahi-daemon.service \\${RESET}"
echo -e "     ${DIM}  avahi-daemon.socket ModemManager.service sssd.service \\${RESET}"
echo -e "     ${DIM}  sssd-kcm.socket mdmonitor.service qemu-guest-agent.service${RESET}"
echo -e "     ${DIM}sudo systemctl disable --now raid-check.timer${RESET}"
echo -e "     ${DIM}for s in \$(systemctl list-unit-files 'virt*' --state=enabled --no-pager | awk '{print \$1}'); do${RESET}"
echo -e "     ${DIM}  sudo systemctl disable --now \"\$s\"${RESET}"
echo -e "     ${DIM}done${RESET}"
echo -e "     ${DIM}sudo systemctl disable --now iscsi-onboot.service iscsi-starter.service \\${RESET}"
echo -e "     ${DIM}  iscsid.socket iscsiuio.socket${RESET}"
echo ""

echo -e "  ${BWHITE}6. Enable ClamAV and health timers:${RESET}"
echo -e "     ${DIM}sudo systemctl daemon-reload${RESET}"
echo -e "     ${DIM}sudo systemctl enable --now clamav-quick.timer clamav-deep.timer${RESET}"
echo -e "     ${DIM}sudo systemctl enable --now system-health.timer${RESET}"
echo -e "     ${DIM}sudo mkdir -p /var/log/system-health${RESET}"
echo -e "     ${DIM}sudo cp configs/logrotate-system-health /etc/logrotate.d/system-health${RESET}"
echo ""

echo -e "  ${BWHITE}7. Enable USBGuard:${RESET}"
echo -e "     ${DIM}sudo systemctl enable --now usbguard${RESET}"
echo ""

echo -e "  ${BWHITE}8. Restart DNS:${RESET}"
echo -e "     ${DIM}sudo systemctl restart systemd-resolved${RESET}"
echo ""

echo -e "  ${BWHITE}9. Fix external SSD ownership:${RESET}"
echo -e "     ${DIM}sudo chown lch:lch /var/mnt/ext-ssd/${RESET}"
echo ""

echo -e "  ${BWHITE}10. Reinstall Flatpaks:${RESET}"
echo -e "     ${DIM}cat /mnt/backup/latest/flatpak-list.txt${RESET}"
echo -e "     ${DIM}(install each with: flatpak install flathub <app-id>)${RESET}"
echo ""

echo -e "  ${BWHITE}11. Apply sysctl settings:${RESET}"
echo -e "     ${DIM}sudo sysctl --system${RESET}"
echo ""

echo -e "  ${BWHITE}12. Reload udev rules:${RESET}"
echo -e "     ${DIM}sudo udevadm control --reload-rules && sudo udevadm trigger${RESET}"
echo ""

echo -e "  ${BWHITE}13. Final reboot${RESET}"
echo -e "     ${DIM}systemctl reboot${RESET}"

separator

# ===========================
# SUMMARY
# ===========================
phase "RESTORE SUMMARY"

echo -e "  ${BGREEN}┌─────────────────────────────────────────────┐${RESET}"
echo -e "  ${BGREEN}│${RESET}  ${BWHITE}RESTORE COMPLETE${RESET}                             ${BGREEN}│${RESET}"
echo -e "  ${BGREEN}└─────────────────────────────────────────────┘${RESET}"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo -e "  ${RED}Errors: ${ERRORS}${RESET}  |  ${YELLOW}Warnings: ${WARNINGS}${RESET}"
    echo -e "  ${DIM}Review errors above before proceeding with manual steps.${RESET}"
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "  ${YELLOW}Warnings: ${WARNINGS}${RESET} (no errors)"
else
    echo -e "  ${GREEN}All files restored successfully.${RESET}"
fi

echo ""
echo -e "  ${BRED}IMPORTANT: Complete the manual steps above (1-13) to finish restoration.${RESET}"
echo ""
