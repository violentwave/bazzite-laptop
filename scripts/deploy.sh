#!/bin/bash
# deploy.sh — Sync repo files to their system deploy targets
# Run with: sudo ./scripts/deploy.sh [--dry-run]
set -euo pipefail

# --- Root check ---
if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (sudo)." >&2
    exit 1
fi

# --- Auto-detect repo root ---
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_HOME="/home/lch"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN — no files will be modified ==="
    echo ""
fi

# --- Counters ---
COUNT_UPDATED=0
COUNT_SKIPPED=0
COUNT_NEW=0

# --- Deploy function ---
# Usage: deploy <source> <destination> <mode> [owner]
deploy() {
    local src="$1"
    local dst="$2"
    local mode="$3"
    local owner="${4:-}"

    if [[ ! -f "$src" ]]; then
        echo "[MISSING]  $src (source not found, skipping)"
        return
    fi

    local label
    if [[ ! -f "$dst" ]]; then
        label="[NEW]"
        COUNT_NEW=$((COUNT_NEW + 1))
    elif diff -q "$src" "$dst" &>/dev/null; then
        echo "[OK]       $dst"
        COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
        return
    else
        label="[UPDATED]"
        COUNT_UPDATED=$((COUNT_UPDATED + 1))
    fi

    echo "$label  $dst"

    if [[ "$DRY_RUN" == false ]]; then
        mkdir -p "$(dirname "$dst")"
        cp -a "$src" "$dst"
        chmod "$mode" "$dst"
        if [[ -n "$owner" ]]; then
            chown "$owner" "$dst"
        fi
    fi
}

# --- Deploy function for directories (recursive) ---
# Usage: deploy_dir <source_dir> <dest_dir> <owner>
deploy_dir() {
    local src_dir="$1"
    local dst_dir="$2"
    local owner="$3"

    find "$src_dir" -type f | while read -r src; do
        local rel="${src#"$src_dir"/}"
        local dst="$dst_dir/$rel"
        deploy "$src" "$dst" 644 "$owner"
    done
}

echo "=== Scripts -> /usr/local/bin/ ==="
for script in clamav-scan.sh clamav-alert.sh clamav-healthcheck.sh quarantine-release.sh bazzite-security-test.sh system-health-snapshot.sh system-health-test.sh start-security-tray.sh integration-test.sh; do
    deploy "$REPO_DIR/scripts/$script" "/usr/local/bin/$script" 755
done
echo ""

echo "=== AI Layer Scripts -> /usr/local/bin/ ==="
for script in threat-lookup.sh rag-embed.sh rag-query.sh code-quality.sh gaming-analyze.sh gaming-profile.sh; do
    deploy "$REPO_DIR/scripts/$script" "/usr/local/bin/$script" 755
done
echo ""

echo "=== Systemd units -> /etc/systemd/system/ ==="
SYSTEMD_CHANGED=false
for unit in "$REPO_DIR"/systemd/*.service "$REPO_DIR"/systemd/*.timer; do
    local_name="$(basename "$unit")"
    dst="/etc/systemd/system/$local_name"

    # Check if this unit will be updated/new before deploying
    if [[ ! -f "$dst" ]] || ! diff -q "$unit" "$dst" &>/dev/null; then
        SYSTEMD_CHANGED=true
    fi

    deploy "$unit" "$dst" 644
done
if [[ "$SYSTEMD_CHANGED" == true && "$DRY_RUN" == false ]]; then
    systemctl daemon-reload
    echo "  -> systemctl daemon-reload"
fi
echo ""

echo "=== Configs -> /etc/ ==="
deploy "$REPO_DIR/configs/60-ioschedulers.rules"   "/etc/udev/rules.d/60-ioschedulers.rules" 644
deploy "$REPO_DIR/configs/99-gaming-network.conf"   "/etc/sysctl.d/99-gaming-network.conf"    644
deploy "$REPO_DIR/configs/clamd-scan.conf"          "/etc/clamd.d/scan.conf"                  644
deploy "$REPO_DIR/configs/gamemode.ini"             "/etc/gamemode.ini"                       644
deploy "$REPO_DIR/configs/clamav-scans-logrotate"   "/etc/logrotate.d/clamav-scans"           644
deploy "$REPO_DIR/configs/logrotate-system-health"  "/etc/logrotate.d/system-health"          644
echo ""

echo "=== Desktop files -> user directories ==="
# Clean up misplaced directory entry from earlier deployments
MISPLACED="$USER_HOME/.local/share/applications/security-directory.desktop"
if [[ -f "$MISPLACED" ]]; then
    if [[ "$DRY_RUN" == false ]]; then
        rm -f "$MISPLACED"
        echo "[CLEANUP]  Removed misplaced $MISPLACED"
    else
        echo "[CLEANUP]  Would remove misplaced $MISPLACED"
    fi
fi
for f in "$REPO_DIR"/desktop/security-*.desktop; do
    local_name="$(basename "$f")"
    # security-directory.desktop goes to desktop-directories (not applications/)
    if [[ "$local_name" == "security-directory.desktop" ]]; then
        deploy "$f" "$USER_HOME/.local/share/desktop-directories/$local_name" 644 "lch:lch"
    else
        deploy "$f" "$USER_HOME/.local/share/applications/$local_name" 644 "lch:lch"
    fi
done
deploy "$REPO_DIR/desktop/security.menu" \
    "$USER_HOME/.config/menus/applications-merged/security.menu" 644 "lch:lch"
deploy "$REPO_DIR/desktop/bazzite-security-tray.desktop" \
    "$USER_HOME/.config/autostart/bazzite-security-tray.desktop" 644 "lch:lch"
echo ""

echo "=== Tray app -> ~/security/ ==="
deploy "$REPO_DIR/tray/bazzite-security-tray.py" \
    "$USER_HOME/security/bazzite-security-tray.py" 755 "lch:lch"
deploy_dir "$REPO_DIR/tray/icons" "$USER_HOME/security/icons" "lch:lch"

# Link tray icons into standard user icon paths for KDE .desktop file resolution
# Icons go into both status/ (for tray) and apps/ (for application menu entries)
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "$USER_HOME/.local/share/icons/hicolor/scalable/status"
    mkdir -p "$USER_HOME/.local/share/icons/hicolor/scalable/apps"
    for svg in "$USER_HOME/security/icons/hicolor/scalable/status"/bazzite-sec-*.svg; do
        local_name="$(basename "$svg")"
        ln -sf "$svg" "$USER_HOME/.local/share/icons/hicolor/scalable/status/$local_name"
        ln -sf "$svg" "$USER_HOME/.local/share/icons/hicolor/scalable/apps/$local_name"
    done
    chown -R lch:lch "$USER_HOME/.local/share/icons/hicolor/scalable/status"
    chown -R lch:lch "$USER_HOME/.local/share/icons/hicolor/scalable/apps"
    # Create index.theme so KDE recognizes this as a valid icon directory
    cat > "$USER_HOME/.local/share/icons/hicolor/index.theme" <<'ICONTHEME'
[Icon Theme]
Name=Hicolor
Comment=Hicolor Icon Theme
Directories=scalable/status,scalable/apps

[scalable/status]
Size=48
Type=Scalable
MinSize=16
MaxSize=512
Context=Status

[scalable/apps]
Size=48
Type=Scalable
MinSize=16
MaxSize=512
Context=Applications
ICONTHEME
    chown lch:lch "$USER_HOME/.local/share/icons/hicolor/index.theme"
    # Rebuild icon cache so KDE picks up new/changed icons
    gtk-update-icon-cache -f -t "$USER_HOME/.local/share/icons/hicolor/" 2>/dev/null || true
    echo "[OK]       Symlinked tray icons into ~/.local/share/icons/hicolor/ (status + apps)"
else
    echo "[SYMLINK]  Tray icons -> ~/.local/share/icons/hicolor/scalable/{status,apps}/"
fi
echo ""

echo "=== Log directories ==="
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p /var/log/system-health
    chmod 755 /var/log/system-health
    echo "[OK]       /var/log/system-health/"
else
    echo "[MKDIR]    /var/log/system-health/"
fi
echo ""

echo "=== KDE cache rebuild ==="
if [[ "$DRY_RUN" == false ]]; then
    # Rebuild KDE's system configuration cache so new desktop entries and icons appear
    sudo -u lch kbuildsycoca6 2>/dev/null && echo "[OK]       kbuildsycoca6 rebuilt" \
        || echo "[SKIP]     kbuildsycoca6 not available"
else
    echo "[CACHE]    Would rebuild kbuildsycoca6"
fi
echo ""

echo "==============================="
echo "  Updated: $COUNT_UPDATED"
echo "  New:     $COUNT_NEW"
echo "  Skipped: $COUNT_SKIPPED (identical)"
echo "==============================="
if [[ "$DRY_RUN" == true ]]; then
    echo "(dry run — nothing was changed)"
fi
