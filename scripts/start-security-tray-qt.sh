#!/usr/bin/env bash
# Start the PySide6 security tray (Qt6 replacement for GTK3 tray)
# Deploy to: /usr/local/bin/start-security-tray-qt.sh (chmod 755)

set -euo pipefail

PROJECT_DIR="/var/home/lch/projects/bazzite-laptop"
VENV_DIR="$PROJECT_DIR/.venv"
TRAY_SCRIPT="$PROJECT_DIR/tray/security_tray_qt.py"

# Activate venv
source "$VENV_DIR/bin/activate"

# PySide6 bundled Qt6 D-Bus conflicts with system Qt6 on Wayland.
# Force XCB (X11) backend until Wayland StatusNotifierItem is fixed.
export QT_QPA_PLATFORM=xcb

exec python "$TRAY_SCRIPT" "$@"
