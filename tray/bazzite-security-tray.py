#!/usr/bin/env python3
# Bazzite Security Tray — system tray monitor for ClamAV scan status
# Deploy to: /home/lch/security/bazzite-security-tray.py (chmod 755)
# Icons deployed to: /home/lch/security/icons/
# Reads ~/security/.status (JSON) and shows a colored shield icon in the KDE system tray.

import signal
import ctypes
import fcntl
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Set process title so "pkill clamscan" won't kill us (pkill uses substring matching)
try:
    libc = ctypes.CDLL('libc.so.6')
    title = b'bazzite-security-tray'
    libc.prctl(15, title, 0, 0, 0)  # PR_SET_NAME = 15
except Exception:  # noqa: S110
    pass

signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

STATUS_FILE = Path.home() / "security" / ".status"
LOCK_FILE = Path.home() / "security" / ".tray.lock"
POLL_INTERVAL = 3  # seconds
ICON_THEME_PATH = str(Path.home() / "security" / "icons")

SCAN_SCRIPT = "/usr/local/bin/clamav-scan.sh"
HEALTHCHECK_SCRIPT = "/usr/local/bin/clamav-healthcheck.sh"
HEALTH_SNAPSHOT_SCRIPT = "/usr/local/bin/system-health-snapshot.sh"
HEALTH_LOG = "/var/log/system-health/health-latest.log"
QUARANTINE_DIR = str(Path.home() / "security" / "quarantine")
LOG_DIR = "/var/log/clamav-scans"

# --- Icon state machine ---

STATE_HEALTHY_IDLE = "healthy_idle"
STATE_SCAN_RUNNING = "scan_running"
STATE_SCAN_COMPLETE = "scan_complete"
STATE_WARNING = "warning"
STATE_SCAN_FAILED = "scan_failed"
STATE_SCAN_ABORTED = "scan_aborted"
STATE_THREATS_FOUND = "threats_found"
STATE_HEALTH_WARNING = "health_warning"
STATE_UNKNOWN = "unknown"

STATE_CONFIG = {
    STATE_HEALTHY_IDLE: {
        "icon": "bazzite-sec-green", "desc": "All clear", "blink": False,
    },
    STATE_SCAN_RUNNING: {
        "icon": "bazzite-sec-teal", "desc": "Scan in progress",
        "blink": True, "interval": 1000,
    },
    STATE_SCAN_COMPLETE: {
        "icon": "bazzite-sec-blue", "desc": "Scan complete",
        "blink": True, "interval": 500,
    },
    STATE_WARNING: {
        "icon": "bazzite-sec-yellow", "desc": "Warning", "blink": False,
    },
    STATE_SCAN_FAILED: {
        "icon": "bazzite-sec-red", "desc": "Scan error", "blink": False,
    },
    STATE_SCAN_ABORTED: {
        "icon": "bazzite-sec-red", "desc": "Scan aborted",
        "blink": True, "interval": 500,
    },
    STATE_THREATS_FOUND: {
        "icon": "bazzite-sec-red", "desc": "Threats found",
        "blink": True, "interval": 1000,
    },
    STATE_HEALTH_WARNING: {
        "icon": "bazzite-sec-health-warn",
        "desc": "Health warnings detected", "blink": False,
    },
    STATE_UNKNOWN: {
        "icon": "bazzite-sec-yellow", "desc": "Status unknown",
        "blink": False,
    },
}

MENU_HEADERS = {
    STATE_HEALTHY_IDLE:  "\u25cf All clear",
    STATE_SCAN_RUNNING:  "\u25cf Scan running...",
    STATE_SCAN_COMPLETE: "\u25cf Scan complete \u2014 log updated",
    STATE_WARNING:       "\u26a0 Warning \u2014 check signatures",
    STATE_SCAN_FAILED:   "\u2717 Scan error",
    STATE_SCAN_ABORTED:  "\u2717 Scan aborted",
    STATE_THREATS_FOUND: "\u2717 {count} threat(s) found",
    STATE_HEALTH_WARNING: "\u26a0 System health: {issues} warning(s)",
    STATE_UNKNOWN:       "? Status unknown",
}


class SecurityTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "bazzite-security",
            "bazzite-sec-yellow",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_icon_theme_path(ICON_THEME_PATH)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self.current_state = None
        self.current_icon = "bazzite-sec-yellow"
        self.current_description = "Starting"
        self.blink_timer_id = None
        self.blink_visible = True
        self.complete_timer_id = None
        self.last_status_raw = None
        self.last_completion_timestamp = None
        self.status = {}

        self.set_state(STATE_UNKNOWN)

        # Force GTK to process events so the icon renders immediately
        while Gtk.events_pending():
            Gtk.main_iteration()

        self.build_menu()
        GLib.timeout_add_seconds(POLL_INTERVAL, self.poll)

    # --- State machine ---

    def set_state(self, new_state):
        if new_state == self.current_state:
            return

        # Cancel existing blink timer
        if self.blink_timer_id is not None:
            GLib.source_remove(self.blink_timer_id)
            self.blink_timer_id = None

        # Cancel complete→idle timer if changing away from SCAN_COMPLETE
        if self.current_state == STATE_SCAN_COMPLETE and new_state != STATE_SCAN_COMPLETE:
            if self.complete_timer_id is not None:
                GLib.source_remove(self.complete_timer_id)
                self.complete_timer_id = None

        self.current_state = new_state
        cfg = STATE_CONFIG[new_state]
        self.current_icon = cfg["icon"]
        self.current_description = cfg["desc"]
        self.blink_visible = True

        # Force AppIndicator3 to refresh (it caches by icon name)
        self.indicator.set_icon_full("", self.current_description)
        self.indicator.set_icon_full(self.current_icon, self.current_description)

        # Start blink timer if needed
        if cfg["blink"]:
            self.blink_timer_id = GLib.timeout_add(cfg["interval"], self._blink_toggle)

        # Schedule transition back to idle after SCAN_COMPLETE
        if new_state == STATE_SCAN_COMPLETE:
            self.complete_timer_id = GLib.timeout_add_seconds(30, self._transition_to_idle)

    def _blink_toggle(self):
        self.blink_visible = not self.blink_visible
        if self.blink_visible:
            self.indicator.set_icon_full(self.current_icon, self.current_description)
        else:
            self.indicator.set_icon_full("bazzite-sec-blank", self.current_description)
        return True

    def _transition_to_idle(self):
        self.complete_timer_id = None
        self.set_state(STATE_HEALTHY_IDLE)
        self.build_menu()
        return False

    # --- Status reading ---

    def read_status_file(self):
        try:
            text = STATUS_FILE.read_text(encoding="utf-8")
            return json.loads(text)
        except Exception:
            return None

    def determine_state(self, data):
        if data is None:
            return STATE_UNKNOWN

        state = data.get("state", "")
        result = data.get("result", "")

        if state in ("scanning", "updating"):
            return STATE_SCAN_RUNNING
        elif state == "complete":
            if result == "clean":
                timestamp = data.get("last_scan_time") or data.get("timestamp", "")
                if timestamp and timestamp != self.last_completion_timestamp:
                    self.last_completion_timestamp = timestamp
                    return STATE_SCAN_COMPLETE
                else:
                    return self._check_health_overlay(data)
            elif result == "threats":
                return STATE_THREATS_FOUND
            elif result == "error":
                return STATE_SCAN_FAILED
            else:
                return self._check_health_overlay(data)
        elif state == "idle":
            last = data.get("last_scan_result", "")
            if last == "threats":
                return STATE_THREATS_FOUND
            elif last == "error":
                return STATE_SCAN_FAILED
            else:
                return self._check_health_overlay(data)
        else:
            return STATE_UNKNOWN

    def _check_health_overlay(self, data):
        """When ClamAV is idle/healthy, check if health monitoring has warnings."""
        health = data.get("health_status", "")
        if not isinstance(health, str):
            return STATE_HEALTHY_IDLE
        if health.upper() in ("WARNING", "CRITICAL"):
            return STATE_HEALTH_WARNING
        return STATE_HEALTHY_IDLE

    def poll(self):
        try:
            raw = None
            try:
                raw = STATUS_FILE.read_bytes()
            except Exception:  # noqa: S110
                pass

            if raw != self.last_status_raw:
                self.last_status_raw = raw
                data = None
                if raw is not None:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        data = None
                self.status = data or {}
                new_state = self.determine_state(data)
                self.set_state(new_state)
                self.build_menu()
        except Exception as e:
            print(f"Poll error: {e}", file=sys.stderr)
        return True

    # --- Menu building ---

    def build_menu(self):
        menu = Gtk.Menu()

        # 1. Status header
        header = self._make_status_header()
        menu.append(header)

        # 2. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 3. Last scan info
        for item in self._make_last_scan_items():
            menu.append(item)

        # 4. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 5. Scheduled scans
        for item in self._make_schedule_items():
            menu.append(item)

        # 6. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 6b. System Health submenu
        health_submenu = Gtk.Menu()

        # Health status line
        health_status_item = self._make_health_status_item()
        health_submenu.append(health_status_item)
        health_submenu.append(Gtk.SeparatorMenuItem())

        # Run Health Snapshot
        item_health_snap = Gtk.MenuItem(label="Run Health Snapshot")
        item_health_snap.connect("activate", self._on_run_health_snapshot)
        health_submenu.append(item_health_snap)

        # View Health Logs
        item_health_logs = Gtk.MenuItem(label="View Health Logs")
        item_health_logs.connect("activate", self._on_view_health_logs)
        health_submenu.append(item_health_logs)

        health_menu_item = Gtk.MenuItem(label="System Health")
        health_menu_item.set_submenu(health_submenu)
        menu.append(health_menu_item)

        # 6c. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 7. Action buttons
        item_quick = Gtk.MenuItem(label="Run Quick Scan")
        item_quick.connect("activate", self._on_run_quick)
        menu.append(item_quick)

        item_deep = Gtk.MenuItem(label="Run Deep Scan")
        item_deep.connect("activate", self._on_run_deep)
        menu.append(item_deep)

        item_health = Gtk.MenuItem(label="Run Health Check")
        item_health.connect("activate", self._on_run_healthcheck)
        menu.append(item_health)

        item_test = Gtk.MenuItem(label="Run Test Scan")
        item_test.connect("activate", self._on_run_test)
        menu.append(item_test)

        item_suite = Gtk.MenuItem(label="Run Test Suite")
        item_suite.connect("activate", self._on_run_suite)
        menu.append(item_suite)

        # 8. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 9. View items
        item_quarantine = Gtk.MenuItem(label="View Quarantine")
        item_quarantine.connect("activate", self._on_view_quarantine)
        menu.append(item_quarantine)

        item_release = Gtk.MenuItem(label="Release from Quarantine")
        item_release.connect("activate", self._on_release_quarantine)
        menu.append(item_release)

        item_logs = Gtk.MenuItem(label="View Scan Logs")
        item_logs.connect("activate", self._on_view_logs)
        menu.append(item_logs)

        # 10. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 11. Quit
        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", self._on_quit)
        menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)

    def _make_status_header(self):
        state = self.current_state or STATE_UNKNOWN
        threat_count = self.status.get("threat_count", 0)

        header_template = MENU_HEADERS.get(state, MENU_HEADERS[STATE_UNKNOWN])
        if state == STATE_THREATS_FOUND:
            count = threat_count if threat_count else "?"
            header_text = header_template.format(count=count)
        elif state == STATE_HEALTH_WARNING:
            issues = self.status.get("health_issues", 0)
            header_text = header_template.format(issues=issues if issues else "?")
        else:
            header_text = header_template

        item = Gtk.MenuItem()
        item.set_sensitive(False)
        label_widget = Gtk.Label()
        label_widget.set_markup(f"<b>{GLib.markup_escape_text(header_text)}</b>")
        label_widget.set_halign(Gtk.Align.START)
        item.add(label_widget)
        return item

    def _make_last_scan_items(self):
        items = []
        scan_type = self.status.get("scan_type", "")
        result = self.status.get("result", "")
        files_scanned = self.status.get("files_scanned", 0)
        duration = self.status.get("duration", "")
        last_scan_time = self.status.get("last_scan_time", "")
        timestamp = self.status.get("timestamp", "")

        time_str = last_scan_time or timestamp
        display_time = self._format_scan_time(time_str)

        if scan_type:
            items.append(self._info_item(
                f"Last: {scan_type.title()} scan \u00b7 {display_time}"
            ))
        else:
            items.append(self._info_item("Last: No scan recorded"))

        if result == "clean":
            items.append(self._info_item(
                f"Result: \u2713 Clean ({files_scanned:,} files)"
            ))
        elif result == "threats":
            threat_count = self.status.get("threat_count", 0)
            items.append(self._info_item(
                f"Result: \u2717 {threat_count} threat(s) ({files_scanned:,} files)"
            ))
        elif result == "error":
            items.append(self._info_item("Result: Error during scan"))
        elif not self.status:
            items.append(self._info_item("Result: Unknown"))

        if duration:
            items.append(self._info_item(f"Duration: {duration}"))

        return items

    def _make_schedule_items(self):
        items = []
        for timer_name, label in [("clamav-quick.timer", "Next quick"),
                                   ("clamav-deep.timer", "Next deep")]:
            next_time = self._get_next_timer_fire(timer_name)
            items.append(self._info_item(f"{label}: {next_time}"))
        return items

    def _info_item(self, text):
        item = Gtk.MenuItem(label=text)
        item.set_sensitive(False)
        return item

    def _make_health_status_item(self):
        health_status = self.status.get("health_status", "")
        health_issues = self.status.get("health_issues", 0)
        health_warnings = self.status.get("health_warnings", 0)
        health_critical = self.status.get("health_critical", 0)
        health_last = self.status.get("health_last_check", "")

        if not health_status:
            text = "No health data yet"
        else:
            age_str = self._format_health_age(health_last)
            if health_status == "OK":
                text = f"\u2713 All OK \u2014 {age_str}"
            elif health_status == "CRITICAL":
                text = (
                    f"\u2717 {health_critical} critical,"
                    f" {health_warnings} warnings \u2014 {age_str}"
                )
            else:
                text = f"\u26a0 {health_issues} issue(s) \u2014 {age_str}"

        return self._info_item(text)

    def _format_health_age(self, timestamp_str):
        if not timestamp_str:
            return "unknown"
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %I:%M %p")
            delta = datetime.now() - dt
            hours = int(delta.total_seconds() / 3600)
            if hours < 1:
                return "just now"
            elif hours < 24:
                return f"{hours}h ago"
            else:
                days = hours // 24
                return f"{days}d ago"
        except Exception:
            return timestamp_str

    def _format_scan_time(self, iso_str):
        if not iso_str:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(iso_str)
            now = datetime.now()
            if dt.date() == now.date():
                return f"Today {dt.strftime('%I:%M %p').lstrip('0')}"
            delta = (now.date() - dt.date()).days
            if delta == 1:
                return f"Yesterday {dt.strftime('%I:%M %p').lstrip('0')}"
            return dt.strftime("%b %d, %I:%M %p").lstrip("0")
        except Exception:
            return iso_str

    def _get_next_timer_fire(self, timer_name):
        try:
            result = subprocess.run(
                ["systemctl", "show", timer_name,
                 "--property=NextElapseUSecRealtime"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "=" in result.stdout:
                value = result.stdout.strip().split("=", 1)[1]
                if not value:
                    return "Not scheduled"
                try:
                    parts = value.rsplit(" ", 1)
                    dt = datetime.strptime(parts[0], "%a %Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    if dt.date() == now.date():
                        return f"Today {dt.strftime('%I:%M %p').lstrip('0')}"
                    delta = (dt.date() - now.date()).days
                    if delta == 1:
                        return f"Tomorrow {dt.strftime('%I:%M %p').lstrip('0')}"
                    return dt.strftime("%a %b %d, %I:%M %p").lstrip("0")
                except Exception:
                    return value
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)
        return "Check systemctl"

    # --- Action handlers ---

    def _on_run_quick(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 f"sudo {SCAN_SCRIPT} quick; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_run_deep(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 f"sudo {SCAN_SCRIPT} deep; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_run_test(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 f"sudo {SCAN_SCRIPT} test; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_run_suite(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 "sudo /usr/local/bin/bazzite-security-test.sh; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_run_health_snapshot(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 f"sudo {HEALTH_SNAPSHOT_SCRIPT}; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_view_health_logs(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 f"less {HEALTH_LOG}; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_run_healthcheck(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 f"sudo {HEALTHCHECK_SCRIPT}; echo 'Press Enter to close'; read"])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_view_quarantine(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 "sudo /usr/local/bin/quarantine-release.sh --list; echo 'Press Enter to close'; read"])  # noqa: E501
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_release_quarantine(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "bash", "-c",
                 "sudo /usr/local/bin/quarantine-release.sh --interactive; echo 'Press Enter to close'; read"])  # noqa: E501
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_view_logs(self, _widget):
        try:
            subprocess.Popen(["dolphin", LOG_DIR])
        except Exception as e:
            print(f"[tray] Action failed: {e}", file=sys.stderr)

    def _on_quit(self, _widget):
        Gtk.main_quit()


def acquire_lock():
    """Prevent multiple tray instances via file lock."""
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd  # Keep reference alive so lock persists
    except BlockingIOError:
        print("[tray] Another instance is already running", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    _lock = acquire_lock()
    tray = SecurityTray()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
