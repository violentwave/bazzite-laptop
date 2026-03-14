#!/usr/bin/env python3
# Bazzite Security Tray — system tray monitor for ClamAV scan status
# Deploy to: /home/lch/security/bazzite-security-tray.py (chmod 755)
# Reads ~/security/.status (JSON) and shows a colored shield icon in the KDE system tray.

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

STATUS_FILE = Path.home() / "security" / ".status"
POLL_INTERVAL = 3  # seconds

SCAN_SCRIPT = "/usr/local/bin/clamav-scan.sh"
HEALTHCHECK_SCRIPT = "/usr/local/bin/clamav-healthcheck.sh"
QUARANTINE_DIR = str(Path.home() / "security" / "quarantine")
LOG_DIR = "/var/log/clamav-scans"


class SecurityTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "bazzite-security",
            "dialog-warning",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.last_status_raw = None
        self.status = {}
        self.update_status()
        self.build_menu()
        GLib.timeout_add_seconds(POLL_INTERVAL, self.poll)

    # --- Status reading ---

    def read_status_file(self):
        """Read and parse the JSON status file. Returns dict or None."""
        try:
            text = STATUS_FILE.read_text(encoding="utf-8")
            return json.loads(text)
        except Exception:
            return None

    def update_status(self):
        """Read status file and update the tray icon."""
        data = self.read_status_file()
        if data is None:
            self.status = {}
            self.indicator.set_icon_full("dialog-warning", "Status unknown")
            return

        self.status = data
        state = data.get("state", "")
        result = data.get("result", "")
        last_result = data.get("last_scan_result", "")

        if state in ("updating", "scanning"):
            self.indicator.set_icon_full("security-medium", "Scan in progress")
        elif state in ("idle", "complete"):
            if result == "threats":
                self.indicator.set_icon_full("security-low", "Threats found")
            elif result == "error":
                self.indicator.set_icon_full("dialog-warning", "Scan error")
            elif result == "clean" or last_result == "clean":
                self.indicator.set_icon_full("security-high", "All clear")
            else:
                self.indicator.set_icon_full("security-high", "Idle")
        else:
            self.indicator.set_icon_full("dialog-warning", "Status unknown")

    def poll(self):
        """Poll the status file and rebuild menu if changed."""
        try:
            raw = None
            try:
                raw = STATUS_FILE.read_bytes()
            except Exception:
                pass

            if raw != self.last_status_raw:
                self.last_status_raw = raw
                self.update_status()
                self.build_menu()
        except Exception as e:
            print(f"Poll error: {e}", file=sys.stderr)
        return True  # keep polling

    # --- Menu building ---

    def build_menu(self):
        """Build the full right-click context menu."""
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

        # 8. Separator
        menu.append(Gtk.SeparatorMenuItem())

        # 9. View items
        item_quarantine = Gtk.MenuItem(label="View Quarantine")
        item_quarantine.connect("activate", self._on_view_quarantine)
        menu.append(item_quarantine)

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
        """Create the status header menu item with bold markup."""
        state = self.status.get("state", "")
        result = self.status.get("result", "")
        threat_count = self.status.get("threat_count", 0)

        if not self.status:
            text = "<b>\u25cf Status Unknown</b>"
        elif state in ("updating", "scanning"):
            scan_type = self.status.get("scan_type", "")
            current = self.status.get("current_dir", "")
            label = f"Scanning {current}..." if current else f"{scan_type.title()} scan running..."
            text = f"<b>\u25cf {label}</b>"
        elif result == "threats":
            count = threat_count if threat_count else "?"
            text = f"<b>\u25cf {count} Threat(s) Found</b>"
        elif result == "error":
            text = "<b>\u25cf Scan Error</b>"
        elif result == "clean":
            text = "<b>\u25cf Idle \u2014 All Clear</b>"
        else:
            text = "<b>\u25cf Idle</b>"

        item = Gtk.MenuItem()
        item.set_sensitive(False)
        label_widget = item.get_child()
        if label_widget:
            label_widget.set_markup(text)
        else:
            label_widget = Gtk.Label()
            label_widget.set_markup(text)
            label_widget.set_halign(Gtk.Align.START)
            item.add(label_widget)
        return item

    def _make_last_scan_items(self):
        """Create info items showing last scan details."""
        items = []
        scan_type = self.status.get("scan_type", "")
        result = self.status.get("result", "")
        files_scanned = self.status.get("files_scanned", 0)
        duration = self.status.get("duration", "")
        last_scan_time = self.status.get("last_scan_time", "")
        timestamp = self.status.get("timestamp", "")

        # Use last_scan_time if available, otherwise timestamp
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
        """Create items showing next scheduled scan times."""
        items = []
        for timer_name, label in [("clamav-quick.timer", "Next quick"),
                                   ("clamav-deep.timer", "Next deep")]:
            next_time = self._get_next_timer_fire(timer_name)
            items.append(self._info_item(f"{label}: {next_time}"))
        return items

    def _info_item(self, text):
        """Create a non-clickable informational menu item."""
        item = Gtk.MenuItem(label=text)
        item.set_sensitive(False)
        return item

    def _format_scan_time(self, iso_str):
        """Format an ISO timestamp to a friendly display string."""
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
        """Get the next fire time for a systemd timer."""
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
                # systemctl returns something like "Thu 2026-03-19 12:00:00 EDT"
                try:
                    # Try to parse and reformat
                    # Strip timezone abbreviation for parsing
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
                    return value  # return raw if parsing fails
        except Exception:
            pass
        return "Check systemctl"

    # --- Action handlers ---

    def _on_run_quick(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "sudo", SCAN_SCRIPT, "quick"])
        except Exception:
            pass

    def _on_run_deep(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "sudo", SCAN_SCRIPT, "deep"])
        except Exception:
            pass

    def _on_run_healthcheck(self, _widget):
        try:
            subprocess.Popen(
                ["konsole", "-e", "sudo", HEALTHCHECK_SCRIPT])
        except Exception:
            pass

    def _on_view_quarantine(self, _widget):
        try:
            subprocess.Popen(["dolphin", QUARANTINE_DIR])
        except Exception:
            pass

    def _on_view_logs(self, _widget):
        try:
            subprocess.Popen(["dolphin", LOG_DIR])
        except Exception:
            pass

    def _on_quit(self, _widget):
        Gtk.main_quit()


if __name__ == "__main__":
    tray = SecurityTray()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
