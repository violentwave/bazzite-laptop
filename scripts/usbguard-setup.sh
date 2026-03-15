#!/bin/bash
# USBGuard initial setup script
# Run manually after reboot to lock down USB device access.
# Usage: sudo bash usbguard-setup.sh
# This script generates a policy from currently connected devices,
# then enables USBGuard. NOT meant to be deployed permanently —
# run once to configure, then manage with usbguard CLI commands.
#
# NOTES:
# - The SanDisk Extreme SSD is connected via USB-C port — make sure it's
#   plugged in during Round 1 (initial policy generation) if you use it regularly
# - Make sure your primary input devices (keyboard, mouse) are connected for
#   Round 1 — they MUST be in the initial policy or they'll be blocked
# - Additional devices can be added in Round 2 via the interactive loop
#   after USBGuard is enabled
set -euo pipefail

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
    echo "${ts} [usbguard-setup] [${user}] ${msg}" >> "$AUDIT_LOG"
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
confirm_yes() {
    local prompt="$1"
    echo ""
    echo -e "  ${BYELLOW}${prompt}${RESET}"
    echo -ne "  ${BWHITE}Type 'yes' to continue: ${RESET}"
    read -r answer
    if [[ "$answer" != "yes" ]]; then
        echo ""
        echo -e "  ${BRED}Aborted.${RESET} No changes were made."
        exit 0
    fi
}

separator() {
    echo ""
    echo -e "  ${DIM}──────────────────────────────────────────────${RESET}"
    echo ""
}

# Must run as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root (use sudo).${RESET}" >&2
    exit 1
fi

audit_log "Script started"

# Check that usbguard is installed
if ! command -v usbguard &>/dev/null; then
    echo -e "${RED}Error: usbguard is not installed.${RESET}" >&2
    echo "Install it with: rpm-ostree install usbguard && systemctl reboot" >&2
    exit 1
fi

# ===========================
# BANNER
# ===========================
echo ""
echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}USBGUARD SETUP${RESET}                 ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}│${RESET}  ${DIM}USBGuard Initial Setup${RESET}               ${BCYAN}│${RESET}"
echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"
echo ""
echo -e "  ${DIM}This script will:${RESET}"
echo -e "  ${DIM}  Round 1: Generate a policy from CURRENTLY connected USB devices${RESET}"
echo -e "  ${DIM}  Round 2: Let you plug in additional devices and allow them${RESET}"
echo ""
echo -e "  ${BYELLOW}Before continuing, make sure these are plugged in NOW:${RESET}"
echo -e "  ${BWHITE}  - Keyboard and mouse${RESET} (critical — will be blocked otherwise)"
echo -e "  ${BWHITE}  - SanDisk Extreme SSD${RESET} (USB-C port, if used regularly)"
echo -e "  ${BWHITE}  - Any other daily-use peripherals${RESET}"
echo ""
echo -e "  ${DIM}Devices NOT plugged in during Round 1 can be added in Round 2.${RESET}"

separator

# ===========================
# ROUND 1 — GENERATE INITIAL POLICY
# ===========================
echo -e "  ${BCYAN}ROUND 1 — INITIAL POLICY FROM CONNECTED DEVICES${RESET}"
echo ""
echo -e "  ${DIM}Scanning currently connected USB devices...${RESET}"
echo ""

# Show what's connected
lsusb | while IFS= read -r line; do
    echo -e "    ${DIM}${line}${RESET}"
done

confirm_yes "Generate USBGuard policy from these devices?"

echo ""
echo -e "  ${YELLOW}Generating policy...${RESET}"
echo ""

GENERATED_POLICY=$(usbguard generate-policy 2>/dev/null) || true

# Validate generated policy before writing
if [[ -z "$GENERATED_POLICY" ]]; then
    echo -e "  ${RED}[FAIL]${RESET} usbguard generate-policy returned empty output. Aborting."
    exit 1
fi

if ! echo "$GENERATED_POLICY" | grep -q "^allow"; then
    echo -e "  ${RED}[FAIL]${RESET} Generated policy contains no 'allow' rules — this would block ALL devices."
    echo -e "  ${DIM}Make sure USB devices are connected and try again.${RESET}"
    exit 1
fi

ALLOW_COUNT=$(echo "$GENERATED_POLICY" | grep -c "^allow" || true)
DEVICE_COUNT=$(lsusb 2>/dev/null | wc -l || echo "?")
audit_log "Policy generated — ${ALLOW_COUNT} allow rules from ${DEVICE_COUNT} connected USB devices"
echo -e "  ${BWHITE}Generated policy (${ALLOW_COUNT} allow rules):${RESET}"
echo ""
echo "$GENERATED_POLICY" | while IFS= read -r line; do
    echo -e "    ${DIM}${line}${RESET}"
done

echo ""
confirm_yes "Write this policy to /etc/usbguard/rules.conf?"

echo "$GENERATED_POLICY" > /etc/usbguard/rules.conf
audit_log "Policy written to /etc/usbguard/rules.conf (${ALLOW_COUNT} allow rules)"
echo ""
echo -e "  ${GREEN}[OK]${RESET} Policy written to /etc/usbguard/rules.conf"

separator

# ===========================
# ENABLE USBGUARD
# ===========================
echo -e "  ${BCYAN}ENABLING USBGUARD${RESET}"
echo ""
echo -e "  ${BWHITE}Review the policy above.${RESET}"
echo -e "  ${DIM}After enabling, any NEW USB device not in the policy will be ${BRED}BLOCKED${RESET}${DIM}.${RESET}"

confirm_yes "Enable and start USBGuard now?"

echo ""
echo -e "  ${YELLOW}Enabling and starting usbguard service...${RESET}"
systemctl enable --now usbguard
echo ""
echo -e "  ${GREEN}[OK]${RESET} USBGuard is now active"

echo ""
echo -e "  ${BWHITE}Current policy rules:${RESET}"
echo ""
usbguard list-rules | while IFS= read -r line; do
    echo -e "    ${DIM}${line}${RESET}"
done

separator

# ===========================
# ROUND 2 — ADDING MORE DEVICES
# ===========================
echo -e "  ${BCYAN}ROUND 2 — ADDING MORE DEVICES${RESET}"
echo ""
echo -e "  ${DIM}Any NEW device plugged in from this point forward is blocked by default.${RESET}"
echo -e "  ${DIM}Use this interactive loop to plug in additional devices and allow them.${RESET}"
echo ""
echo -e "  ${DIM}How it works:${RESET}"
echo -e "  ${DIM}  1. Plug in a device${RESET}"
echo -e "  ${DIM}  2. Press Enter — the script will find the blocked device${RESET}"
echo -e "  ${DIM}  3. Confirm the device ID to allow it permanently (-p flag)${RESET}"
echo -e "  ${DIM}  4. Repeat, or type 'done' to finish${RESET}"

echo ""

while true; do
    echo ""
    echo -ne "  ${BYELLOW}Plug in a device and press Enter, or type 'done' to finish: ${RESET}"
    read -r input

    if [[ "$input" == "done" ]]; then
        break
    fi

    # Find blocked devices
    BLOCKED=$(usbguard list-devices 2>/dev/null | grep "block" || true)

    if [[ -z "$BLOCKED" ]]; then
        echo -e "  ${DIM}No blocked devices found. The device may already be allowed,${RESET}"
        echo -e "  ${DIM}or it hasn't been detected yet. Try unplugging and replugging.${RESET}"
        continue
    fi

    echo ""
    echo -e "  ${BWHITE}Blocked device(s):${RESET}"
    echo ""
    echo "$BLOCKED" | while IFS= read -r line; do
        echo -e "    ${RED}${line}${RESET}"
    done

    echo ""
    echo -ne "  ${BYELLOW}Enter the device ID number to allow (or 'skip' to skip): ${RESET}"
    read -r device_id

    if [[ "$device_id" == "skip" ]]; then
        echo -e "  ${DIM}Skipped.${RESET}"
        continue
    fi

    # Validate it looks like a number
    if ! [[ "$device_id" =~ ^[0-9]+$ ]]; then
        echo -e "  ${RED}Invalid ID '${device_id}' — must be a number. Try again.${RESET}"
        continue
    fi

    echo -e "  ${YELLOW}Allowing device ${device_id} permanently...${RESET}"
    if usbguard allow-device "$device_id" -p 2>&1; then
        echo -e "  ${GREEN}[OK]${RESET} Device ${device_id} allowed and saved to policy"
    else
        echo -e "  ${RED}[FAIL]${RESET} Could not allow device ${device_id}. Check the ID and try again."
    fi
done

separator

# ===========================
# FINAL POLICY
# ===========================
echo -e "  ${BCYAN}FINAL POLICY${RESET}"
echo ""
echo -e "  ${BWHITE}Complete USBGuard rules:${RESET}"
echo ""
usbguard list-rules | while IFS= read -r line; do
    echo -e "    ${DIM}${line}${RESET}"
done

separator

# ===========================
# USEFUL COMMANDS & RECOVERY
# ===========================
echo -e "  ${BCYAN}USEFUL COMMANDS${RESET}"
echo ""
echo -e "  ${DIM}usbguard list-devices${RESET}          — see all connected USB devices"
echo -e "  ${DIM}usbguard allow-device <id> -p${RESET}  — allow a device permanently"
echo -e "  ${DIM}usbguard block-device <id>${RESET}     — block a device (temporary)"
echo -e "  ${DIM}usbguard list-rules${RESET}            — see current policy rules"

separator

echo -e "  ${BRED}┌─────────────────────────────────────────────────────────────────┐${RESET}"
echo -e "  ${BRED}│${RESET}  ${BRED}RECOVERY — IF KEYBOARD/MOUSE GETS BLOCKED${RESET}                      ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}                                                                  ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  If your keyboard or mouse is blocked after reboot:              ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  1. Reboot and select the ${BWHITE}previous ostree deployment${RESET} from GRUB   ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  2. Run: ${DIM}sudo systemctl disable usbguard${RESET}                         ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  3. Reboot back into the current deployment                     ${BRED}│${RESET}"
echo -e "  ${BRED}│${RESET}  4. Re-run this script with all devices plugged in               ${BRED}│${RESET}"
echo -e "  ${BRED}└─────────────────────────────────────────────────────────────────┘${RESET}"
echo ""
audit_log "Script completed — USBGuard setup finished"
echo -e "  ${BGREEN}USBGuard setup complete.${RESET} Test all your USB devices now!"
echo ""
