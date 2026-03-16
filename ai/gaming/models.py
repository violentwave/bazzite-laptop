"""Data models for the gaming optimization AI layer."""

from dataclasses import dataclass, field


@dataclass
class FrametimeStats:
    """Statistical summary of frame timing data."""

    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0
    p1_fps: float = 0.0  # 1st percentile (1% low)
    p01_fps: float = 0.0  # 0.1th percentile (0.1% low)
    avg_frametime_ms: float = 0.0
    p95_frametime_ms: float = 0.0
    p99_frametime_ms: float = 0.0
    stutter_pct: float = 0.0  # % of frames with frametime > 2x avg


@dataclass
class ThermalStats:
    """Thermal summary from a gaming session."""

    cpu_temp_avg: float = 0.0
    cpu_temp_max: float = 0.0
    gpu_temp_avg: float = 0.0
    gpu_temp_max: float = 0.0
    throttle_events: int = 0


@dataclass
class LoadStats:
    """CPU/GPU/Memory load summary."""

    cpu_load_avg: float = 0.0
    cpu_load_max: float = 0.0
    gpu_load_avg: float = 0.0
    gpu_load_max: float = 0.0
    ram_used_avg_mb: float = 0.0
    ram_used_max_mb: float = 0.0
    vram_used_avg_mb: float = 0.0
    vram_used_max_mb: float = 0.0


@dataclass
class GameSession:
    """Parsed MangoHud session with computed statistics."""

    log_path: str = ""
    game_name: str = ""
    duration_seconds: float = 0.0
    total_frames: int = 0
    frametime: FrametimeStats = field(default_factory=FrametimeStats)
    thermal: ThermalStats = field(default_factory=ThermalStats)
    load: LoadStats = field(default_factory=LoadStats)
    timestamp: str = ""
    raw_fps: list[float] = field(default_factory=list, repr=False)
    raw_frametime: list[float] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON output. Excludes raw arrays."""
        return {
            "log_path": self.log_path,
            "game_name": self.game_name,
            "duration_seconds": round(self.duration_seconds, 1),
            "total_frames": self.total_frames,
            "frametime": {
                "avg_fps": round(self.frametime.avg_fps, 1),
                "min_fps": round(self.frametime.min_fps, 1),
                "max_fps": round(self.frametime.max_fps, 1),
                "p1_fps": round(self.frametime.p1_fps, 1),
                "p01_fps": round(self.frametime.p01_fps, 1),
                "avg_frametime_ms": round(self.frametime.avg_frametime_ms, 2),
                "p95_frametime_ms": round(self.frametime.p95_frametime_ms, 2),
                "p99_frametime_ms": round(self.frametime.p99_frametime_ms, 2),
                "stutter_pct": round(self.frametime.stutter_pct, 1),
            },
            "thermal": {
                "cpu_temp_avg": round(self.thermal.cpu_temp_avg, 1),
                "cpu_temp_max": round(self.thermal.cpu_temp_max, 1),
                "gpu_temp_avg": round(self.thermal.gpu_temp_avg, 1),
                "gpu_temp_max": round(self.thermal.gpu_temp_max, 1),
                "throttle_events": self.thermal.throttle_events,
            },
            "load": {
                "cpu_load_avg": round(self.load.cpu_load_avg, 1),
                "gpu_load_avg": round(self.load.gpu_load_avg, 1),
                "ram_used_max_mb": round(self.load.ram_used_max_mb, 1),
                "vram_used_max_mb": round(self.load.vram_used_max_mb, 1),
            },
            "timestamp": self.timestamp,
        }


@dataclass
class PerformanceIssue:
    """A detected performance problem from session analysis."""

    category: str  # "thermal", "vram_pressure", "cpu_bottleneck", "stutter", "low_fps"
    severity: str  # "info", "warning", "critical"
    metric: str  # e.g. "gpu_temp_max"
    value: float
    threshold: float
    suggestion: str  # human-readable fix suggestion

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "metric": self.metric,
            "value": round(self.value, 1),
            "threshold": round(self.threshold, 1),
            "suggestion": self.suggestion,
        }


@dataclass
class GameProfile:
    """Per-game optimization profile stored in game-profiles.json."""

    name: str
    appid: int = 0
    launch_options: str = ""
    mangohud_preset: str = "default"
    gamemode: bool = True
    notes: str = ""
    last_analyzed: str = ""
    ai_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "appid": self.appid,
            "launch_options": self.launch_options,
            "mangohud_preset": self.mangohud_preset,
            "gamemode": self.gamemode,
            "notes": self.notes,
            "last_analyzed": self.last_analyzed,
            "ai_suggestions": self.ai_suggestions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameProfile":
        return cls(
            name=data.get("name", ""),
            appid=data.get("appid", 0),
            launch_options=data.get("launch_options", ""),
            mangohud_preset=data.get("mangohud_preset", "default"),
            gamemode=data.get("gamemode", True),
            notes=data.get("notes", ""),
            last_analyzed=data.get("last_analyzed", ""),
            ai_suggestions=data.get("ai_suggestions", []),
        )


@dataclass
class HardwareSnapshot:
    """Point-in-time hardware state for AI context."""

    gpu_name: str = ""
    gpu_driver: str = ""
    gpu_vram_total_mb: int = 0
    gpu_vram_used_mb: int = 0
    gpu_temp_c: int = 0
    gpu_power_draw_w: float = 0.0
    gpu_clock_mhz: int = 0
    gpu_mem_clock_mhz: int = 0
    gpu_utilization_pct: int = 0
    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    swap_total_mb: int = 0
    swap_used_mb: int = 0
    zram_total_mb: int = 0
    zram_used_mb: int = 0
    timestamp: str = ""

    @property
    def vram_pressure_pct(self) -> float:
        """VRAM usage as a percentage (0-100). Returns 0.0 if total is unknown."""
        if self.gpu_vram_total_mb <= 0:
            return 0.0
        return (self.gpu_vram_used_mb / self.gpu_vram_total_mb) * 100

    @property
    def ram_pressure_pct(self) -> float:
        """RAM usage as a percentage (0-100). Returns 0.0 if total is unknown."""
        if self.ram_total_mb <= 0:
            return 0.0
        used = self.ram_total_mb - self.ram_available_mb
        return (used / self.ram_total_mb) * 100

    def to_context_string(self) -> str:
        """Human-readable summary for LLM context injection."""
        lines = [f"Hardware Snapshot ({self.timestamp})"]

        if self.gpu_name:
            lines.append(
                f"GPU: {self.gpu_name} (driver {self.gpu_driver})"
                f" | VRAM: {self.gpu_vram_used_mb}/{self.gpu_vram_total_mb} MB"
                f" ({self.vram_pressure_pct:.0f}%)"
                f" | Temp: {self.gpu_temp_c}C"
                f" | Power: {self.gpu_power_draw_w:.1f}W"
                f" | Clock: {self.gpu_clock_mhz} MHz"
                f" | MemClock: {self.gpu_mem_clock_mhz} MHz"
                f" | Util: {self.gpu_utilization_pct}%"
            )

        if self.cpu_model:
            lines.append(
                f"CPU: {self.cpu_model}"
                f" | Cores: {self.cpu_cores} | Threads: {self.cpu_threads}"
            )

        if self.ram_total_mb:
            lines.append(
                f"RAM: {self.ram_available_mb}/{self.ram_total_mb} MB available"
                f" ({self.ram_pressure_pct:.0f}% used)"
            )

        if self.swap_total_mb:
            lines.append(f"Swap: {self.swap_used_mb}/{self.swap_total_mb} MB used")

        if self.zram_total_mb:
            lines.append(f"ZRAM: {self.zram_used_mb}/{self.zram_total_mb} MB used")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Structured dict with gpu/cpu/memory sub-keys for JSON serialization."""
        return {
            "gpu": {
                "name": self.gpu_name,
                "driver": self.gpu_driver,
                "vram_total_mb": self.gpu_vram_total_mb,
                "vram_used_mb": self.gpu_vram_used_mb,
                "vram_pressure_pct": round(self.vram_pressure_pct, 1),
                "temp_c": self.gpu_temp_c,
                "power_draw_w": round(self.gpu_power_draw_w, 1),
                "clock_mhz": self.gpu_clock_mhz,
                "mem_clock_mhz": self.gpu_mem_clock_mhz,
                "utilization_pct": self.gpu_utilization_pct,
            },
            "cpu": {
                "model": self.cpu_model,
                "cores": self.cpu_cores,
                "threads": self.cpu_threads,
            },
            "memory": {
                "ram_total_mb": self.ram_total_mb,
                "ram_available_mb": self.ram_available_mb,
                "ram_pressure_pct": round(self.ram_pressure_pct, 1),
                "swap_total_mb": self.swap_total_mb,
                "swap_used_mb": self.swap_used_mb,
                "zram_total_mb": self.zram_total_mb,
                "zram_used_mb": self.zram_used_mb,
            },
            "timestamp": self.timestamp,
        }
