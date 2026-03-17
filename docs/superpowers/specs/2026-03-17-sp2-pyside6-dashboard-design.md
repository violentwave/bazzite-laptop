# SP2: PySide6 Dashboard + Tray — Design Spec

## Overview
Replace the broken GTK3/AppIndicator3 tray app with native PySide6 (Qt6) on Bazzite OS (KDE Plasma 6). Add a tabbed dashboard window accessible from the tray.

## Approach
**Tray-First (Option A):** Drop-in replacement of the tray icon, then incremental dashboard.

## Architecture

### File Structure
```
tray/
  security_tray_qt.py      # PySide6 tray (replaces bazzite-security-tray.py)
  dashboard_window.py       # QMainWindow with QTabWidget
  state_machine.py          # Extracted state logic (shared)
  __init__.py
```

### Data Flow
```
~/security/.status (JSON, written by ClamAV scripts + health monitor)
        │
        ▼
  state_machine.py ──► SecurityTrayQt (icon color, blink, tooltip)
        │                     │
        ▼                     ▼ (left-click)
  DashboardWindow        QSystemTrayIcon
  (live label updates)   (right-click menu)
```

### State Machine (unchanged contract)
9 states: healthy_idle, scan_running, scan_complete, warning, scan_failed, scan_aborted, threats_found, health_warning, unknown.

Each state maps to: icon name, description, blink (bool), blink interval (ms).

State triggers: `state="scanning"` OR `state="updating"` → scan_running. `state="complete"` checks `result` field. `state="idle"` checks `last_scan_result`. Health overlay: `health_status` in ("WARNING","CRITICAL") case-insensitive → health_warning.

Auto-transition: `scan_complete` → `healthy_idle` after 30 seconds. Timer cancelled if state changes before timeout.

`.status` JSON contract (keys used):
- `state`: "idle"|"scanning"|"updating"|"complete"
- `result`: "clean"|"threats"|"error"|""
- `last_scan_result`: same values as result
- `scan_type`, `files_scanned`, `duration`, `threat_count`, `timestamp`, `last_scan_time`
- `health_status`: "OK"|"WARNING"|"CRITICAL"
- `health_issues`, `health_warnings`, `health_critical`, `health_last_check`, `health_log`

Extracted into `state_machine.py` so both tray and dashboard can consume it.

### Tray Component (`security_tray_qt.py`)
- `QApplication.setQuitOnLastWindowClosed(False)` — CRITICAL: prevents dashboard close from killing tray
- `QSystemTrayIcon` with `QMenu` (right-click)
- Left-click → toggle dashboard (via `activated` signal with `Trigger` reason). NOTE: unreliable on Wayland — "Show Dashboard" menu item is the primary access path, left-click is a bonus
- `QTimer` for `.status` polling (3s) and icon blinking
- File lock via `fcntl.flock` (same as current). Stale lock handling: check if PID in lock file is alive before failing
- Process title set via `ctypes.CDLL('libc.so.6').prctl()`
- Icons loaded as `QIcon(absolute_svg_path)` — no theme names
- All `subprocess.Popen` calls use list-form (never `shell=True`)
- `scan_complete → healthy_idle` auto-transition after 30 seconds via `QTimer.singleShot`

Menu items (same as current):
- Status header (disabled, bold)
- Last scan info
- Scheduled scans (next quick/deep from systemctl)
- System Health submenu
- Run Quick/Deep/Test Scan, Health Check, Test Suite
- View Quarantine, Release, View Logs
- Show Dashboard / Quit

### Dashboard Window (`dashboard_window.py`)
- `QMainWindow` with `QTabWidget`
- Initially 3 tabs: Security, Health, About
- Future tabs: Gaming (SP5), AI (later)
- Follows KDE dark/light theme via `QPalette` auto-detection
- Closes to tray (doesn't quit app)
- Window geometry saved/restored via `QSettings("BazziteSecurity", "Dashboard")`

**Security tab:**
- Shield status icon + state label
- Last scan: type, time (relative), result, file count
- Next scheduled scans
- Action buttons: Quick Scan, Deep Scan, View Logs
- Quarantine count + view button

**Health tab:**
- Parses `health-latest.log` for display
- GPU temp, CPU thermals, SMART status, ZRAM, storage
- Health warnings highlighted
- "Run Snapshot" button

**About tab:**
- App version, system info (Bazzite version, kernel)
- Links: GitHub repo, docs

### Icon Handling
- All 7 SVGs loaded from absolute paths: `~/security/icons/*.svg`
- `QIcon.fromTheme()` NOT used — absolute paths only
- Blink: alternate between state icon and `bazzite-sec-blank.svg` via `QTimer`
- Tray tooltip: `QSystemTrayIcon.setToolTip(state_description)`

## Bazzite OS Constraints
- PySide6 installed via `uv pip install PySide6` in `.venv/`
- No `rpm-ostree`, no system packages, no `sudo` in the app
- All scan/health actions launch `konsole -e bash -c "sudo ..."`
- Launcher script: `scripts/start-security-tray-qt.sh` (absolute paths, matches existing `start-security-tray.sh` pattern)
- `.desktop` autostart Exec points to launcher script with absolute path
- `uv pip install` needs `UV_CACHE_DIR=/tmp/uv-cache` on Bazzite (read-only home cache)
- Icons use absolute paths (fixes KDE icon resolution bug)

## Deployment (Two-Phase)
**Phase A (Claude Code):**
- Create `tray/state_machine.py`, `tray/security_tray_qt.py`, `tray/dashboard_window.py`
- Create `tests/test_tray_state_machine.py`
- Create `scripts/start-security-tray-qt.sh` (launcher with absolute paths)
- Install PySide6: `UV_CACHE_DIR=/tmp/uv-cache uv pip install PySide6`
- Update `desktop/bazzite-security-tray.desktop` Icon= to absolute SVG path
- Add PySide6 to `requirements.txt`

**Phase B (User manually):**
- Copy new tray files to `~/security/`
- Copy launcher: `sudo cp scripts/start-security-tray-qt.sh /usr/local/bin/`
- Kill old GTK tray: `pkill -f bazzite-security-tray.py`
- Remove stale lock if needed: `rm -f ~/security/.tray.lock`
- Start new Qt tray: `/usr/local/bin/start-security-tray-qt.sh`
- Update autostart `.desktop` Exec to new launcher path

## Rollback
Old `bazzite-security-tray.py` remains in repo untouched. Revert autostart `.desktop` to switch back.

## Testing
- `tests/test_tray_state_machine.py`: All 9 state transitions (incl. `updating`), health overlay (OK/WARNING/CRITICAL/non-string/missing), icon mapping, blink config, 30s auto-transition, format helpers (relative time, health age), JSON parse failures (None data), stale lock detection
- `tests/test_dashboard_window.py` (future): smoke test with `QT_QPA_PLATFORM=offscreen` to verify 3 tabs exist
- Manual smoke: start tray → verify icon → trigger scan → verify state changes → open dashboard
- Verify on Bazzite: KDE theme detection, icon rendering, konsole launch
- Test under both X11 and Wayland sessions (left-click behavior differs)

## Known Limitations
- SVG icon colors are hardcoded — may be hard to see on light KDE panel themes. Acceptable for now; mitigation in SP3 (add white stroke to SVGs)
- PySide6 bundles its own Qt6 libs (~236MB). Potential D-Bus conflict with system Qt6 — if tray icon fails to appear, try `QT_QPA_PLATFORM=xcb` in launcher script
- `QSystemTrayIcon.activated` left-click signal unreliable on Wayland — "Show Dashboard" menu item is the reliable fallback

## Success Criteria
1. Tray icon renders correctly on KDE Plasma 6 (no GTK compatibility bridge)
2. All 9 states produce correct icon + tooltip
3. Right-click menu matches current functionality
4. Left-click opens/closes dashboard window
5. Dashboard shows live security + health status
6. No impact on gaming performance (PySide6 app is <30MB RAM idle)
7. Native KDE icons (Bitwarden, etc.) no longer broken by custom icon theme
