"""Unit tests for ai/agents/performance_tuning.py."""

import json
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

# Module path prefix for patching
_PT = "ai.agents.performance_tuning"


class TestCollectCpuTemps:
    def test_nominal_temps(self):
        sensors_json = json.dumps({
            "coretemp-isa-0000": {
                "Package id 0": {"temp1_input": 45.0, "temp1_max": 100.0},
                "Core 0": {"temp2_input": 43.0},
                "Core 1": {"temp2_input": 44.0},
            }
        })
        with patch(f"{_PT}._run", return_value=sensors_json):
            from ai.agents.performance_tuning import _collect_cpu_temps

            avg, max_t = _collect_cpu_temps()
        assert 40.0 <= avg <= 50.0
        assert max_t == 45.0

    def test_sensors_failure_returns_zeros(self):
        with patch(f"{_PT}._run", return_value=None):
            from ai.agents.performance_tuning import _collect_cpu_temps

            avg, max_t = _collect_cpu_temps()
        assert avg == 0.0
        assert max_t == 0.0

    def test_invalid_json_returns_zeros(self):
        with patch(f"{_PT}._run", return_value="not json"):
            from ai.agents.performance_tuning import _collect_cpu_temps

            avg, max_t = _collect_cpu_temps()
        assert avg == 0.0
        assert max_t == 0.0


class TestCollectGpuStats:
    def test_parses_nvidia_smi_output(self):
        with patch(f"{_PT}._run", return_value="41, 3, 5.27, 512\n"):
            from ai.agents.performance_tuning import _collect_gpu_stats

            result = _collect_gpu_stats()
        assert result["temp"] == 41
        assert result["utilization"] == 3
        assert result["power_watts"] == 5.27
        assert result["memory_used_mb"] == 512
        assert "unavailable" not in result

    def test_nvidia_smi_failure_returns_unavailable(self):
        with patch(f"{_PT}._run", return_value=None):
            from ai.agents.performance_tuning import _collect_gpu_stats

            result = _collect_gpu_stats()
        assert result.get("unavailable") is True


class TestCollectMemory:
    def test_parses_free_output(self):
        free_out = (
            "               total        used        free\n"
            "Mem:     16000000000  8000000000  8000000000\n"
            "Swap:    33000000000   100000000 32900000000\n"
        )
        with patch(f"{_PT}._run", return_value=free_out):
            from ai.agents.performance_tuning import _collect_memory

            mem_pct, swap_pct = _collect_memory()
        assert mem_pct == 50.0
        assert round(swap_pct, 1) == 0.3

    def test_failure_returns_zeros(self):
        with patch(f"{_PT}._run", return_value=None):
            from ai.agents.performance_tuning import _collect_memory

            mem_pct, swap_pct = _collect_memory()
        assert mem_pct == 0.0
        assert swap_pct == 0.0


class TestCollectDisk:
    def test_parses_df_output_with_steam(self):
        df_out = (
            "Filesystem      1B-blocks       Used  Available Use% Mounted on\n"
            "/dev/sda1   499963174912 391600123904 108363051008  79% /home\n"
            "/dev/sdb1  1000000536576 551234567890 448765968686  56%"
            " /run/media/lch/SteamLibrary\n"
        )
        steam_mock = MagicMock(
            exists=lambda: True,
            __str__=lambda s: "/run/media/lch/SteamLibrary",
        )
        with (
            patch(f"{_PT}._run", return_value=df_out),
            patch(f"{_PT}.STEAM_MOUNT", steam_mock),
        ):
            from ai.agents.performance_tuning import _collect_disk

            result = _collect_disk()
        assert result["home"] == 79.0
        assert result["steam"] == 56.0

    def test_steam_not_mounted_skips(self):
        steam_mock = MagicMock(exists=lambda: False)
        df_out = "Filesystem ...\n/dev/sda1 ... ... ...  55% /home\n"
        with (
            patch(f"{_PT}.STEAM_MOUNT", steam_mock),
            patch(f"{_PT}._run", return_value=df_out),
        ):
            from ai.agents.performance_tuning import _collect_disk

            result = _collect_disk()
        assert result["steam"] is None


class TestBuildRecommendations:
    def _call(self, **kwargs):
        defaults = {
            "cpu_max": 45.0,
            "gpu": {"temp": 40, "utilization": 2, "power_watts": 5.0},
            "mem_pct": 40.0,
            "swap_pct": 0.0,
            "disk": {"home": 60.0, "steam": 50.0},
            "load_1m": 0.5,
        }
        defaults.update(kwargs)
        from ai.agents.performance_tuning import _build_recommendations

        return _build_recommendations(**defaults)

    def test_all_nominal_returns_optimal(self):
        recs, status = self._call()
        assert status == "optimal"
        assert any("nominal" in r or "idle" in r for r in recs)

    def test_hot_cpu_returns_attention(self):
        recs, status = self._call(cpu_max=82.0)
        assert status == "attention_needed"
        assert any("thermal paste" in r for r in recs)

    def test_hot_gpu_returns_attention(self):
        recs, status = self._call(
            gpu={"temp": 78, "utilization": 90, "power_watts": 100.0}
        )
        assert status == "attention_needed"
        assert any("airflow" in r for r in recs)

    def test_high_memory_returns_attention(self):
        recs, status = self._call(mem_pct=90.0)
        assert status == "attention_needed"
        assert any("memory" in r.lower() for r in recs)

    def test_heavy_swap_returns_attention(self):
        recs, status = self._call(swap_pct=60.0)
        assert status == "attention_needed"
        assert any("swap" in r.lower() for r in recs)

    def test_home_disk_nearly_full_returns_attention(self):
        recs, status = self._call(disk={"home": 88.0, "steam": None})
        assert status == "attention_needed"
        assert any("SSD nearly full" in r for r in recs)

    def test_steam_disk_nearly_full_returns_attention(self):
        recs, status = self._call(disk={"home": 60.0, "steam": 93.0})
        assert status == "attention_needed"
        assert any("Steam drive nearly full" in r for r in recs)

    def test_high_load_returns_attention(self):
        recs, status = self._call(load_1m=5.0)
        assert status == "attention_needed"
        assert any("runaway" in r for r in recs)

    def test_minor_disk_returns_acceptable(self):
        recs, status = self._call(disk={"home": 80.0, "steam": None})
        assert status == "acceptable"

    def test_gpu_unavailable_message(self):
        recs, _status = self._call(gpu={"unavailable": True})
        assert any("unavailable" in r for r in recs)


def _run_tuning_patched(tmp_path, gpu_override=None):
    """Helper: run run_tuning with all collectors mocked."""
    gpu = gpu_override or {
        "temp": 41, "utilization": 3, "power_watts": 5.27, "memory_used_mb": 512
    }
    patches = [
        patch(f"{_PT}._collect_cpu_temps", return_value=(45.0, 52.0)),
        patch(f"{_PT}._collect_gpu_stats", return_value=gpu),
        patch(f"{_PT}._collect_memory", return_value=(42.5, 0.0)),
        patch(f"{_PT}._collect_disk", return_value={"home": 78.3, "steam": 55.1}),
        patch(f"{_PT}._collect_load", return_value=(0.5, 0.4, 0.3)),
        patch(f"{_PT}._get_gaming_profiles_count", return_value=3),
        patch(f"{_PT}.PERF_REPORTS_DIR", tmp_path / "reports"),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from ai.agents.performance_tuning import run_tuning

        return run_tuning()


class TestRunTuning:
    def test_full_workflow_writes_report(self, tmp_path):
        result = _run_tuning_patched(tmp_path)

        assert result["cpu_temp_avg"] == 45.0
        assert result["cpu_temp_max"] == 52.0
        assert result["gpu_temp"] == 41
        assert result["memory_used_pct"] == 42.5
        assert result["gaming_profiles_count"] == 3
        assert "timestamp" in result
        assert "status" in result
        assert "recommendations" in result

        files = list((tmp_path / "reports").glob("perf-*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["status"] == result["status"]

    def test_report_keys_complete(self, tmp_path):
        result = _run_tuning_patched(tmp_path)

        expected_keys = {
            "timestamp", "cpu_temp_avg", "cpu_temp_max",
            "gpu_temp", "gpu_utilization", "gpu_power_watts",
            "memory_used_pct", "swap_used_pct",
            "disk_home_used_pct", "disk_steam_used_pct",
            "load_avg_1m", "gaming_profiles_count",
            "recommendations", "status",
        }
        assert set(result.keys()) == expected_keys

    def test_gpu_unavailable_handled(self, tmp_path):
        result = _run_tuning_patched(tmp_path, gpu_override={"unavailable": True})

        assert result["gpu_temp"] is None
        assert result["gpu_utilization"] is None
        assert result["gpu_power_watts"] is None
