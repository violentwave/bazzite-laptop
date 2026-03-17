#!/usr/bin/env python3
"""Bazzite Security Tray — PySide6/Qt6 replacement for the GTK3 tray."""

from __future__ import annotations

import ctypes
import fcntl
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure the tray directory and project root are importable
# regardless of working directory when launched as a script
_TRAY_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _TRAY_DIR.parent
for _p in (str(_TRAY_DIR), str(_PROJECT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

try:
    from tray.state_machine import (
        BLANK_ICON, LOG_DIR, SCAN_SCRIPT,
        HEALTHCHECK_SCRIPT, HEALTH_SNAPSHOT_SCRIPT, HEALTH_LOG,
        STATE_CONFIGS, STATE_HEALTHY_IDLE, STATE_SCAN_COMPLETE,
        STATE_UNKNOWN,
        determine_state, format_header, format_health_age,
        format_relative_time, icon_path,
    )
except ImportError:
    from state_machine import (
        BLANK_ICON, LOG_DIR, SCAN_SCRIPT,
        HEALTHCHECK_SCRIPT, HEALTH_SNAPSHOT_SCRIPT, HEALTH_LOG,
        STATE_CONFIGS, STATE_HEALTHY_IDLE, STATE_SCAN_COMPLETE,
        STATE_UNKNOWN,
        determine_state, format_header, format_health_age,
        format_relative_time, icon_path,
    )

LOCK_FILE = Path.home() / "security" / ".tray.lock"
POLL_INTERVAL_MS = 3000
SCAN_COMPLETE_TIMEOUT_MS = 30_000

try:
    ctypes.CDLL("libc.so.6").prctl(15, b"bazzite-security-tray", 0, 0, 0)
except Exception:
    pass

signal.signal(signal.SIGHUP, signal.SIG_IGN)


def _qicon(name: str) -> QIcon:
    return QIcon(str(icon_path(name)))


def _get_next_timer_fire(timer_name: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "show", timer_name, "--property=NextElapseUSecRealtime"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "=" in result.stdout:
            value = result.stdout.strip().split("=", 1)[1]
            if not value:
                return "Not scheduled"
            parts = value.rsplit(" ", 1)
            dt = datetime.strptime(parts[0], "%a %Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if dt.date() == now.date():
                return f"Today {dt.strftime('%I:%M %p').lstrip('0')}"
            delta = (dt.date() - now.date()).days
            if delta == 1:
                return f"Tomorrow {dt.strftime('%I:%M %p').lstrip('0')}"
            return dt.strftime("%a %b %d, %I:%M %p").lstrip("0")
    except Exception as exc:
        print(f"[tray] Timer query failed: {exc}", file=sys.stderr)
    return "Check systemctl"


def _konsole_run(cmd: str) -> None:
    """Run a command in a konsole terminal (for interactive/view commands)."""
    try:
        subprocess.Popen(
            ["konsole", "-e", "bash", "-c",
             f"{cmd}; echo 'Press Enter to close'; read"]
        )
    except Exception as exc:
        print(f"[tray] Action failed: {exc}", file=sys.stderr)


def _pkexec_run(*args: str) -> None:
    """Run a privileged command via pkexec (KDE graphical sudo dialog)."""
    try:
        subprocess.Popen(["pkexec"] + list(args))
    except FileNotFoundError:
        # Fallback to konsole+sudo if pkexec not available
        cmd = " ".join(args)
        _konsole_run(f"sudo {cmd}")
    except Exception as exc:
        print(f"[tray] Action failed: {exc}", file=sys.stderr)


class SecurityTrayQt:
    def __init__(self) -> None:
        self._current_state: str = STATE_UNKNOWN
        self._last_status_raw: bytes | None = None
        self._last_completion_timestamp: str | None = None
        self._status: dict = {}
        self._blink_visible: bool = True
        self._dashboard = None

        self._notification_enabled: bool = True

        self._tray = QSystemTrayIcon(_qicon(STATE_CONFIGS[STATE_UNKNOWN].icon))
        self._tray.setToolTip("Security: starting…")
        self._tray.activated.connect(self._on_activated)
        self._tray.messageClicked.connect(self._toggle_dashboard)

        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._blink_toggle)

        self._complete_timer = QTimer()
        self._complete_timer.setSingleShot(True)
        self._complete_timer.timeout.connect(self._transition_to_idle)

        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(POLL_INTERVAL_MS)

        self._build_menu()
        self._tray.show()
        self._poll_status()

    def _poll_status(self) -> None:
        try:
            try:
                from tray.state_machine import STATUS_FILE
            except ImportError:
                from state_machine import STATUS_FILE
            raw: bytes | None = None
            try:
                raw = STATUS_FILE.read_bytes()
            except Exception:
                pass

            file_changed = raw != self._last_status_raw

            if file_changed:
                self._last_status_raw = raw
                data = None
                if raw is not None:
                    import json
                    try:
                        data = json.loads(raw)
                    except Exception:
                        data = None

                self._status = data or {}
                new_state, new_ts = determine_state(
                    data, self._last_completion_timestamp
                )
                self._last_completion_timestamp = new_ts
                self._set_state(new_state)
                self._build_menu()

            # Always forward status to dashboard if visible
            # (refreshes relative timestamps and scan progress)
            if (self._dashboard is not None
                    and self._dashboard.isVisible()
                    and self._status):
                try:
                    self._dashboard.update_status(
                        self._status, self._current_state
                    )
                except Exception as exc:
                    print(
                        f"[tray] Dashboard update error: {exc}",
                        file=sys.stderr,
                    )
        except Exception as exc:
            print(f"[tray] Poll error: {exc}", file=sys.stderr)

    def _set_state(self, new_state: str) -> None:
        if new_state == self._current_state:
            return

        # Cancel blink if leaving a blinking state
        self._blink_timer.stop()

        # Cancel complete→idle timer if we're leaving SCAN_COMPLETE for something else
        if self._current_state == STATE_SCAN_COMPLETE and new_state != STATE_SCAN_COMPLETE:
            self._complete_timer.stop()

        self._current_state = new_state
        cfg = STATE_CONFIGS[new_state]
        self._blink_visible = True
        self._tray.setIcon(_qicon(cfg.icon))
        self._tray.setToolTip(f"Security: {cfg.description}")

        if cfg.blink and cfg.blink_interval_ms > 0:
            self._blink_timer.start(cfg.blink_interval_ms)

        if new_state == STATE_SCAN_COMPLETE:
            self._complete_timer.start(SCAN_COMPLETE_TIMEOUT_MS)

        if self._notification_enabled:
            self._show_state_notification(new_state)

    def _show_state_notification(self, state: str) -> None:
        """Show a system tray balloon notification for actionable state changes."""
        MI = QSystemTrayIcon.MessageIcon
        if state == "scan_complete":
            duration = self._status.get("duration", "")
            body = "ClamAV scan finished — no threats found"
            if duration:
                body += f" ({duration})"
            self._tray.showMessage("Scan Complete", body, MI.Information, 5000)
        elif state == "threats_found":
            count = self._status.get("threat_count", 0)
            self._tray.showMessage(
                "Threats Detected!",
                f"{count} threat(s) found and quarantined",
                MI.Critical,
                5000,
            )
        elif state == "scan_failed":
            self._tray.showMessage(
                "Scan Error",
                "ClamAV scan encountered an error",
                MI.Warning,
                5000,
            )
        elif state == "health_warning":
            issues = self._status.get("health_issues", 0)
            self._tray.showMessage(
                "Health Warning",
                f"{issues} system health issue(s) detected",
                MI.Warning,
                5000,
            )

    def _blink_toggle(self) -> None:
        self._blink_visible = not self._blink_visible
        cfg = STATE_CONFIGS[self._current_state]
        icon_name = cfg.icon if self._blink_visible else BLANK_ICON
        self._tray.setIcon(_qicon(icon_name))

    def _transition_to_idle(self) -> None:
        self._set_state(STATE_HEALTHY_IDLE)
        self._build_menu()

    def _build_menu(self) -> None:
        menu = QMenu()

        # 1. Status header (bold, disabled)
        header_text = format_header(self._current_state, self._status)
        header_action = menu.addAction(f"<b>{header_text}</b>")
        header_action.setEnabled(False)

        menu.addSeparator()

        # 2. Last scan info
        self._add_last_scan_items(menu)

        menu.addSeparator()

        # 3. Scheduled scans
        for timer_name, label in [("clamav-quick.timer", "Next quick"),
                                   ("clamav-deep.timer", "Next deep")]:
            next_time = _get_next_timer_fire(timer_name)
            a = menu.addAction(f"{label}: {next_time}")
            a.setEnabled(False)

        menu.addSeparator()

        # 4. System Health submenu
        health_menu = QMenu("System Health", menu)
        self._add_health_status_item(health_menu)
        health_menu.addSeparator()
        health_menu.addAction("Run Health Snapshot").triggered.connect(
            self._on_run_health_snapshot
        )
        health_menu.addAction("View Health Logs").triggered.connect(
            self._on_view_health_logs
        )
        menu.addMenu(health_menu)

        menu.addSeparator()

        # 5. Scan / check actions
        menu.addAction("Run Quick Scan").triggered.connect(self._on_run_quick)
        menu.addAction("Run Deep Scan").triggered.connect(self._on_run_deep)
        menu.addAction("Run Health Check").triggered.connect(self._on_run_healthcheck)
        menu.addAction("Run Test Scan").triggered.connect(self._on_run_test)
        menu.addAction("Run Test Suite").triggered.connect(self._on_run_suite)

        menu.addSeparator()

        # 6. View / quarantine
        menu.addAction("View Quarantine").triggered.connect(self._on_view_quarantine)
        menu.addAction("Release from Quarantine").triggered.connect(
            self._on_release_quarantine
        )
        menu.addAction("View Scan Logs").triggered.connect(self._on_view_logs)

        menu.addSeparator()

        # 7. Notifications toggle + dashboard + quit
        notif_action = menu.addAction("Enable Notifications")
        notif_action.setCheckable(True)
        notif_action.setChecked(self._notification_enabled)
        notif_action.triggered.connect(self._on_toggle_notifications)
        menu.addAction("Show Dashboard").triggered.connect(self._toggle_dashboard)
        menu.addAction("Quit").triggered.connect(QApplication.quit)

        self._tray.setContextMenu(menu)

    def _add_last_scan_items(self, menu: QMenu) -> None:
        scan_type = self._status.get("scan_type", "")
        result = self._status.get("result", "")
        files_scanned = self._status.get("files_scanned", 0)
        duration = self._status.get("duration", "")
        time_str = self._status.get("last_scan_time") or self._status.get("timestamp", "")
        display_time = format_relative_time(time_str)

        if scan_type:
            a = menu.addAction(f"Last: {scan_type.title()} scan \u00b7 {display_time}")
        else:
            a = menu.addAction("Last: No scan recorded")
        a.setEnabled(False)

        if result == "clean":
            a = menu.addAction(f"Result: \u2713 Clean ({files_scanned:,} files)")
        elif result == "threats":
            threat_count = self._status.get("threat_count", 0)
            a = menu.addAction(f"Result: \u2717 {threat_count} threat(s) ({files_scanned:,} files)")
        elif result == "error":
            a = menu.addAction("Result: Error during scan")
        else:
            a = menu.addAction("Result: Unknown")
        a.setEnabled(False)

        if duration:
            a = menu.addAction(f"Duration: {duration}")
            a.setEnabled(False)

    def _add_health_status_item(self, menu: QMenu) -> None:
        health_status = self._status.get("health_status", "")
        health_issues = self._status.get("health_issues", 0)
        health_warnings = self._status.get("health_warnings", 0)
        health_critical = self._status.get("health_critical", 0)
        health_last = self._status.get("health_last_check", "")

        if not health_status:
            text = "No health data yet"
        else:
            age_str = format_health_age(health_last)
            if health_status == "OK":
                text = f"\u2713 All OK \u2014 {age_str}"
            elif health_status == "CRITICAL":
                text = (
                    f"\u2717 {health_critical} critical,"
                    f" {health_warnings} warnings \u2014 {age_str}"
                )
            else:
                text = f"\u26a0 {health_issues} issue(s) \u2014 {age_str}"

        a = menu.addAction(text)
        a.setEnabled(False)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_dashboard()

    def _toggle_dashboard(self) -> None:
        if self._dashboard is None:
            try:
                try:
                    from tray.dashboard_window import DashboardWindow
                except ImportError:
                    from dashboard_window import DashboardWindow
                self._dashboard = DashboardWindow()
                # Push current status immediately
                if self._status and self._current_state:
                    self._dashboard.update_status(self._status, self._current_state)
            except Exception as exc:
                print(f"[tray] Dashboard unavailable: {exc}", file=sys.stderr)
                return

        if self._dashboard.isVisible():
            self._dashboard.hide()
        else:
            # Refresh status when showing
            if self._status and self._current_state:
                self._dashboard.update_status(self._status, self._current_state)
            self._dashboard.show()
            self._dashboard.raise_()
            self._dashboard.activateWindow()

    def _on_run_quick(self) -> None:
        _pkexec_run(SCAN_SCRIPT, "quick")

    def _on_run_deep(self) -> None:
        _pkexec_run(SCAN_SCRIPT, "deep")

    def _on_run_test(self) -> None:
        _pkexec_run(SCAN_SCRIPT, "test")

    def _on_run_suite(self) -> None:
        _pkexec_run("/usr/local/bin/bazzite-security-test.sh")

    def _on_run_healthcheck(self) -> None:
        _pkexec_run(HEALTHCHECK_SCRIPT)

    def _on_run_health_snapshot(self) -> None:
        _pkexec_run(HEALTH_SNAPSHOT_SCRIPT)

    def _on_view_health_logs(self) -> None:
        try:
            subprocess.Popen(
                ["konsole", "-e", "less", str(HEALTH_LOG)]
            )
        except Exception as exc:
            print(f"[tray] Action failed: {exc}", file=sys.stderr)

    def _on_view_quarantine(self) -> None:
        _pkexec_run(
            "/usr/local/bin/quarantine-release.sh", "--list"
        )

    def _on_release_quarantine(self) -> None:
        _pkexec_run(
            "/usr/local/bin/quarantine-release.sh", "--interactive"
        )

    def _on_view_logs(self) -> None:
        try:
            subprocess.Popen(["dolphin", str(LOG_DIR)])
        except Exception as exc:
            print(f"[tray] Action failed: {exc}", file=sys.stderr)

    def _on_toggle_notifications(self, checked: bool) -> None:
        self._notification_enabled = checked


def acquire_lock() -> object:
    """Prevent multiple tray instances via exclusive file lock."""
    lock_fd = open(LOCK_FILE, "w")  # noqa: SIM115
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd  # keep reference alive so lock persists
    except BlockingIOError:
        print("[tray] Another instance is already running", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    _lock = acquire_lock()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running when dashboard closes

    signal.signal(signal.SIGTERM, lambda _s, _f: app.quit())

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("[tray] No system tray available", file=sys.stderr)
        sys.exit(1)

    tray = SecurityTrayQt()
    sys.exit(app.exec())
