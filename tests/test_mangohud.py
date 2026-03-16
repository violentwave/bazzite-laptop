"""Unit tests for ai/gaming/mangohud.py."""

from unittest.mock import MagicMock, patch

import pytest

from ai.gaming.mangohud import (
    _BANNED_PATTERNS,
    analyze_performance,
    parse_mangohud_log,
    suggest_optimizations,
)
from ai.gaming.models import (
    FrametimeStats,
    GameSession,
    LoadStats,
    PerformanceIssue,
    ThermalStats,
)

# ── Sample CSV data ──

SAMPLE_CSV = """\
# MangoHud 0.7.2
# application: TestGame
fps,frametime,cpu_load,gpu_load,cpu_temp,gpu_temp,ram_used,vram_used
60.1,16.63,45,78,72,65,8192,3200
59.8,16.72,47,80,73,66,8200,3210
58.5,17.09,52,82,74,67,8210,3220
61.2,16.34,44,77,72,65,8190,3200
55.0,18.18,65,85,76,68,8250,3250
30.0,33.33,90,95,82,78,8500,3500
62.0,16.13,42,75,71,64,8180,3190
59.0,16.95,48,81,73,66,8200,3210
60.5,16.53,46,79,72,65,8195,3205
58.0,17.24,50,83,74,67,8220,3230
"""

THERMAL_THROTTLE_CSV = """\
fps,frametime,cpu_load,gpu_load,cpu_temp,gpu_temp,ram_used,vram_used
25.0,40.00,98,99,96,92,8500,5950
24.0,41.67,99,99,97,93,8550,5960
23.0,43.48,99,98,98,91,8520,5940
"""


# ── Parsing tests ──


class TestMangoHudParsing:
    """Tests for parse_mangohud_log."""

    def test_parse_basic_csv(self, tmp_path):
        """Verify correct frame count from sample CSV."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        assert session.total_frames == 10

    def test_parse_fps_stats(self, tmp_path):
        """Verify avg/min/max FPS are computed correctly."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        assert session.frametime.min_fps == pytest.approx(30.0)
        assert session.frametime.max_fps == pytest.approx(62.0)
        expected_avg = (
            60.1 + 59.8 + 58.5 + 61.2 + 55.0 + 30.0 + 62.0 + 59.0 + 60.5 + 58.0
        ) / 10
        assert session.frametime.avg_fps == pytest.approx(expected_avg, rel=1e-3)

    def test_parse_frametime_stats(self, tmp_path):
        """Verify average frametime is computed."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        ft_values = [16.63, 16.72, 17.09, 16.34, 18.18, 33.33, 16.13, 16.95, 16.53, 17.24]
        expected_avg = sum(ft_values) / len(ft_values)
        assert session.frametime.avg_frametime_ms == pytest.approx(expected_avg, rel=1e-3)

    def test_parse_thermal_stats(self, tmp_path):
        """Verify avg/max temperatures are correct."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        cpu_temps = [72, 73, 74, 72, 76, 82, 71, 73, 72, 74]
        gpu_temps = [65, 66, 67, 65, 68, 78, 64, 66, 65, 67]
        assert session.thermal.cpu_temp_max == pytest.approx(82.0)
        assert session.thermal.gpu_temp_max == pytest.approx(78.0)
        assert session.thermal.cpu_temp_avg == pytest.approx(
            sum(cpu_temps) / len(cpu_temps), rel=1e-3,
        )
        assert session.thermal.gpu_temp_avg == pytest.approx(
            sum(gpu_temps) / len(gpu_temps), rel=1e-3,
        )

    def test_parse_load_stats(self, tmp_path):
        """Verify avg/max loads are correct."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        cpu_loads = [45, 47, 52, 44, 65, 90, 42, 48, 46, 50]
        gpu_loads = [78, 80, 82, 77, 85, 95, 75, 81, 79, 83]
        assert session.load.cpu_load_max == pytest.approx(90.0)
        assert session.load.gpu_load_max == pytest.approx(95.0)
        assert session.load.cpu_load_avg == pytest.approx(
            sum(cpu_loads) / len(cpu_loads), rel=1e-3,
        )
        assert session.load.gpu_load_avg == pytest.approx(
            sum(gpu_loads) / len(gpu_loads), rel=1e-3,
        )

    def test_parse_duration(self, tmp_path):
        """Verify computed duration is positive."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        assert session.duration_seconds > 0

    def test_parse_game_name_from_comment(self, tmp_path):
        """Verify game name is extracted from # application: comment."""
        p = tmp_path / "test.csv"
        p.write_text(SAMPLE_CSV)
        session = parse_mangohud_log(p)
        assert session.game_name == "TestGame"

    def test_parse_missing_columns(self, tmp_path):
        """CSV with only fps and frametime produces partial data without crash."""
        csv_data = "fps,frametime\n60.0,16.67\n59.0,16.95\n"
        p = tmp_path / "partial.csv"
        p.write_text(csv_data)
        session = parse_mangohud_log(p)
        assert session.total_frames == 2
        assert session.thermal.cpu_temp_avg == 0.0
        assert session.thermal.gpu_temp_avg == 0.0
        assert session.load.cpu_load_avg == 0.0

    def test_parse_empty_file(self, tmp_path):
        """Empty file raises ValueError."""
        p = tmp_path / "empty.csv"
        p.write_text("")
        with pytest.raises(ValueError, match="No CSV content"):
            parse_mangohud_log(p)

    def test_parse_header_only(self, tmp_path):
        """Header-only file (no data rows) raises ValueError."""
        p = tmp_path / "header_only.csv"
        p.write_text("fps,frametime,cpu_load\n")
        with pytest.raises(ValueError, match="No valid data rows"):
            parse_mangohud_log(p)

    def test_parse_bad_rows_skipped(self, tmp_path):
        """Rows with non-numeric values are silently skipped."""
        csv_data = (
            "fps,frametime,cpu_load,gpu_load,cpu_temp,gpu_temp,ram_used,vram_used\n"
            "60.0,16.67,45,78,72,65,8192,3200\n"
            "N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A\n"
            "59.0,16.95,47,80,73,66,8200,3210\n"
        )
        p = tmp_path / "bad_rows.csv"
        p.write_text(csv_data)
        session = parse_mangohud_log(p)
        assert session.total_frames == 2

    def test_parse_file_not_found(self, tmp_path):
        """Non-existent file raises FileNotFoundError."""
        p = tmp_path / "nonexistent.csv"
        with pytest.raises(FileNotFoundError):
            parse_mangohud_log(p)


# ── Analysis tests ──


class TestPerformanceAnalysis:
    """Tests for analyze_performance."""

    def _make_session(self, **kwargs) -> GameSession:
        """Create a GameSession with sensible defaults, overriding with kwargs."""
        defaults = {
            "game_name": "TestGame",
            "total_frames": 1000,
            "duration_seconds": 60.0,
            "frametime": FrametimeStats(
                avg_fps=60.0, min_fps=50.0, max_fps=70.0,
                p1_fps=45.0, p01_fps=40.0,
                avg_frametime_ms=16.67, p95_frametime_ms=18.0,
                p99_frametime_ms=20.0, stutter_pct=1.0,
            ),
            "thermal": ThermalStats(
                cpu_temp_avg=70.0, cpu_temp_max=75.0,
                gpu_temp_avg=65.0, gpu_temp_max=70.0,
            ),
            "load": LoadStats(
                cpu_load_avg=50.0, cpu_load_max=70.0,
                gpu_load_avg=70.0, gpu_load_max=85.0,
                ram_used_avg_mb=8000.0, ram_used_max_mb=8500.0,
                vram_used_avg_mb=3000.0, vram_used_max_mb=3500.0,
            ),
        }
        defaults.update(kwargs)

        # Pull out nested dataclass overrides
        thermal = defaults.pop("thermal")
        load = defaults.pop("load")
        frametime = defaults.pop("frametime")

        return GameSession(
            **defaults, thermal=thermal, load=load, frametime=frametime,
        )

    def test_no_issues_clean_session(self):
        """Good metrics produce an empty issue list."""
        session = self._make_session()
        issues = analyze_performance(session)
        assert issues == []

    def test_gpu_thermal_critical(self):
        """GPU temp max >= 90 triggers critical thermal issue."""
        session = self._make_session(
            thermal=ThermalStats(
                cpu_temp_avg=70, cpu_temp_max=75,
                gpu_temp_avg=80, gpu_temp_max=92,
            ),
        )
        issues = analyze_performance(session)
        thermal_issues = [
            i for i in issues
            if i.category == "thermal" and i.metric == "gpu_temp_max"
        ]
        assert len(thermal_issues) == 1
        assert thermal_issues[0].severity == "critical"

    def test_cpu_thermal_critical(self):
        """CPU temp max >= 95 triggers critical thermal issue."""
        session = self._make_session(
            thermal=ThermalStats(
                cpu_temp_avg=80, cpu_temp_max=96,
                gpu_temp_avg=65, gpu_temp_max=70,
            ),
        )
        issues = analyze_performance(session)
        thermal_issues = [
            i for i in issues
            if i.category == "thermal" and i.metric == "cpu_temp_max"
        ]
        assert len(thermal_issues) == 1
        assert thermal_issues[0].severity == "critical"

    def test_vram_pressure_warning(self):
        """VRAM avg >= 5600 triggers warning."""
        session = self._make_session(
            load=LoadStats(
                cpu_load_avg=50, cpu_load_max=70,
                gpu_load_avg=70, gpu_load_max=85,
                ram_used_avg_mb=8000, ram_used_max_mb=8500,
                vram_used_avg_mb=5650, vram_used_max_mb=5800,
            ),
        )
        issues = analyze_performance(session)
        vram_issues = [i for i in issues if i.category == "vram_pressure"]
        assert len(vram_issues) == 1
        assert vram_issues[0].severity == "warning"

    def test_stutter_warning(self):
        """Stutter pct >= 5 triggers warning."""
        session = self._make_session(
            frametime=FrametimeStats(
                avg_fps=60.0, min_fps=50.0, max_fps=70.0,
                p1_fps=45.0, p01_fps=40.0,
                avg_frametime_ms=16.67, p95_frametime_ms=18.0,
                p99_frametime_ms=20.0, stutter_pct=8.0,
            ),
        )
        issues = analyze_performance(session)
        stutter_issues = [i for i in issues if i.category == "stutter"]
        assert len(stutter_issues) == 1
        assert stutter_issues[0].severity == "warning"

    def test_low_fps(self):
        """Average FPS < 30 triggers warning."""
        session = self._make_session(
            frametime=FrametimeStats(
                avg_fps=25.0, min_fps=20.0, max_fps=30.0,
                p1_fps=15.0, p01_fps=12.0,
                avg_frametime_ms=40.0, p95_frametime_ms=50.0,
                p99_frametime_ms=55.0, stutter_pct=1.0,
            ),
        )
        issues = analyze_performance(session)
        fps_issues = [i for i in issues if i.category == "low_fps"]
        assert len(fps_issues) >= 1
        assert all(i.severity == "warning" for i in fps_issues)

    def test_multiple_issues_sorted(self):
        """Critical issues sort before warnings."""
        session = self._make_session(
            thermal=ThermalStats(
                cpu_temp_avg=70, cpu_temp_max=96,
                gpu_temp_avg=80, gpu_temp_max=92,
            ),
            frametime=FrametimeStats(
                avg_fps=25.0, min_fps=20.0, max_fps=30.0,
                p1_fps=15.0, p01_fps=12.0,
                avg_frametime_ms=40.0, p95_frametime_ms=50.0,
                p99_frametime_ms=55.0, stutter_pct=8.0,
            ),
        )
        issues = analyze_performance(session)
        assert len(issues) >= 3
        # All critical issues come before any warning
        severities = [i.severity for i in issues]
        critical_indices = [idx for idx, s in enumerate(severities) if s == "critical"]
        warning_indices = [idx for idx, s in enumerate(severities) if s == "warning"]
        if critical_indices and warning_indices:
            assert max(critical_indices) < min(warning_indices)

    def test_thermal_throttle_csv(self, tmp_path):
        """Full pipeline with THERMAL_THROTTLE_CSV detects multiple critical issues."""
        p = tmp_path / "throttle.csv"
        p.write_text(THERMAL_THROTTLE_CSV)
        session = parse_mangohud_log(p)
        issues = analyze_performance(session)

        categories = {i.category for i in issues}
        assert "thermal" in categories
        assert "vram_pressure" in categories

        critical_count = sum(1 for i in issues if i.severity == "critical")
        assert critical_count >= 2


# ── Suggestion tests ──


class TestSuggestOptimizations:
    """Tests for suggest_optimizations."""

    @patch("ai.gaming.mangohud.route_query")
    def test_llm_suggestions_returned(self, mock_route):
        """LLM numbered list response is parsed into suggestion strings."""
        mock_route.return_value = (
            "1. Lower texture quality to Medium\n"
            "2. Enable shader pre-caching\n"
            "3. Cap FPS to 60\n"
        )
        issues = [PerformanceIssue(
            category="thermal", severity="warning",
            metric="gpu_temp_avg", value=83, threshold=82,
            suggestion="GPU averaging 83C (high)",
        )]
        result = suggest_optimizations(issues, "TestGame")
        assert len(result) == 3
        assert any("texture" in s.lower() for s in result)
        mock_route.assert_called_once()

    @patch("ai.gaming.mangohud.route_query")
    def test_rate_limited_returns_static(self, mock_route):
        """When rate limiter says no, static suggestions are returned."""
        limiter = MagicMock()
        limiter.can_call.return_value = False
        issues = [PerformanceIssue(
            category="thermal", severity="warning",
            metric="gpu_temp_avg", value=83, threshold=82,
            suggestion="GPU averaging 83C (high)",
        )]
        result = suggest_optimizations(issues, "TestGame", rate_limiter=limiter)
        assert len(result) > 0
        mock_route.assert_not_called()

    @patch("ai.gaming.mangohud.route_query")
    def test_llm_failure_returns_static(self, mock_route):
        """When LLM raises an exception, static fallback is used."""
        mock_route.side_effect = RuntimeError("LLM unavailable")
        issues = [PerformanceIssue(
            category="stutter", severity="warning",
            metric="stutter_pct", value=8, threshold=5,
            suggestion="Stutter rate 8.0% (noticeable hitching)",
        )]
        result = suggest_optimizations(issues, "TestGame")
        assert len(result) > 0
        assert any(
            "shader" in s.lower() or "shadow" in s.lower()
            for s in result
        )

    @patch("ai.gaming.mangohud.route_query")
    def test_prime_offload_filtered(self, mock_route):
        """Suggestions containing banned PRIME offload vars are stripped."""
        mock_route.return_value = (
            "1. Set __NV_PRIME_RENDER_OFFLOAD=1 in launch options\n"
            "2. Lower texture quality to Medium\n"
            "3. Use prime-run to force NVIDIA GPU\n"
            "4. Cap FPS to 60\n"
        )
        issues = [PerformanceIssue(
            category="low_fps", severity="warning",
            metric="avg_fps", value=25, threshold=30,
            suggestion="Average FPS 25.0 (below 30)",
        )]
        result = suggest_optimizations(issues, "TestGame")
        for line in result:
            for banned in _BANNED_PATTERNS:
                assert banned not in line
        # Should still have the non-banned suggestions
        assert len(result) == 2

    @patch("ai.gaming.mangohud.route_query")
    def test_empty_issues_no_llm_call(self, mock_route):
        """No issues means no LLM call and empty result."""
        result = suggest_optimizations([], "TestGame")
        assert result == []
        mock_route.assert_not_called()
