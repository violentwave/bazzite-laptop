#!/bin/bash
# setup-security-folder.sh — Creates ~/security folder structure
# Run as your normal user (not root)
# This is the central security hub for quick access to security configs and tools
set -euo pipefail

SECURITY_DIR="/home/lch/security"

echo "Setting up security folder at ${SECURITY_DIR}..."

# Create directories
mkdir -p "${SECURITY_DIR}/quarantine"
mkdir -p "${SECURITY_DIR}/configs"
mkdir -p "${SECURITY_DIR}/usbguard"

# Create logs symlink (only if target exists)
if [[ -d /var/log/clamav-scans ]]; then
    ln -sfn /var/log/clamav-scans "${SECURITY_DIR}/logs"
    echo "  Linked logs/ -> /var/log/clamav-scans"
else
    mkdir -p "${SECURITY_DIR}/logs"
    echo "  Created logs/ (/var/log/clamav-scans doesn't exist yet — will be a plain directory)"
    echo "  Re-run this script after ClamAV is set up to create the symlink."
fi

# Create config symlinks
ln -sf /etc/gamemode.ini "${SECURITY_DIR}/configs/gamemode.ini"
ln -sf /etc/systemd/resolved.conf.d/dns-over-tls.conf "${SECURITY_DIR}/configs/dns-config"
ln -sf /usr/local/bin/public-wifi-mode "${SECURITY_DIR}/configs/public-wifi-mode"

# Create firewall-status.sh
cat > "${SECURITY_DIR}/configs/firewall-status.sh" << 'EOF'
#!/bin/bash
# firewall-status.sh — Quick firewall overview
sudo firewall-cmd --list-all && echo "---" && sudo firewall-cmd --get-log-denied
EOF
chmod +x "${SECURITY_DIR}/configs/firewall-status.sh"

# Create configs/README.md
cat > "${SECURITY_DIR}/configs/README.md" << 'EOF'
# Security Configs Reference

Symlinks and scripts for quick access to security-related configuration files.

| File | Real Path | Purpose |
|------|-----------|---------|
| gamemode.ini | /etc/gamemode.ini | GameMode performance tuning config |
| dns-config | /etc/systemd/resolved.conf.d/dns-over-tls.conf | DNS-over-TLS resolver settings |
| public-wifi-mode | /usr/local/bin/public-wifi-mode | Script to toggle public WiFi hardening |
| firewall-status.sh | (local script) | Shows firewall rules and log-denied setting |
EOF

# Create top-level README.md
cat > "${SECURITY_DIR}/README.md" << 'EOF'
# Security Hub — Bazzite Gaming Laptop

Central security folder for the Bazzite gaming laptop (Acer Predator G3-571).

## Folder Structure

- **quarantine/** — Files ClamAV flagged as infected are moved here automatically
- **logs/** — ClamAV scan logs (symlink to /var/log/clamav-scans)
- **configs/** — Symlinks to security-related config files for easy reference and editing
- **usbguard/** — USBGuard policy reference (populated after USBGuard setup)

## Quick Commands

```bash
# Run a quick antivirus scan (home + tmp)
sudo /usr/local/bin/clamav-scan.sh quick

# Run a deep antivirus scan (includes Steam library)
sudo /usr/local/bin/clamav-scan.sh deep

# Check firewall status
sudo firewall-cmd --list-all

# Check firewall log-denied setting
sudo firewall-cmd --get-log-denied

# List USB devices (USBGuard)
usbguard list-devices

# List USB devices (lsusb)
lsusb

# Check DNS resolution
resolvectl status
```
EOF

echo "Security folder setup complete at ${SECURITY_DIR}"
