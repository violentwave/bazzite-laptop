"""Tests for ai/system/perf_profiler.py"""

from unittest.mock import MagicMock, patch


class TestPerfProfiler:
    """Test PerfProfiler class."""

    def test_latency_stats_initialization(self):
        """Test LatencyStats dataclass initialization."""
        from ai.system.perf_profiler import LatencyStats

        stats = LatencyStats(
            min_ms=10.0, max_ms=100.0, mean_ms=50.0, p95_ms=90.0, samples=[10, 50, 100]
        )
        assert stats.min_ms == 10.0
        assert stats.max_ms == 100.0
        assert stats.mean_ms == 50.0
        assert stats.p95_ms == 90.0
        assert len(stats.samples) == 3

    @patch("ai.system.perf_profiler.httpx.Client")
    def test_profile_mcp_tools_uses_json_rpc(self, mock_client_cls):
        """Test profile_mcp_tools uses JSON-RPC tools/list."""
        from ai.system.perf_profiler import PerfProfiler

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {"name": "tool1", "annotations": {"destructive": False}},
                    {"name": "tool2", "annotations": {"destructive": True}},
                ]
            },
            "id": 1,
        }
        mock_client.post.return_value = mock_response

        profiler = PerfProfiler()
        tool_stats = profiler.profile_mcp_tools(n=1)

        call_args = mock_client.post.call_args_list[0]
        rpc_payload = call_args[1]["json"]
        assert rpc_payload["method"] == "tools/list"
        assert rpc_payload["jsonrpc"] == "2.0"

    def test_profile_file_io_missing_file(self):
        """Test profile_file_io handles missing files."""
        from ai.system.perf_profiler import PerfProfiler

        profiler = PerfProfiler()
        results = profiler.profile_file_io(paths=["nonexistent_file_xyz123.txt"])

        assert len(results) == 1
        assert results[0].size_bytes == -1

    @patch("ai.system.perf_profiler.httpx.Client")
    def test_profile_llm_latency_calculates_stats(self, mock_client_cls):
        """Test profile_llm_latency calculates correct stats."""
        from ai.system.perf_profiler import PerfProfiler

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
        mock_client.post.return_value = mock_response

        profiler = PerfProfiler()
        stats = profiler.profile_llm_latency(n=3)

        assert stats.samples is not None
        assert len(stats.samples) == 3

    @patch("ai.system.perf_profiler.os")
    def test_collect_system_snapshot_without_psutil(self, mock_os):
        """Test collect_system_snapshot with /proc fallback."""
        from ai.system.perf_profiler import PerfProfiler

        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=mock_open)
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_open.readline.return_value = "cpu  100 0 0 0 0 0 0"
        mock_open.read.return_value = "MemTotal: 8000000 kB\nMemAvailable: 4000000 kB\n"
        mock_os.path.exists.return_value = True

        with patch("builtins.open", mock_open):
            with patch("ai.system.perf_profiler.HAS_PSUTIL", False):
                profiler = PerfProfiler()
                snapshot = profiler.collect_system_snapshot()

        assert snapshot is not None
