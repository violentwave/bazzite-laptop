# ruff: noqa: E701,E702,E741
"""Bazzite Security Dashboard -- PySide6 dark-theme tabbed window."""
from __future__ import annotations
import platform, re, subprocess, sys, time  # noqa: E401
from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget)

try:
    from tray.state_machine import (
        LOG_DIR, QUARANTINE_DIR, SCAN_SCRIPT, HEALTH_SNAPSHOT_SCRIPT,
        HEALTHCHECK_SCRIPT, TEST_SUITE_SCRIPT,
        HEALTH_LOG, STATE_CONFIGS, STATE_HEALTHY_IDLE,
        format_relative_time, format_health_age, icon_path,
    )
except ImportError:
    from state_machine import (
        LOG_DIR, QUARANTINE_DIR, SCAN_SCRIPT, HEALTH_SNAPSHOT_SCRIPT,
        HEALTHCHECK_SCRIPT, TEST_SUITE_SCRIPT,
        HEALTH_LOG, STATE_CONFIGS, STATE_HEALTHY_IDLE,
        format_relative_time, format_health_age, icon_path,
    )

# -- Theme -------------------------------------------------------------------
_BG, _CARD, _ACCENT = "#1a1a2e", "#16213e", "#0f3460"
_OK, _WARN, _ERR, _INFO = "#00b894", "#fdcb6e", "#e17055", "#74b9ff"
_T1, _T2, _BD = "#dfe6e9", "#b2bec3", "#2d3436"

STATE_COLORS: dict[str, str] = {
    "healthy_idle": _OK, "scan_running": _INFO, "scan_complete": _INFO,
    "warning": _WARN, "scan_failed": _ERR, "scan_aborted": _ERR,
    "threats_found": _ERR, "health_warning": _WARN, "unknown": _T2,
}

_QSS = (
    f"QMainWindow,QWidget{{background:{_BG};color:{_T1};"
    f"font-family:'Noto Sans','Segoe UI',sans-serif}}"
    f"QTabWidget::pane{{border:1px solid {_BD};border-radius:4px;"
    f"background:{_BG};top:-1px}}"
    f"QTabBar::tab{{background:{_CARD};color:{_T2};padding:8px 20px;"
    f"border:1px solid {_BD};border-bottom:none;"
    f"border-top-left-radius:6px;border-top-right-radius:6px;"
    f"margin-right:2px;font-weight:600}}"
    f"QTabBar::tab:selected{{background:{_ACCENT};color:{_T1};"
    f"border-color:{_INFO}}}"
    f"QTabBar::tab:hover:!selected{{background:{_ACCENT}}}"
    f"QPushButton{{background:{_ACCENT};color:{_T1};border:1px solid {_BD};"
    f"border-radius:6px;padding:7px 16px;font-weight:600;font-size:12px}}"
    f"QPushButton:hover{{background:{_INFO};color:#0a0a1a;border-color:{_INFO}}}"
    f"QPushButton:pressed{{background:#5a9fd4}}"
    f"QStatusBar{{background:{_CARD};color:{_T2};border-top:1px solid {_BD};"
    f"font-size:11px;padding:2px 8px}}"
)

# -- Helpers -----------------------------------------------------------------
_TIMER_CACHE: dict[str, tuple[str, float]] = {}
_SS_TRANS = "background:transparent;border:none"


def _os_release_value(key: str) -> str:
    try:
        for ln in Path("/etc/os-release").read_text().splitlines():
            if ln.startswith(f"{key}="):
                return ln.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "Unknown"


def _next_timer(name: str) -> str:
    now = time.monotonic()
    c = _TIMER_CACHE.get(name)
    if c and (now - c[1]) < 60.0:
        return c[0]
    res = "Check systemctl"
    try:
        r = subprocess.run(
            ["systemctl", "show", name, "--property=NextElapseUSecRealtime"],
            capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "=" in r.stdout:
            val = r.stdout.strip().split("=", 1)[1]
            if not val:
                res = "Not scheduled"
            else:
                from datetime import datetime
                try:
                    dt = datetime.strptime(val.rsplit(" ", 1)[0],
                                           "%a %Y-%m-%d %H:%M:%S")
                    nd = datetime.now()
                    if dt.date() == nd.date():
                        res = f"Today {dt.strftime('%I:%M %p').lstrip('0')}"
                    elif (dt.date() - nd.date()).days == 1:
                        res = f"Tomorrow {dt.strftime('%I:%M %p').lstrip('0')}"
                    else:
                        res = dt.strftime("%a %b %d, %I:%M %p").lstrip("0")
                except Exception:
                    res = val
    except Exception:
        pass
    _TIMER_CACHE[name] = (res, time.monotonic())
    return res


def _quarantine_count() -> int:
    try:
        return sum(1 for _ in QUARANTINE_DIR.iterdir()) if QUARANTINE_DIR.exists() else 0
    except Exception:
        return 0


def _run_scan(args: list[str]) -> None:
    try:
        subprocess.Popen(["pkexec"] + args)
    except FileNotFoundError:
        subprocess.Popen(["konsole", "-e", "bash", "-c",
                          f"sudo {' '.join(args)}; echo; echo 'Press Enter to close'; read"])


def _btn(label: str, slot) -> QPushButton:
    b = QPushButton(label)
    b.clicked.connect(slot)
    return b


def _parse_health_log() -> dict[str, dict[str, str]]:
    """Parse health log into grouped GPU/CPU/Storage/Services dicts."""
    try:
        text = HEALTH_LOG.read_text(errors="replace")
    except Exception:
        return {}
    def _f(pat: str) -> str | None:
        m = re.search(pat, text)
        return m.group(1) if m else None
    g: dict[str, dict[str, str]] = {
        "gpu": {}, "cpu": {}, "storage": {}, "memory": {}, "services": {}}
    v = _f(r"GPU temperature[:\s]+(\d+)")
    if v: g["gpu"]["Temperature"] = f"{v} C"
    v = _f(r"VRAM[:\s]+(\d+\s*/\s*\d+\s*MiB)")
    if v: g["gpu"]["VRAM"] = v.strip()
    v = _f(r"Power draw[:\s]+([\d.]+\s*W)")
    if v: g["gpu"]["Power"] = v.strip()
    v = _f(r"Package temp[:\s]+([\d.]+)")
    if v: g["cpu"]["Package"] = f"{v} C"
    ct = re.findall(r"Core\s+\d+[:\s]+([\d.]+)", text)
    if ct: g["cpu"]["Cores"] = ", ".join(ct[:4]) + " C"
    for u, mt in re.findall(r"(\d+%)\s+(/[^\s]*)", text)[:4]:
        g["storage"][mt.rstrip("/").rsplit("/", 1)[-1] or "/"] = u
    v = _f(r"ZRAM[^:]*:[^\d]*([\d.]+\s*[GMK]iB[^\n]*)")
    if v: g["memory"]["ZRAM"] = v.strip()
    for m in re.finditer(r"[✔✓]\s+([\w\-]+)[:\s]+([\w]+)", text):
        g["services"][m.group(1)] = m.group(2)
    for m in re.finditer(r"[✘✗✕]\s+([\w\-]+)[:\s]+([\w]+)", text):
        g["services"][m.group(1)] = f"FAIL: {m.group(2)}"
    return {k: v for k, v in g.items() if v}


# -- UI primitives -----------------------------------------------------------

def _card() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.StyledPanel)
    f.setStyleSheet(f"QFrame{{background:{_CARD};border:1px solid {_BD};"
                    f"border-radius:8px;padding:10px}}")
    return f


def _heading(text: str, color: str = _T2) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color};font-size:11px;font-weight:700;{_SS_TRANS}")
    return lbl


def _vlbl(text: str = "--") -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color:{_T1};font-size:12px;{_SS_TRANS}")
    return lbl


# -- Dashboard ---------------------------------------------------------------

class DashboardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bazzite Security Dashboard")
        self.setMinimumSize(520, 480)
        self.setStyleSheet(_QSS)
        self._settings = QSettings("BazziteSecurity", "Dashboard")
        geo = self._settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(640, 600)
        tabs = QTabWidget()
        self._security_tab, self._sec_refs = self._build_security()
        self._health_tab, self._health_refs = self._build_health()
        tabs.addTab(self._security_tab, "  Security  ")
        tabs.addTab(self._health_tab, "  Health  ")
        tabs.addTab(self._build_about(), "  About  ")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("  Waiting for status update...")

    def _build_security(self) -> tuple[QWidget, dict]:
        root, lay, refs = QWidget(), None, {}
        lay = QVBoxLayout(root)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)
        # Banner
        banner = _card()
        bl = QHBoxLayout(banner)
        bl.setSpacing(14)
        shield = QLabel()
        shield.setFixedSize(48, 48)
        shield.setScaledContents(True)
        shield.setStyleSheet(_SS_TRANS)
        refs["shield"] = shield
        bl.addWidget(shield)
        sl = QLabel("Initialising...")
        sl.setTextFormat(Qt.TextFormat.RichText)
        sl.setWordWrap(True)
        sl.setStyleSheet(f"font-size:16px;font-weight:700;{_SS_TRANS}")
        refs["state_label"] = sl
        bl.addWidget(sl, stretch=1)
        lay.addWidget(banner)
        # Info cards row
        row = QHBoxLayout()
        row.setSpacing(10)
        sc = _card()
        scl = QVBoxLayout(sc)
        scl.setSpacing(4)
        scl.addWidget(_heading("LAST SCAN"))
        for k in ("scan_type", "scan_time", "scan_result", "scan_files", "scan_duration"):
            refs[k] = _vlbl(); scl.addWidget(refs[k])
        row.addWidget(sc, stretch=3)
        sd = _card()
        sdl = QVBoxLayout(sd)
        sdl.setSpacing(4)
        sdl.addWidget(_heading("SCHEDULE"))
        for k in ("next_quick", "next_deep", "quarantine"):
            refs[k] = _vlbl(); sdl.addWidget(refs[k])
        sdl.addStretch()
        row.addWidget(sd, stretch=2)
        lay.addLayout(row)
        # Progress (hidden)
        pc = _card()
        pl = QVBoxLayout(pc)
        pl.setSpacing(4)
        pl.addWidget(_heading("SCAN PROGRESS", color=_INFO))
        for k in ("progress_dirs", "progress_files", "progress_dir"):
            refs[k] = _vlbl(); pl.addWidget(refs[k])
        refs["progress_box"] = pc
        pc.setVisible(False)
        lay.addWidget(pc)
        # Actions
        ac = _card()
        ag = QGridLayout(ac)
        ag.setSpacing(8)
        ag.addWidget(_heading("ACTIONS"), 0, 0, 1, 3)
        ag.addWidget(_btn("Quick Scan", lambda: _run_scan([SCAN_SCRIPT, "quick"])), 1, 0)
        ag.addWidget(_btn("Deep Scan", lambda: _run_scan([SCAN_SCRIPT, "deep"])), 1, 1)
        ag.addWidget(_btn("Test Scan", lambda: _run_scan([SCAN_SCRIPT, "test"])), 1, 2)
        ag.addWidget(_btn("Test Suite", lambda: _run_scan([TEST_SUITE_SCRIPT])), 2, 0)
        ag.addWidget(_btn("Quarantine",
                          lambda: subprocess.Popen(["dolphin", str(QUARANTINE_DIR)])), 2, 1)
        ag.addWidget(_btn("View Logs",
                          lambda: subprocess.Popen(["dolphin", str(LOG_DIR)])), 2, 2)
        lay.addWidget(ac)
        lay.addStretch()
        return root, refs

    def _build_health(self) -> tuple[QWidget, dict]:
        root, lay, refs = QWidget(), None, {}
        lay = QVBoxLayout(root)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)
        # Banner
        banner = _card()
        bl = QHBoxLayout(banner)
        bl.setSpacing(12)
        hi = QLabel()
        hi.setFixedSize(48, 48)
        hi.setScaledContents(True)
        hi.setStyleSheet(_SS_TRANS)
        refs["health_icon"] = hi
        ht = QLabel("Checking health...")
        ht.setTextFormat(Qt.TextFormat.RichText)
        ht.setWordWrap(True)
        ht.setStyleSheet(f"font-size:16px;font-weight:700;{_SS_TRANS}")
        refs["health_banner_text"] = ht
        bl.addWidget(hi)
        bl.addWidget(ht, stretch=1)
        al = _vlbl()
        al.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        refs["health_age"] = al
        bl.addWidget(al)
        lay.addWidget(banner)
        # 2x2 metric cards
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (key, title) in enumerate([
            ("gpu", "GPU"), ("cpu", "CPU"), ("storage", "STORAGE"), ("services", "SERVICES"),
        ]):
            c = _card()
            vl = QVBoxLayout(c)
            vl.setSpacing(3)
            vl.addWidget(_heading(title))
            refs[f"hw_{key}_layout"] = vl
            refs[f"hw_{key}_labels"] = {}
            grid.addWidget(c, i // 2, i % 2)
        lay.addLayout(grid)
        ph = _vlbl("No health data yet -- run a snapshot.")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph.setStyleSheet(f"color:{_T2};font-style:italic;font-size:12px;{_SS_TRANS}")
        refs["hw_placeholder"] = ph
        lay.addWidget(ph)
        # Actions
        ac = _card()
        ag = QGridLayout(ac)
        ag.setSpacing(8)
        ag.addWidget(_heading("ACTIONS"), 0, 0, 1, 3)
        ag.addWidget(_btn("Health Snapshot",
                          lambda: _run_scan([HEALTH_SNAPSHOT_SCRIPT])), 1, 0)
        ag.addWidget(_btn("Health Check", lambda: _run_scan([HEALTHCHECK_SCRIPT])), 1, 1)
        ag.addWidget(_btn("Self-Test",
                          lambda: _run_scan([HEALTH_SNAPSHOT_SCRIPT, "--selftest"])), 1, 2)
        ag.addWidget(_btn("View Health Logs",
                          lambda: subprocess.Popen(["dolphin", str(HEALTH_LOG.parent)])),
                     2, 0, 1, 3)
        lay.addWidget(ac)
        lay.addStretch()
        return root, refs

    def _build_about(self) -> QWidget:
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(20, 30, 20, 20)
        lay.setSpacing(14)
        shield = QLabel()
        shield.setFixedSize(64, 64)
        shield.setScaledContents(True)
        shield.setStyleSheet(_SS_TRANS)
        svg = icon_path("bazzite-sec-green")
        if svg.exists():
            shield.setPixmap(QPixmap(str(svg)))
        lay.addWidget(shield, alignment=Qt.AlignmentFlag.AlignCenter)
        for txt, sz, clr in [("Bazzite Security Dashboard", 18, _T1),
                              ("Enterprise security monitoring for Bazzite Linux", 12, _T2)]:
            l = QLabel(txt)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet(f"font-size:{sz}px;font-weight:700;color:{clr};{_SS_TRANS}")
            lay.addWidget(l)
        lay.addSpacing(10)
        try:
            import PySide6; pv = PySide6.__version__
        except Exception:
            pv = "Unknown"
        ic = _card()
        il = QVBoxLayout(ic)
        il.setSpacing(5)
        il.addWidget(_heading("SYSTEM INFO"))
        for label, value in [("Version", "2.0.0"), ("System", _os_release_value("PRETTY_NAME")),
                              ("Kernel", platform.release()), ("Python", sys.version.split()[0]),
                              ("PySide6", pv)]:
            rl = QLabel(f'<span style="color:{_T2};">{label}:</span>  '
                        f'<span style="color:{_T1};">{value}</span>')
            rl.setTextFormat(Qt.TextFormat.RichText)
            rl.setStyleSheet(_SS_TRANS)
            il.addWidget(rl)
        lay.addWidget(ic)
        link = QLabel(f'<a style="color:{_INFO};" href="https://github.com/violentwave/'
                      f'bazzite-laptop">github.com/violentwave/bazzite-laptop</a>')
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link.setStyleSheet(_SS_TRANS)
        lay.addWidget(link)
        lay.addStretch()
        return root

    # -- Live updates --------------------------------------------------------

    def update_status(self, data: dict, state: str) -> None:
        self._update_security(data, state)
        self._update_health(data)
        from datetime import datetime
        self.statusBar().showMessage(
            f"  Live  |  Last update: {datetime.now().strftime('%I:%M:%S %p').lstrip('0')}")

    def _update_security(self, data: dict, state: str) -> None:
        refs = self._sec_refs
        ss = state
        if state == "health_warning":
            s, r = data.get("state", ""), data.get("last_scan_result", "")
            if s in ("scanning", "updating"): ss = "scan_running"
            elif r == "threats": ss = "threats_found"
            elif r == "error": ss = "scan_failed"
            else: ss = "healthy_idle"
        cfg = STATE_CONFIGS.get(ss, STATE_CONFIGS[STATE_HEALTHY_IDLE])
        color = STATE_COLORS.get(ss, STATE_COLORS["unknown"])
        svg = icon_path(cfg.icon)
        if svg.exists():
            refs["shield"].setPixmap(QPixmap(str(svg)))
        refs["state_label"].setText(
            f'<span style="color:{color};font-size:16px;">{cfg.description}</span>')
        st = data.get("scan_type", "")
        ts = data.get("last_scan_time") or data.get("timestamp", "")
        res = data.get("result") or data.get("last_scan_result", "")
        files = data.get("files_scanned", 0)
        dur = data.get("duration", "")
        rc = _OK if res == "clean" else (_ERR if res in ("threats", "error") else _T1)
        refs["scan_type"].setText(f"Type: {st.title() if st else '--'}")
        refs["scan_time"].setText(f"Time: {format_relative_time(ts)}")
        refs["scan_result"].setText(
            f'Result: <span style="color:{rc};">{res.title() if res else "--"}</span>')
        refs["scan_result"].setTextFormat(Qt.TextFormat.RichText)
        refs["scan_files"].setText(f"Files: {files:,}" if files else "Files: --")
        refs["scan_duration"].setText(f"Duration: {dur}" if dur else "Duration: --")
        scanning = ss == "scan_running"
        refs["progress_box"].setVisible(scanning)
        if scanning:
            dd, dt_ = data.get("dirs_completed", ""), data.get("dirs_total", "")
            fl, cd = data.get("files_scanned", 0), data.get("current_dir", "")
            refs["progress_dirs"].setText(
                f"Directories: {dd} / {dt_}" if dd != "" and dt_ != "" else "Directories: --")
            refs["progress_files"].setText(f"Files: {int(fl):,}" if fl else "Files: --")
            refs["progress_dir"].setText(f"Current: {cd}" if cd else "Current: --")
        refs["next_quick"].setText(f"Quick: {_next_timer('clamav-quick.timer')}")
        refs["next_deep"].setText(f"Deep: {_next_timer('clamav-deep.timer')}")
        qc = _quarantine_count()
        refs["quarantine"].setText(
            f'Quarantine: <span style="color:{_ERR if qc else _OK};">{qc}</span>')
        refs["quarantine"].setTextFormat(Qt.TextFormat.RichText)

    def _update_health(self, data: dict) -> None:
        refs = self._health_refs
        hs = data.get("health_status", "")
        hts = data.get("health_last_check", "")
        issues = data.get("health_issues", 0)
        critical = data.get("health_critical", 0)
        if hs:
            u = str(hs).upper()
            if u == "CRITICAL":
                color, ico, summary = _ERR, "bazzite-sec-red", f"{critical} critical issue(s)"
            elif u == "WARNING":
                color, ico = _WARN, "bazzite-sec-health-warn"
                summary = f"{issues} issue(s) detected"
            else:
                color, ico, summary = _OK, "bazzite-sec-green", "All systems nominal"
            refs["health_banner_text"].setText(
                f'<span style="color:{color};font-size:16px;">{u}</span>'
                f'<br/><span style="color:{_T2};font-size:12px;">{summary}</span>')
            svg = icon_path(ico)
            if svg.exists():
                refs["health_icon"].setPixmap(QPixmap(str(svg)))
        else:
            refs["health_banner_text"].setText(f'<span style="color:{_T2};">No health data</span>')
        refs["health_age"].setText(f"Last: {format_health_age(hts)}" if hts else "")
        self._update_hw_details()

    def _update_hw_details(self) -> None:
        refs = self._health_refs
        groups = _parse_health_log()
        refs["hw_placeholder"].setVisible(not groups)
        for gk in ("gpu", "cpu", "storage", "services"):
            lk, labk = f"hw_{gk}_layout", f"hw_{gk}_labels"
            if lk not in refs:
                continue
            layout: QVBoxLayout = refs[lk]
            existing: dict[str, QLabel] = refs[labk]
            metrics = groups.get(gk, {})
            for mn, val in metrics.items():
                disp = f"{mn}: {val}" if val else mn
                if mn in existing:
                    existing[mn].setText(disp)
                    existing[mn].setVisible(True)
                else:
                    lbl = _vlbl(disp)
                    layout.addWidget(lbl)
                    existing[mn] = lbl
            for key in list(existing.keys()):
                if key not in metrics:
                    lbl = existing.pop(key)
                    layout.removeWidget(lbl)
                    lbl.deleteLater()
        # ZRAM into storage card
        for mk, mv in groups.get("memory", {}).items():
            sl, slb = refs["hw_storage_labels"], refs["hw_storage_layout"]
            d = f"{mk}: {mv}"
            if mk in sl:
                sl[mk].setText(d)
            else:
                lbl = _vlbl(d)
                slb.addWidget(lbl)
                sl[mk] = lbl

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        event.ignore()
        self.hide()
