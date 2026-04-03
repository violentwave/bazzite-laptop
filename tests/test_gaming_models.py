"""Test coverage for ai/gaming/models.py."""

from ai.gaming.models import (
    FrametimeStats,
    GameProfile,
    GameSession,
    HardwareSnapshot,
    LoadStats,
    PerformanceIssue,
    ThermalStats,
)


class TestFrametimeStats:
    """Test FrametimeStats dataclass."""

    def test_frametime_stats_defaults(self):
        """All fields default to 0.0."""
        stats = FrametimeStats()

        assert stats.avg_fps == 0.0
        assert stats.min_fps == 0.0
        assert stats.max_fps == 0.0
        assert stats.p1_fps == 0.0
        assert stats.p01_fps == 0.0
        assert stats.avg_frametime_ms == 0.0
        assert stats.p95_frametime_ms == 0.0
        assert stats.p99_frametime_ms == 0.0
        assert stats.stutter_pct == 0.0

    def test_frametime_stats_with_values(self):
        """Create FrametimeStats with realistic gaming data."""
        stats = FrametimeStats(
            avg_fps=120.5,
            min_fps=90.2,
            max_fps=144.0,
            p1_fps=100.1,
            p01_fps=95.0,
            avg_frametime_ms=8.3,
            p95_frametime_ms=11.1,
            p99_frametime_ms=14.2,
            stutter_pct=2.5,
        )

        assert stats.avg_fps == 120.5
        assert stats.stutter_pct == 2.5


class TestThermalStats:
    """Test ThermalStats dataclass."""

    def test_thermal_stats_defaults(self):
        """All thermal fields default to 0 or 0.0."""
        stats = ThermalStats()

        assert stats.cpu_temp_avg == 0.0
        assert stats.cpu_temp_max == 0.0
        assert stats.gpu_temp_avg == 0.0
        assert stats.gpu_temp_max == 0.0
        assert stats.throttle_events == 0

    def test_thermal_stats_high_temps(self):
        """Handle high temperature values."""
        stats = ThermalStats(
            cpu_temp_avg=75.5,
            cpu_temp_max=92.0,
            gpu_temp_avg=68.3,
            gpu_temp_max=85.0,
            throttle_events=3,
        )

        assert stats.cpu_temp_max == 92.0
        assert stats.gpu_temp_max == 85.0
        assert stats.throttle_events == 3


class TestLoadStats:
    """Test LoadStats dataclass."""

    def test_load_stats_defaults(self):
        """All load fields default to 0.0."""
        stats = LoadStats()

        assert stats.cpu_load_avg == 0.0
        assert stats.gpu_load_avg == 0.0
        assert stats.ram_used_avg_mb == 0.0
        assert stats.vram_used_avg_mb == 0.0

    def test_load_stats_full_utilization(self):
        """Handle 100% utilization."""
        stats = LoadStats(
            cpu_load_avg=100.0,
            cpu_load_max=100.0,
            gpu_load_avg=100.0,
            gpu_load_max=100.0,
            ram_used_avg_mb=16384.0,
            ram_used_max_mb=16384.0,
            vram_used_avg_mb=8192.0,
            vram_used_max_mb=8192.0,
        )

        assert stats.cpu_load_max == 100.0
        assert stats.vram_used_max_mb == 8192.0


class TestGameSession:
    """Test GameSession dataclass."""

    def test_game_session_defaults(self):
        """Empty GameSession has default values."""
        session = GameSession()

        assert session.log_path == ""
        assert session.game_name == ""
        assert session.duration_seconds == 0.0
        assert session.total_frames == 0
        assert isinstance(session.frametime, FrametimeStats)
        assert isinstance(session.thermal, ThermalStats)
        assert isinstance(session.load, LoadStats)
        assert session.raw_fps == []
        assert session.raw_frametime == []

    def test_game_session_to_dict_excludes_raw_arrays(self):
        """to_dict() excludes raw_fps and raw_frametime."""
        session = GameSession(
            log_path="/tmp/test.log",
            game_name="TestGame",
            duration_seconds=3600.5,
            total_frames=216000,
            raw_fps=[60.0] * 100,  # Should be excluded
            raw_frametime=[16.67] * 100,  # Should be excluded
            timestamp="2026-04-02T12:00:00Z",
        )

        data = session.to_dict()

        assert "log_path" in data
        assert "game_name" in data
        assert "duration_seconds" in data
        assert data["duration_seconds"] == 3600.5
        assert "raw_fps" not in data
        assert "raw_frametime" not in data

    def test_game_session_to_dict_rounds_values(self):
        """to_dict() rounds floats appropriately."""
        session = GameSession(
            game_name="Test",
            duration_seconds=123.456789,
            frametime=FrametimeStats(avg_fps=120.123456),
        )

        data = session.to_dict()

        assert data["duration_seconds"] == 123.5  # 1 decimal
        assert data["frametime"]["avg_fps"] == 120.1  # 1 decimal

    def test_game_session_to_dict_nested_structures(self):
        """to_dict() properly serializes nested dataclasses."""
        session = GameSession(
            game_name="Test",
            frametime=FrametimeStats(avg_fps=60.0),
            thermal=ThermalStats(cpu_temp_max=80.0),
            load=LoadStats(cpu_load_avg=75.0),
        )

        data = session.to_dict()

        assert "frametime" in data
        assert data["frametime"]["avg_fps"] == 60.0
        assert "thermal" in data
        assert data["thermal"]["cpu_temp_max"] == 80.0
        assert "load" in data
        assert data["load"]["cpu_load_avg"] == 75.0


class TestPerformanceIssue:
    """Test PerformanceIssue dataclass."""

    def test_performance_issue_creation(self):
        """Create PerformanceIssue with all fields."""
        issue = PerformanceIssue(
            category="thermal",
            severity="critical",
            metric="gpu_temp_max",
            value=92.5,
            threshold=90.0,
            suggestion="Improve case airflow or reduce graphics settings",
        )

        assert issue.category == "thermal"
        assert issue.severity == "critical"
        assert issue.value == 92.5
        assert "airflow" in issue.suggestion

    def test_performance_issue_to_dict_rounds_values(self):
        """to_dict() rounds value and threshold to 1 decimal."""
        issue = PerformanceIssue(
            category="stutter",
            severity="warning",
            metric="stutter_pct",
            value=5.678,
            threshold=5.0,
            suggestion="Check for background processes",
        )

        data = issue.to_dict()

        assert data["value"] == 5.7  # rounded
        assert data["threshold"] == 5.0


class TestGameProfile:
    """Test GameProfile dataclass."""

    def test_game_profile_defaults(self):
        """GameProfile has sensible defaults."""
        profile = GameProfile(name="TestGame")

        assert profile.name == "TestGame"
        assert profile.appid == 0
        assert profile.launch_options == ""
        assert profile.mangohud_preset == "default"
        assert profile.gamemode is True
        assert profile.notes == ""
        assert profile.ai_suggestions == []

    def test_game_profile_to_dict(self):
        """to_dict() serializes all fields."""
        profile = GameProfile(
            name="Cyberpunk 2077",
            appid=1091500,
            launch_options="-fullscreen",
            mangohud_preset="performance",
            gamemode=True,
            notes="DLSS Quality mode recommended",
            last_analyzed="2026-04-02T10:00:00Z",
            ai_suggestions=["Enable FSR", "Cap FPS to 120"],
        )

        data = profile.to_dict()

        assert data["name"] == "Cyberpunk 2077"
        assert data["appid"] == 1091500
        assert data["mangohud_preset"] == "performance"
        assert len(data["ai_suggestions"]) == 2

    def test_game_profile_from_dict(self):
        """from_dict() deserializes correctly."""
        data = {
            "name": "Portal 2",
            "appid": 620,
            "launch_options": "-novid",
            "mangohud_preset": "minimal",
            "gamemode": False,
            "notes": "Runs great, no tweaks needed",
            "last_analyzed": "2026-04-01T15:30:00Z",
            "ai_suggestions": [],
        }

        profile = GameProfile.from_dict(data)

        assert profile.name == "Portal 2"
        assert profile.appid == 620
        assert profile.gamemode is False

    def test_game_profile_from_dict_missing_fields(self):
        """from_dict() uses defaults for missing fields."""
        data = {"name": "MinimalGame"}

        profile = GameProfile.from_dict(data)

        assert profile.name == "MinimalGame"
        assert profile.appid == 0  # default
        assert profile.mangohud_preset == "default"  # default


class TestHardwareSnapshot:
    """Test HardwareSnapshot dataclass."""

    def test_hardware_snapshot_defaults(self):
        """HardwareSnapshot has empty/zero defaults."""
        snapshot = HardwareSnapshot()

        assert snapshot.gpu_name == ""
        assert snapshot.cpu_model == ""
        assert snapshot.ram_total_mb == 0

    def test_vram_pressure_pct_calculation(self):
        """vram_pressure_pct computes usage percentage."""
        snapshot = HardwareSnapshot(
            gpu_vram_total_mb=8192,
            gpu_vram_used_mb=6144,
        )

        assert snapshot.vram_pressure_pct == 75.0  # 6144/8192 * 100

    def test_vram_pressure_pct_zero_total(self):
        """vram_pressure_pct returns 0.0 when total is 0."""
        snapshot = HardwareSnapshot(
            gpu_vram_total_mb=0,
            gpu_vram_used_mb=100,
        )

        assert snapshot.vram_pressure_pct == 0.0

    def test_ram_pressure_pct_calculation(self):
        """ram_pressure_pct computes usage percentage."""
        snapshot = HardwareSnapshot(
            ram_total_mb=16384,
            ram_available_mb=4096,
        )

        # Used = Total - Available = 16384 - 4096 = 12288
        # Pressure = 12288 / 16384 * 100 = 75%
        assert snapshot.ram_pressure_pct == 75.0

    def test_ram_pressure_pct_zero_total(self):
        """ram_pressure_pct returns 0.0 when total is 0."""
        snapshot = HardwareSnapshot(
            ram_total_mb=0,
            ram_available_mb=1000,
        )

        assert snapshot.ram_pressure_pct == 0.0

    def test_to_context_string_full_snapshot(self):
        """to_context_string() generates human-readable summary."""
        snapshot = HardwareSnapshot(
            gpu_name="NVIDIA RTX 4060",
            gpu_driver="550.78",
            gpu_vram_total_mb=8192,
            gpu_vram_used_mb=6000,
            gpu_temp_c=68,
            gpu_power_draw_w=120.5,
            gpu_clock_mhz=2100,
            gpu_mem_clock_mhz=7000,
            gpu_utilization_pct=95,
            cpu_model="AMD Ryzen 9 7940HS",
            cpu_cores=8,
            cpu_threads=16,
            ram_total_mb=16384,
            ram_available_mb=4096,
            timestamp="2026-04-02T12:00:00Z",
        )

        context = snapshot.to_context_string()

        assert "RTX 4060" in context
        assert "7940HS" in context
        assert "6000/8192 MB" in context
        assert "68C" in context

    def test_to_dict_nested_structure(self):
        """to_dict() creates gpu/cpu/memory sub-keys."""
        snapshot = HardwareSnapshot(
            gpu_name="Test GPU",
            cpu_model="Test CPU",
            ram_total_mb=8192,
        )

        data = snapshot.to_dict()

        assert "gpu" in data
        assert data["gpu"]["name"] == "Test GPU"
        assert "cpu" in data
        assert data["cpu"]["model"] == "Test CPU"
        assert "memory" in data
        assert data["memory"]["ram_total_mb"] == 8192

    def test_to_dict_rounds_floats(self):
        """to_dict() rounds float values to 1 decimal."""
        snapshot = HardwareSnapshot(
            gpu_vram_total_mb=8192,
            gpu_vram_used_mb=6000,
            gpu_power_draw_w=120.567,
        )

        data = snapshot.to_dict()

        assert data["gpu"]["vram_pressure_pct"] == 73.2  # 6000/8192
        assert data["gpu"]["power_draw_w"] == 120.6
