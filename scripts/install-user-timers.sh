#!/bin/bash
# install-user-timers.sh — Migrate repo-owned scheduled jobs to user-scoped systemd units
# Location: scripts/install-user-timers.sh
#
# PURPOSE:
#   System-scoped services executing user-home repo venv paths fail with 203/EXEC
#   because SELinux prevents system services from accessing user_home_t labeled files.
#   This script installs user-scoped units that run as the user, avoiding the
#   namespace/permission issues.
#
# USAGE:
#   ./scripts/install-user-timers.sh [--disable-system]
#
# OPTIONS:
#   --disable-system   Also disable the old system timers (requires sudo)
#
# SAFETY:
#   - Idempotent — safe to run multiple times
#   - Non-destructive by default — old system units remain unless --disable-system
#   - Validates all paths before activation

set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
USER_UNITS_DIR="${REPO_DIR}/systemd/user"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
DISABLE_SYSTEM=false

# ─────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --disable-system) DISABLE_SYSTEM=true ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--disable-system]"
            echo ""
            echo "Install user-scoped systemd units for repo-owned scheduled jobs."
            echo ""
            echo "Options:"
            echo "  --disable-system   Disable old system timers (requires sudo)"
            echo "  --help, -h         Show this help"
            echo ""
            echo "This script is idempotent and safe to run multiple times."
            exit 0
            ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# ─────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────
echo "=== User-Scoped Timer Installation ==="
echo ""

# Verify repo directory exists
if [[ ! -d "$REPO_DIR" ]]; then
    echo "ERROR: Repository directory not found: $REPO_DIR" >&2
    exit 1
fi

# Verify venv exists
VENV_PYTHON="$REPO_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: Virtual environment not found or not executable:" >&2
    echo "  $VENV_PYTHON" >&2
    echo "  Run: uv venv && uv pip install -r requirements-ai.txt" >&2
    exit 1
fi
echo "✓ Virtual environment verified: $VENV_PYTHON"

# Verify user unit files exist
UNITS=(code-index fedora-updates release-watch rag-embed)
for unit in "${UNITS[@]}"; do
    if [[ ! -f "$USER_UNITS_DIR/${unit}.service" ]]; then
        echo "ERROR: Service file not found: $USER_UNITS_DIR/${unit}.service" >&2
        exit 1
    fi
    if [[ ! -f "$USER_UNITS_DIR/${unit}.timer" ]]; then
        echo "ERROR: Timer file not found: $USER_UNITS_DIR/${unit}.timer" >&2
        exit 1
    fi
done
echo "✓ All user unit files present"

# Verify systemd is available
if ! command -v systemctl &>/dev/null; then
    echo "ERROR: systemctl not found" >&2
    exit 1
fi

# Check if running as the target user (should NOT be root for user units)
if [[ "$(id -u)" -eq 0 ]]; then
    echo "WARNING: Running as root. User units should be installed as the target user (lch)." >&2
    echo "  Switch to the user account and re-run this script." >&2
    exit 1
fi

echo "✓ Running as user: $(id -un)"
echo ""

# ─────────────────────────────────────────────────────────────
# Install user units
# ─────────────────────────────────────────────────────────────
echo "=== Installing User Units ==="

# Create user systemd directory
mkdir -p "$SYSTEMD_USER_DIR"
echo "✓ Created $SYSTEMD_USER_DIR"

# Copy unit files
for unit in "${UNITS[@]}"; do
    cp "$USER_UNITS_DIR/${unit}.service" "$SYSTEMD_USER_DIR/"
    cp "$USER_UNITS_DIR/${unit}.timer" "$SYSTEMD_USER_DIR/"
    echo "✓ Installed ${unit}.service and ${unit}.timer"
done

# Set permissions (user units don't need special SELinux handling)
chmod 644 "$SYSTEMD_USER_DIR"/*.service "$SYSTEMD_USER_DIR"/*.timer
echo "✓ Set permissions on unit files"

# ─────────────────────────────────────────────────────────────
# Reload and enable
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== Reloading systemd ==="
systemctl --user daemon-reload
echo "✓ systemctl --user daemon-reload"

echo ""
echo "=== Enabling Timers ==="
for unit in "${UNITS[@]}"; do
    systemctl --user enable "${unit}.timer"
    echo "✓ Enabled ${unit}.timer"
done

# ─────────────────────────────────────────────────────────────
# Optional: Disable old system units
# ─────────────────────────────────────────────────────────────
if [[ "$DISABLE_SYSTEM" == true ]]; then
    echo ""
    echo "=== Disabling System Units ==="
    
    # Check if we have sudo access
    if ! sudo -n true 2>/dev/null; then
        echo "ERROR: --disable-system requires passwordless sudo or interactive sudo." >&2
        echo "  Run with sudo first, or disable system units manually:" >&2
        echo "    sudo systemctl disable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer" >&2
        exit 1
    fi
    
    for unit in "${UNITS[@]}"; do
        # Check if system unit exists and is enabled
        if systemctl is-enabled "${unit}.timer" &>/dev/null; then
            sudo systemctl disable --now "${unit}.timer" 2>/dev/null || true
            echo "✓ Disabled system ${unit}.timer"
        else
            echo "  (system ${unit}.timer not enabled — skipping)"
        fi
        
        # Also check service units
        if systemctl is-enabled "${unit}.service" &>/dev/null; then
            sudo systemctl disable "${unit}.service" 2>/dev/null || true
            echo "✓ Disabled system ${unit}.service"
        fi
    done
    
    echo ""
    echo "NOTE: System unit files remain in /etc/systemd/system/"
    echo "      To completely remove them (optional):"
    echo "        sudo rm -f /etc/systemd/system/{code-index,fedora-updates,release-watch,rag-embed}.{service,timer}"
    echo "        sudo systemctl daemon-reload"
else
    echo ""
    echo "=== System Units ==="
    echo "NOTE: Old system units are still active. To disable them, run:"
    echo "  $0 --disable-system"
    echo ""
    echo "Or manually:"
    echo "  sudo systemctl disable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer"
fi

# ─────────────────────────────────────────────────────────────
# Start timers
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== Starting Timers ==="
systemctl --user start code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer
echo "✓ Started all timers"

# ─────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== Validation ==="
echo ""
echo "Timer Status:"
systemctl --user list-timers code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer --no-pager || true

echo ""
echo "Next Run Times:"
for unit in "${UNITS[@]}"; do
    NEXT=$(systemctl --user show "${unit}.timer" --property=NextElapseUSecRealtime --value 2>/dev/null || echo "unknown")
    echo "  ${unit}.timer: $NEXT"
done

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "Installation Complete"
echo "========================================"
echo ""
echo "User units installed to: $SYSTEMD_USER_DIR"
echo ""
echo "VALIDATION COMMANDS:"
echo "  systemctl --user list-timers"
echo "  systemctl --user status code-index.service --no-pager"
echo "  journalctl --user -u code-index.service -n 50 --no-pager"
echo ""
echo "MANUAL TESTING (run services immediately):"
echo "  systemctl --user start code-index.service"
echo "  systemctl --user start fedora-updates.service"
echo "  systemctl --user start release-watch.service"
echo "  systemctl --user start rag-embed.service"
echo ""
echo "ROLLBACK (if needed):"
echo "  systemctl --user disable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer"
echo "  rm -f ~/.config/systemd/user/{code-index,fedora-updates,release-watch,rag-embed}.{service,timer}"
echo "  systemctl --user daemon-reload"
echo ""

if [[ "$DISABLE_SYSTEM" == false ]]; then
    echo "TO COMPLETE MIGRATION:"
    echo "  sudo systemctl disable --now code-index.timer fedora-updates.timer release-watch.timer rag-embed.timer"
    echo "  sudo rm -f /etc/systemd/system/{code-index,fedora-updates,release-watch,rag-embed}.{service,timer}"
    echo "  sudo systemctl daemon-reload"
    echo ""
fi

echo "REMAINING MANUAL STEPS (see docs/P76_SYSTEMD_SCOPE_REMEDIATION.md):"
echo "  1. Verify security-audit.service API keys (Gemini key may be invalid)"
echo "  2. Check system-health.service if still failing (may require SELinux policy review)"
echo "  3. Check logrotate.service boot.log permissions (system-level issue)"
echo ""
