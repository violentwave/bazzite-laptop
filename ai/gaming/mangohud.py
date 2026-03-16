"""MangoHud CSV log parser, performance analyzer, and AI suggestion generator.

Parses MangoHud performance overlay CSV logs, computes statistics,
detects performance issues, and optionally queries an LLM for
optimization suggestions tailored to this laptop's hardware.

Hardware: Acer Predator G3-571, GTX 1060 6GB, i7-7700HQ, Bazzite 43.
"""

import csv
import io
import logging
import statistics
from pathlib import Path

from ai.config import APP_NAME
from ai.gaming.models import (
    FrametimeStats,
    GameSession,
    LoadStats,
    PerformanceIssue,
    ThermalStats,
)
from ai.rate_limiter import RateLimiter
from ai.router import route_query

logger = logging.getLogger(APP_NAME)

# ── Column alias mapping ──
# MangoHud CSV headers vary between versions. Map canonical names to
# all known alternatives so the parser works regardless of version.

COLUMN_ALIASES: dict[str, list[str]] = {
    "fps": ["fps"],
    "frametime": ["frametime", "frametime_ms"],
    "cpu_load": ["cpu_load", "cpu_load_percent", "cpu_usage"],
    "gpu_load": ["gpu_load", "gpu_load_percent", "gpu_usage"],
    "cpu_temp": ["cpu_temp", "cpu_temp_c"],
    "gpu_temp": ["gpu_temp", "gpu_temp_c"],
    "ram_used": ["ram_used", "ram_used_mb"],
    "vram_used": ["vram_used", "gpu_vram_used", "vram_used_mb"],
}

# Patterns that must NEVER appear in optimization suggestions.
# PRIME offload env vars crash games on this hybrid GPU laptop.
_BANNED_PATTERNS = [
    "__NV_PRIME_RENDER_OFFLOAD",
    "__GLX_VENDOR_LIBRARY_NAME",
    "__VK_LAYER_NV_optimus",
    "prime-run",
    "DRI_PRIME",
]


# ── Parsing ──


def _resolve_column(header: list[str], canonical: str) -> int | None:
    """Find the header index for a canonical column name using aliases."""
    aliases = COLUMN_ALIASES.get(canonical, [canonical])
    lower_header = [h.strip().lower() for h in header]
    for alias in aliases:
        if alias.lower() in lower_header:
            return lower_header.index(alias.lower())
    return None


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute a percentile from a pre-sorted list. pct is 0-100."""
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct / 100.0)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


def parse_mangohud_log(path: Path) -> GameSession:
    """Parse a MangoHud CSV log file into a GameSession with computed stats.

    Lines starting with ``#`` are metadata comments.  The game name is
    extracted from a ``# application: ...`` comment if present.  The first
    non-comment line is the CSV header; subsequent lines are data rows.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file contains no valid data rows.
    """
    if not path.exists():
        raise FileNotFoundError(f"MangoHud log not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")

    game_name = "Unknown"
    content_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            lower = stripped.lower()
            if lower.startswith("# application:"):
                game_name = stripped.split(":", 1)[1].strip()
        else:
            content_lines.append(stripped)

    # Filter empty lines
    content_lines = [ln for ln in content_lines if ln]

    if not content_lines:
        raise ValueError(f"No CSV content in {path}")

    # First non-comment line is the header
    reader = csv.reader(io.StringIO("\n".join(content_lines)))
    header = next(reader)

    # Resolve column indices
    col = {name: _resolve_column(header, name) for name in COLUMN_ALIASES}

    # Parse data rows
    fps_vals: list[float] = []
    ft_vals: list[float] = []
    cpu_load_vals: list[float] = []
    gpu_load_vals: list[float] = []
    cpu_temp_vals: list[float] = []
    gpu_temp_vals: list[float] = []
    ram_vals: list[float] = []
    vram_vals: list[float] = []

    for row in reader:
        try:
            if col["fps"] is not None:
                fps_vals.append(float(row[col["fps"]]))
            if col["frametime"] is not None:
                ft_vals.append(float(row[col["frametime"]]))
            if col["cpu_load"] is not None:
                cpu_load_vals.append(float(row[col["cpu_load"]]))
            if col["gpu_load"] is not None:
                gpu_load_vals.append(float(row[col["gpu_load"]]))
            if col["cpu_temp"] is not None:
                cpu_temp_vals.append(float(row[col["cpu_temp"]]))
            if col["gpu_temp"] is not None:
                gpu_temp_vals.append(float(row[col["gpu_temp"]]))
            if col["ram_used"] is not None:
                ram_vals.append(float(row[col["ram_used"]]))
            if col["vram_used"] is not None:
                vram_vals.append(float(row[col["vram_used"]]))
        except (IndexError, ValueError):
            # Skip malformed rows (e.g. "N/A" values)
            continue

    if not fps_vals and not ft_vals:
        raise ValueError(f"No valid data rows in {path}")

    total_frames = max(len(fps_vals), len(ft_vals))

    # FPS stats
    sorted_fps = sorted(fps_vals) if fps_vals else [0.0]
    avg_fps = statistics.mean(fps_vals) if fps_vals else 0.0
    min_fps = min(fps_vals) if fps_vals else 0.0
    max_fps = max(fps_vals) if fps_vals else 0.0
    p1_fps = _percentile(sorted_fps, 1)
    p01_fps = _percentile(sorted_fps, 0.1)

    # Frametime stats
    avg_ft = statistics.mean(ft_vals) if ft_vals else 0.0
    sorted_ft = sorted(ft_vals) if ft_vals else [0.0]
    p95_ft = _percentile(sorted_ft, 95)
    p99_ft = _percentile(sorted_ft, 99)

    # Stutter: frames where frametime > 2x average
    stutter_count = sum(1 for ft in ft_vals if ft > 2.0 * avg_ft) if ft_vals else 0
    stutter_pct = (stutter_count / len(ft_vals) * 100.0) if ft_vals else 0.0

    # Thermal stats
    cpu_temp_avg = statistics.mean(cpu_temp_vals) if cpu_temp_vals else 0.0
    cpu_temp_max = max(cpu_temp_vals) if cpu_temp_vals else 0.0
    gpu_temp_avg = statistics.mean(gpu_temp_vals) if gpu_temp_vals else 0.0
    gpu_temp_max = max(gpu_temp_vals) if gpu_temp_vals else 0.0

    # Throttle events: gpu_temp >= 90 or cpu_temp >= 95
    throttle_events = 0
    for i in range(max(len(cpu_temp_vals), len(gpu_temp_vals))):
        ct = cpu_temp_vals[i] if i < len(cpu_temp_vals) else 0.0
        gt = gpu_temp_vals[i] if i < len(gpu_temp_vals) else 0.0
        if gt >= 90 or ct >= 95:
            throttle_events += 1

    # Load stats
    cpu_load_avg = statistics.mean(cpu_load_vals) if cpu_load_vals else 0.0
    cpu_load_max = max(cpu_load_vals) if cpu_load_vals else 0.0
    gpu_load_avg = statistics.mean(gpu_load_vals) if gpu_load_vals else 0.0
    gpu_load_max = max(gpu_load_vals) if gpu_load_vals else 0.0
    ram_avg = statistics.mean(ram_vals) if ram_vals else 0.0
    ram_max = max(ram_vals) if ram_vals else 0.0
    vram_avg = statistics.mean(vram_vals) if vram_vals else 0.0
    vram_max = max(vram_vals) if vram_vals else 0.0

    # Duration = total_frames * avg_frametime_ms / 1000
    duration = total_frames * avg_ft / 1000.0 if avg_ft > 0 else 0.0

    return GameSession(
        log_path=str(path),
        game_name=game_name,
        total_frames=total_frames,
        duration_seconds=duration,
        frametime=FrametimeStats(
            avg_fps=avg_fps,
            min_fps=min_fps,
            max_fps=max_fps,
            p1_fps=p1_fps,
            p01_fps=p01_fps,
            avg_frametime_ms=avg_ft,
            p95_frametime_ms=p95_ft,
            p99_frametime_ms=p99_ft,
            stutter_pct=stutter_pct,
        ),
        thermal=ThermalStats(
            cpu_temp_avg=cpu_temp_avg,
            cpu_temp_max=cpu_temp_max,
            gpu_temp_avg=gpu_temp_avg,
            gpu_temp_max=gpu_temp_max,
            throttle_events=throttle_events,
        ),
        load=LoadStats(
            cpu_load_avg=cpu_load_avg,
            cpu_load_max=cpu_load_max,
            gpu_load_avg=gpu_load_avg,
            gpu_load_max=gpu_load_max,
            ram_used_avg_mb=ram_avg,
            ram_used_max_mb=ram_max,
            vram_used_avg_mb=vram_avg,
            vram_used_max_mb=vram_max,
        ),
        raw_fps=fps_vals,
        raw_frametime=ft_vals,
    )


# ── Analysis ──


def analyze_performance(session: GameSession) -> list[PerformanceIssue]:
    """Detect performance issues from a parsed GameSession.

    Thresholds are tuned for the GTX 1060 6 GB / i7-7700HQ combo.
    Returns issues sorted by severity (critical first).
    """
    issues: list[PerformanceIssue] = []

    # GPU thermals
    if session.thermal.gpu_temp_max >= 90:
        issues.append(PerformanceIssue(
            category="thermal", severity="critical",
            metric="gpu_temp_max",
            value=session.thermal.gpu_temp_max, threshold=90,
            suggestion=f"GPU hit {session.thermal.gpu_temp_max:.0f}C (throttle zone)",
        ))
    elif session.thermal.gpu_temp_avg >= 82:
        issues.append(PerformanceIssue(
            category="thermal", severity="warning",
            metric="gpu_temp_avg",
            value=session.thermal.gpu_temp_avg, threshold=82,
            suggestion=f"GPU averaging {session.thermal.gpu_temp_avg:.0f}C (high)",
        ))

    # CPU thermals
    if session.thermal.cpu_temp_max >= 95:
        issues.append(PerformanceIssue(
            category="thermal", severity="critical",
            metric="cpu_temp_max",
            value=session.thermal.cpu_temp_max, threshold=95,
            suggestion=f"CPU hit {session.thermal.cpu_temp_max:.0f}C (throttle zone)",
        ))
    elif session.thermal.cpu_temp_avg >= 85:
        issues.append(PerformanceIssue(
            category="thermal", severity="warning",
            metric="cpu_temp_avg",
            value=session.thermal.cpu_temp_avg, threshold=85,
            suggestion=f"CPU averaging {session.thermal.cpu_temp_avg:.0f}C (high)",
        ))

    # VRAM pressure
    if session.load.vram_used_max_mb >= 5900:
        issues.append(PerformanceIssue(
            category="vram_pressure", severity="critical",
            metric="vram_used_max_mb",
            value=session.load.vram_used_max_mb, threshold=5900,
            suggestion=(
                f"VRAM peaked at {session.load.vram_used_max_mb:.0f} MB "
                f"(near 6 GB limit)"
            ),
        ))
    elif session.load.vram_used_avg_mb >= 5600:
        issues.append(PerformanceIssue(
            category="vram_pressure", severity="warning",
            metric="vram_used_avg_mb",
            value=session.load.vram_used_avg_mb, threshold=5600,
            suggestion=(
                f"VRAM averaging {session.load.vram_used_avg_mb:.0f} MB "
                f"(high for 6 GB card)"
            ),
        ))

    # CPU bottleneck
    if session.load.cpu_load_avg >= 95:
        issues.append(PerformanceIssue(
            category="cpu_bottleneck", severity="warning",
            metric="cpu_load_avg",
            value=session.load.cpu_load_avg, threshold=95,
            suggestion=(
                f"CPU load averaging {session.load.cpu_load_avg:.0f}% "
                f"(bottleneck likely)"
            ),
        ))

    # Stutter
    if session.frametime.stutter_pct >= 15:
        issues.append(PerformanceIssue(
            category="stutter", severity="critical",
            metric="stutter_pct",
            value=session.frametime.stutter_pct, threshold=15,
            suggestion=f"Stutter rate {session.frametime.stutter_pct:.1f}% (severe hitching)",
        ))
    elif session.frametime.stutter_pct >= 5:
        issues.append(PerformanceIssue(
            category="stutter", severity="warning",
            metric="stutter_pct",
            value=session.frametime.stutter_pct, threshold=5,
            suggestion=f"Stutter rate {session.frametime.stutter_pct:.1f}% (noticeable hitching)",
        ))

    # Low FPS
    if session.frametime.avg_fps < 30:
        issues.append(PerformanceIssue(
            category="low_fps", severity="warning",
            metric="avg_fps",
            value=session.frametime.avg_fps, threshold=30,
            suggestion=f"Average FPS {session.frametime.avg_fps:.1f} (below 30)",
        ))
    if session.frametime.p1_fps < 20:
        issues.append(PerformanceIssue(
            category="low_fps", severity="warning",
            metric="p1_fps",
            value=session.frametime.p1_fps, threshold=20,
            suggestion=f"1% low FPS {session.frametime.p1_fps:.1f} (severe dips)",
        ))

    # Sort: critical first, then warning
    severity_order = {"critical": 0, "warning": 1}
    issues.sort(key=lambda i: severity_order.get(i.severity, 2))

    return issues


# ── Suggestions ──

_STATIC_SUGGESTIONS: dict[str, list[str]] = {
    "thermal": [
        "Clean laptop fans and vents with compressed air",
        "Use a cooling pad to improve airflow",
        "Lower in-game graphics preset by one level",
        "Cap FPS to 60 in MangoHud or game settings",
    ],
    "vram_pressure": [
        "Lower texture quality to Medium or below",
        "Reduce render resolution to 1600x900",
        "Disable HD texture packs if installed",
    ],
    "cpu_bottleneck": [
        "Enable GameMode (gamemoded) for CPU governor optimization",
        "Lower NPC density or draw distance in game settings",
        "Close background applications before gaming",
    ],
    "stutter": [
        "Enable shader pre-caching in Steam settings",
        "Set DXVK_ASYNC=1 in Steam launch options for Vulkan titles",
        "Lower shadow quality to reduce frame-time spikes",
    ],
    "low_fps": [
        "Lower resolution to 1600x900 or use FSR upscaling",
        "Reduce graphics preset by one or two levels",
        "Disable anti-aliasing or use FXAA instead of MSAA",
    ],
}


def _filter_banned(lines: list[str]) -> list[str]:
    """Remove any suggestion lines containing banned patterns."""
    result = []
    for line in lines:
        if any(pat in line for pat in _BANNED_PATTERNS):
            logger.warning("Filtered banned pattern from suggestion: %s", line.strip())
            continue
        result.append(line)
    return result


def _static_fallback(issues: list[PerformanceIssue]) -> list[str]:
    """Return static suggestions based on detected issue categories."""
    seen: set[str] = set()
    suggestions: list[str] = []
    for issue in issues:
        if issue.category not in seen:
            seen.add(issue.category)
            suggestions.extend(_STATIC_SUGGESTIONS.get(issue.category, []))
    return suggestions


def suggest_optimizations(
    issues: list[PerformanceIssue],
    game_name: str,
    hardware: object | None = None,
    rate_limiter: RateLimiter | None = None,
) -> list[str]:
    """Get optimization suggestions for detected performance issues.

    Attempts to use the LLM router for tailored advice.  Falls back to
    static suggestions if the LLM is unavailable, rate-limited, or
    returns an error.

    Args:
        issues: Performance issues detected by :func:`analyze_performance`.
        game_name: Name of the game being analyzed.
        hardware: Optional hardware snapshot (reserved for future use).
        rate_limiter: Optional rate limiter to gate LLM calls.

    Returns:
        A list of actionable suggestion strings.
    """
    if not issues:
        return []

    # Check rate limits before calling LLM
    if rate_limiter is not None and not rate_limiter.can_call("groq"):
        logger.info("Rate limited -- returning static suggestions")
        return _static_fallback(issues)

    issue_text = "\n".join(
        f"- [{i.severity.upper()}] {i.category}: {i.suggestion}"
        for i in issues
    )

    prompt = (
        f"Game: {game_name}\n"
        f"Hardware: Acer Predator G3-571, NVIDIA GTX 1060 6GB, Intel i7-7700HQ, "
        f"Bazzite 43 (Fedora Atomic immutable Linux), ZRAM swap.\n\n"
        f"Detected performance issues:\n{issue_text}\n\n"
        f"Give 3-5 actionable optimization suggestions as a numbered list.\n\n"
        f"CRITICAL RULES:\n"
        f"- NEVER suggest __NV_PRIME_RENDER_OFFLOAD or any PRIME offload "
        f"environment variables. They crash games on this laptop.\n"
        f"- NEVER suggest lowering vm.swappiness. The value 180 is correct "
        f"for ZRAM-based swap on Bazzite.\n"
        f"- NEVER suggest DRI_PRIME or prime-run.\n"
    )

    try:
        response = route_query("fast", prompt)
        if rate_limiter is not None:
            rate_limiter.record_call("groq")

        # Parse numbered list lines from response
        lines = [
            ln.strip()
            for ln in response.splitlines()
            if ln.strip() and ln.strip()[0].isdigit()
        ]
        lines = _filter_banned(lines)

        if lines:
            return lines

        # If parsing produced nothing, return any non-empty lines
        all_lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
        all_lines = _filter_banned(all_lines)
        return all_lines if all_lines else _static_fallback(issues)

    except Exception:
        logger.exception("LLM query failed -- returning static suggestions")
        return _static_fallback(issues)
