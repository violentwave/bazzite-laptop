"""Bazzite Security Dashboard — PySide6 tabbed main window."""

from __future__ import annotations

import platform
import re
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from tray.state_machine import (
        LOG_DIR, QUARANTINE_DIR, SCAN_SCRIPT, HEALTH_SNAPSHOT_SCRIPT,
        HEALTH_LOG, STATE_CONFIGS, STATE_HEALTHY_IDLE,
        format_relative_time, format_health_age, icon_path,
    )
except ImportError:
    from state_machine import (
        LOG_DIR, QUARANTINE_DIR, SCAN_SCRIPT, HEALTH_SNAPSHOT_SCRIPT,
        HEALTH_LOG, STATE_CONFIGS, STATE_HEALTHY_IDLE,
        format_relative_time, format_health_age, icon_path,
    )

STATE_COLORS: dict[str, str] = {
    "healthy_idle": "#4caf50",
    "scan_running": "#009688",
    "scan_complete": "#2196f3",
    "warning": "#ffc107",
    "scan_failed": "#f44336",
    "scan_aborted": "#f44336",
    "threats_found": "#f44336",
    "health_warning": "#ff9800",
    "unknown": "#9e9e9e",
}

# Timer cache: {name: (result, fetched_monotonic)}
_TIMER_CACHE: dict[str, tuple[str, float]] = {}
_TIMER_CACHE_TTL = 60.0


def _os_release_value(key: str) -> str:
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "Unknown"


def _next_timer(timer_name: str) -> str:
    """Return next fire time for a systemd timer; cached for 60 s."""
    now = time.monotonic()
    cached = _TIMER_CACHE.get(timer_name)
    if cached and (now - cached[1]) < _TIMER_CACHE_TTL:
        return cached[0]
    result_str = "Check systemctl"
    try:
        r = subprocess.run(
            ["systemctl", "show", timer_name, "--property=NextElapseUSecRealtime"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and "=" in r.stdout:
            value = r.stdout.strip().split("=", 1)[1]
            if not value:
                result_str = "Not scheduled"
            else:
                from datetime import datetime
                try:
                    dt = datetime.strptime(value.rsplit(" ", 1)[0], "%a %Y-%m-%d %H:%M:%S")
                    now_dt = datetime.now()
                    if dt.date() == now_dt.date():
                        result_str = f"Today {dt.strftime('%I:%M %p').lstrip('0')}"
                    elif (dt.date() - now_dt.date()).days == 1:
                        result_str = f"Tomorrow {dt.strftime('%I:%M %p').lstrip('0')}"
                    else:
                        result_str = dt.strftime("%a %b %d, %I:%M %p").lstrip("0")
                except Exception:
                    result_str = value
    except Exception:
        pass
    _TIMER_CACHE[timer_name] = (result_str, time.monotonic())
    return result_str


def _quarantine_count() -> int:
    try:
        return sum(1 for _ in QUARANTINE_DIR.iterdir()) if QUARANTINE_DIR.exists() else 0
    except Exception:
        return 0


def _run_scan(args: list[str]) -> None:
    try:
        subprocess.Popen(["pkexec"] + args)
    except FileNotFoundError:
        cmd = " ".join(args)
        subprocess.Popen(["konsole", "-e", "bash", "-c",
            f"sudo {cmd}; echo; echo 'Press Enter to close'; read"])


def _parse_health_log() -> dict[str, str]:
    """Extract key metrics from the health snapshot log file."""
    try:
        text = HEALTH_LOG.read_text(errors="replace")
    except Exception:
        return {}

    def _find(pat: str) -> str | None:
        m = re.search(pat, text)
        return m.group(1) if m else None

    metrics: dict[str, str] = {}
    # GPU
    v = _find(r"GPU temperature[:\s]+(\d+)")
    if v:
        metrics["GPU Temperature"] = f"{v} °C"
    v = _find(r"VRAM[:\s]+(\d+\s*/\s*\d+\s*MiB)")
    if v:
        metrics["VRAM Usage"] = v.strip()
    v = _find(r"Power draw[:\s]+([\d.]+\s*W)")
    if v:
        metrics["GPU Power"] = v.strip()
    # CPU
    v = _find(r"Package temp[:\s]+([\d.]+)")
    if v:
        metrics["CPU Package Temp"] = f"{v} °C"
    core_temps = re.findall(r"Core\s+\d+[:\s]+([\d.]+)", text)
    if core_temps:
        metrics["CPU Core Temps"] = ", ".join(
            f"{t} °C" for t in core_temps[:4]
        )
    # Storage
    disks = re.findall(r"(\d+%)\s+(/[^\s]*)", text)
    if disks:
        metrics["Disk Usage"] = ", ".join(
            f"{u} on {m}" for u, m in disks[:3]
        )
    v = _find(r"ZRAM[^:]*:[^\d]*([\d.]+\s*[GMK]iB[^\n]*)")
    if v:
        metrics["ZRAM"] = v.strip()

    svc_ok = re.findall(r"[✔✓]\s+([\w\s\-]+?)(?:\s{2,}|\n)", text)
    svc_fail = re.findall(r"[✘✗✕]\s+([\w\s\-]+?)(?:\s{2,}|\n)", text)
    svc_parts = (["OK: " + str(len(svc_ok))] if svc_ok else []) + \
                (["failed: " + str(len(svc_fail))] if svc_fail else [])
    if svc_parts:
        metrics["Services"] = ", ".join(svc_parts)

    return metrics


class DashboardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bazzite Security Dashboard")
        self.setMinimumSize(400, 350)

        self._settings = QSettings("BazziteSecurity", "Dashboard")
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(600, 540)

        tabs = QTabWidget()
        self._security_tab, self._sec_refs = self._create_security_tab()
        self._health_tab, self._health_refs = self._create_health_tab()
        tabs.addTab(self._security_tab, "Security")
        tabs.addTab(self._health_tab, "Health")
        tabs.addTab(self._create_about_tab(), "About")
        self.setCentralWidget(tabs)

        self.statusBar().showMessage("Waiting for status update...")

    def _create_security_tab(self) -> tuple[QWidget, dict]:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        refs: dict = {}

        header_box = QGroupBox()
        header_layout = QHBoxLayout(header_box)
        header_layout.setSpacing(12)
        shield_label = QLabel()
        shield_label.setFixedSize(64, 64)
        shield_label.setScaledContents(True)
        refs["shield"] = shield_label
        header_layout.addWidget(shield_label)
        state_label = QLabel("Initialising…")
        state_label.setTextFormat(Qt.TextFormat.RichText)
        state_label.setWordWrap(True)
        font = state_label.font()
        font.setPointSize(13)
        font.setBold(True)
        state_label.setFont(font)
        refs["state_label"] = state_label
        header_layout.addWidget(state_label, stretch=1)
        layout.addWidget(header_box)

        scan_box = QGroupBox("Last Scan")
        scan_layout = QVBoxLayout(scan_box)
        scan_layout.setSpacing(4)
        for key in ("scan_type", "scan_time", "scan_result", "scan_files", "scan_duration"):
            lbl = QLabel("—")
            lbl.setWordWrap(True)
            refs[key] = lbl
            scan_layout.addWidget(lbl)
        layout.addWidget(scan_box)

        progress_box = QGroupBox("Scan Progress")
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setSpacing(4)
        for key in ("progress_dirs", "progress_files", "progress_dir"):
            lbl = QLabel("—")
            lbl.setWordWrap(True)
            refs[key] = lbl
            progress_layout.addWidget(lbl)
        refs["progress_box"] = progress_box
        progress_box.setVisible(False)
        layout.addWidget(progress_box)

        sched_box = QGroupBox("Schedule")
        sched_layout = QVBoxLayout(sched_box)
        sched_layout.setSpacing(4)
        for key in ("next_quick", "next_deep", "quarantine"):
            lbl = QLabel("—")
            refs[key] = lbl
            sched_layout.addWidget(lbl)
        layout.addWidget(sched_box)

        action_box = QGroupBox("Actions")
        action_layout = QHBoxLayout(action_box)
        action_layout.setSpacing(8)
        btn_quick = QPushButton("Run Quick Scan")
        btn_quick.clicked.connect(lambda: _run_scan([SCAN_SCRIPT, "quick"]))
        action_layout.addWidget(btn_quick)
        btn_deep = QPushButton("Run Deep Scan")
        btn_deep.clicked.connect(lambda: _run_scan([SCAN_SCRIPT, "deep"]))
        action_layout.addWidget(btn_deep)
        btn_logs = QPushButton("View Logs")
        btn_logs.clicked.connect(lambda: subprocess.Popen(["dolphin", str(LOG_DIR)]))
        action_layout.addWidget(btn_logs)
        layout.addWidget(action_box)
        layout.addStretch()
        return root, refs

    def _create_health_tab(self) -> tuple[QWidget, dict]:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        refs: dict = {}

        status_box = QGroupBox("Health Status")
        status_layout = QVBoxLayout(status_box)
        status_layout.setSpacing(4)
        health_keys = (
            "health_status", "health_age", "health_issues",
            "health_warnings", "health_critical",
        )
        for key in health_keys:
            lbl = QLabel("—")
            lbl.setWordWrap(True)
            refs[key] = lbl
            status_layout.addWidget(lbl)
        layout.addWidget(status_box)

        detail_box = QGroupBox("Hardware Details")
        detail_layout = QVBoxLayout(detail_box)
        detail_layout.setSpacing(4)
        placeholder = QLabel("No health log data yet — run a health snapshot.")
        placeholder.setEnabled(False)
        placeholder.setWordWrap(True)
        refs["hw_placeholder"] = placeholder
        detail_layout.addWidget(placeholder)
        refs["hw_layout"] = detail_layout
        refs["hw_labels"] = {}
        layout.addWidget(detail_box)

        action_box = QGroupBox("Actions")
        action_layout = QHBoxLayout(action_box)
        btn_snapshot = QPushButton("Run Health Snapshot")
        btn_snapshot.clicked.connect(lambda: _run_scan([HEALTH_SNAPSHOT_SCRIPT]))
        action_layout.addWidget(btn_snapshot)
        btn_logs = QPushButton("View Health Logs")
        btn_logs.clicked.connect(
            lambda: subprocess.Popen(["dolphin", str(HEALTH_LOG.parent)])
        )
        action_layout.addWidget(btn_logs)
        layout.addWidget(action_box)
        layout.addStretch()
        return root, refs

    def _create_about_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("<h2>Bazzite Security Dashboard</h2>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        try:
            import PySide6
            pyside_ver = PySide6.__version__
        except Exception:
            pyside_ver = "Unknown"

        rows = [
            ("Version", "2.0.0 (PySide6 rewrite)"),
            ("System", _os_release_value("PRETTY_NAME")),
            ("Kernel", platform.release()),
            ("Python", sys.version.split()[0]),
            ("PySide6", pyside_ver),
        ]
        info_box = QGroupBox("System Info")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(4)
        for label, value in rows:
            lbl = QLabel(f"<b>{label}:</b> {value}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)
        layout.addWidget(info_box)

        link = QLabel(
            '<a href="https://github.com/lch/bazzite-laptop">'
            "github.com/lch/bazzite-laptop</a>"
        )
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(link)
        layout.addStretch()
        return root

    def update_status(self, data: dict, state: str) -> None:
        self._update_security(data, state)
        self._update_health(data)
        from datetime import datetime
        self.statusBar().showMessage(
            f"Last update: {datetime.now().strftime('%I:%M:%S %p').lstrip('0')}"
            "  |  Live"
        )

    def _update_security(self, data: dict, state: str) -> None:
        refs = self._sec_refs
        scan_state = state
        if state == "health_warning":
            s = data.get("state", "")
            r = data.get("last_scan_result", "")
            if s in ("scanning", "updating"):
                scan_state = "scan_running"
            elif r == "threats":
                scan_state = "threats_found"
            elif r == "error":
                scan_state = "scan_failed"
            else:
                scan_state = "healthy_idle"
        cfg = STATE_CONFIGS.get(scan_state, STATE_CONFIGS[STATE_HEALTHY_IDLE])
        color = STATE_COLORS.get(scan_state, STATE_COLORS["unknown"])

        svg = icon_path(cfg.icon)
        if svg.exists():
            refs["shield"].setPixmap(QPixmap(str(svg)))
        refs["state_label"].setText(f'<span style="color:{color};">{cfg.description}</span>')

        scan_type = data.get("scan_type", "")
        time_str = data.get("last_scan_time") or data.get("timestamp", "")
        result = data.get("result") or data.get("last_scan_result", "")
        files = data.get("files_scanned", 0)
        duration = data.get("duration", "")

        refs["scan_type"].setText(f"Type: {scan_type.title() if scan_type else '—'}")
        refs["scan_time"].setText(f"Time: {format_relative_time(time_str)}")
        refs["scan_result"].setText(f"Result: {result or '—'}")
        refs["scan_files"].setText(f"Files scanned: {files:,}" if files else "Files scanned: —")
        refs["scan_duration"].setText(f"Duration: {duration}" if duration else "Duration: —")

        is_scanning = scan_state == "scan_running"
        refs["progress_box"].setVisible(is_scanning)
        if is_scanning:
            dirs_done = data.get("dirs_completed", "")
            dirs_total = data.get("dirs_total", "")
            files_live = data.get("files_scanned", 0)
            cur_dir = data.get("current_dir", "")
            if dirs_done != "" and dirs_total != "":
                refs["progress_dirs"].setText(f"Directories: {dirs_done} / {dirs_total}")
            else:
                refs["progress_dirs"].setText("Directories: —")
            refs["progress_files"].setText(
                f"Files scanned: {int(files_live):,}" if files_live else "Files scanned: —"
            )
            refs["progress_dir"].setText(
                f"Current: {cur_dir}" if cur_dir else "Current directory: —"
            )

        refs["next_quick"].setText(f"Next quick: {_next_timer('clamav-quick.timer')}")
        refs["next_deep"].setText(f"Next deep: {_next_timer('clamav-deep.timer')}")
        refs["quarantine"].setText(f"Quarantine files: {_quarantine_count()}")

    def _update_health(self, data: dict) -> None:
        refs = self._health_refs
        health_status = data.get("health_status", "")
        health_ts = data.get("health_last_check", "")
        issues = data.get("health_issues", 0)
        warnings = data.get("health_warnings", 0)
        critical = data.get("health_critical", 0)

        if health_status:
            color = "#4caf50"
            if str(health_status).upper() == "CRITICAL":
                color = "#f44336"
            elif str(health_status).upper() == "WARNING":
                color = "#ff9800"
            refs["health_status"].setText(
                f'Status: <span style="color:{color};"><b>{health_status}</b></span>'
            )
            refs["health_status"].setTextFormat(Qt.TextFormat.RichText)
        else:
            refs["health_status"].setText("Status: No data yet")

        refs["health_age"].setText(
            f"Last check: {format_health_age(health_ts)}" if health_ts else "Last check: —"
        )
        refs["health_issues"].setText(f"Issues: {issues}" if health_status else "Issues: —")
        refs["health_warnings"].setText(f"Warnings: {warnings}" if health_status else "Warnings: —")
        refs["health_critical"].setText(f"Critical: {critical}" if health_status else "Critical: —")
        self._update_hw_details()

    def _update_hw_details(self) -> None:
        """Parse health log and update Hardware Details labels."""
        refs = self._health_refs
        metrics = _parse_health_log()

        if not metrics:
            refs["hw_placeholder"].setVisible(True)
            for lbl in refs["hw_labels"].values():
                lbl.setVisible(False)
            return

        refs["hw_placeholder"].setVisible(False)
        layout: QVBoxLayout = refs["hw_layout"]
        existing: dict[str, QLabel] = refs["hw_labels"]

        for metric_key, value in metrics.items():
            if metric_key in existing:
                existing[metric_key].setText(f"<b>{metric_key}:</b> {value}")
            else:
                lbl = QLabel(f"<b>{metric_key}:</b> {value}")
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setWordWrap(True)
                layout.addWidget(lbl)
                existing[metric_key] = lbl

        for key, lbl in existing.items():
            lbl.setVisible(key in metrics)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        event.ignore()
        self.hide()
