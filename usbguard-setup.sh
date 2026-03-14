#!/bin/bash
# USBGuard initial setup script
# Run manually after reboot to lock down USB device access.
# Usage: sudo bash usbguard-setup.sh
# This script generates a policy from currently connected devices,
# then enables USBGuard. NOT meant to be deployed permanently —
# run once to configure, then manage with usbguard CLI commands.
set -euo pipefail

# Must run as root
if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (use sudo)." >&2
    exit 1
fi

# Step 1: Check that usbguard is installed
if ! command -v usbguard &>/dev/null; then
    echo "Error: usbguard is not installed." >&2
    echo "Install it with: rpm-ostree install usbguard && systemctl reboot" >&2
    exit 1
fi

# Step 2: Explain what's about to happen
echo "========================================"
echo "  USBGuard Initial Setup"
echo "========================================"
echo ""
echo "This script will:"
echo "  1. Generate a USBGuard policy from your CURRENTLY connected USB devices"
echo "  2. Save it to /etc/usbguard/rules.conf"
echo "  3. Enable and start the usbguard service"
echo ""
echo "After this, any NEW USB device not in the policy will be BLOCKED by default."
echo "Make sure all devices you use regularly are plugged in right now:"
echo "  - Mouse, keyboard, external SSD, gaming peripherals, etc."
echo ""
read -rp "Press Enter to continue (or Ctrl+C to abort)... "

# Step 3: Generate initial policy from currently connected devices
echo ""
echo "Generating policy from connected devices..."
usbguard generate-policy | tee /etc/usbguard/rules.conf
echo ""
echo "Policy written to /etc/usbguard/rules.conf"

# Step 4: Confirm before enabling
echo ""
echo "========================================"
echo "  Review the policy above."
echo "  Ready to enable USBGuard?"
echo "========================================"
echo ""
read -rp "Type 'yes' to enable USBGuard, anything else to abort: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted. Policy was saved but service was NOT enabled."
    echo "You can enable it later with: sudo systemctl enable --now usbguard"
    exit 0
fi

echo ""
echo "Enabling and starting usbguard..."
systemctl enable --now usbguard

# Step 5: Show current policy
echo ""
echo "Current rules:"
echo "----------------------------------------"
usbguard list-rules
echo "----------------------------------------"

# Step 6: Useful commands reference
echo ""
echo "Useful USBGuard commands:"
echo "  usbguard list-devices          — see all connected USB devices"
echo "  usbguard allow-device <id>     — allow a new device (temporary)"
echo "  usbguard block-device <id>     — block a device (temporary)"
echo "  usbguard list-rules            — see current policy rules"
echo "  usbguard append-rule 'allow ...' — permanently allow a device"
echo ""
echo "To permanently allow a new device, plug it in, then:"
echo "  usbguard list-devices           # find the device ID"
echo "  usbguard allow-device <id> -p   # allow and save to policy"

# Step 7: Warning
echo ""
echo "========================================"
echo "  WARNING"
echo "========================================"
echo "Test ALL your USB devices NOW before logging out or rebooting!"
echo "  - Mouse, keyboard, external SSD, gaming peripherals"
echo "  - If a device is blocked, fix it while you're still logged in:"
echo "    usbguard list-devices"
echo "    usbguard allow-device <id> -p"
echo ""
echo "If you get locked out (keyboard/mouse blocked), you can recover by"
echo "booting into the previous ostree deployment from the GRUB menu."
echo "========================================"
