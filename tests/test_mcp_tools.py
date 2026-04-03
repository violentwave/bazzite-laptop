"""Unit tests for ai/mcp_bridge/tools.py — tool implementations."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


@pytest.fixture()
def allowlist():
    path = Path(__file__).parent.parent / "configs" / "mcp-bridge-allowlist.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


class TestAllowlistIntegrity:
    def test_has_48_tools(self, allowlist):
        assert len(allowlist["tools"]) == 52

    def test_all_expected_tools_present(self, allowlist):
        expected = {
            "system.disk_usage",
            "system.cpu_temps",
            "system.gpu_status",
            "system.memory_usage",
            "system.uptime",
            "system.service_status",
            "system.llm_models",
            "system.mcp_manifest",
            "system.llm_status",
            "system.key_status",
            "system.release_watch",
            "system.fedora_updates",
            "system.pkg_intel",
            "system.gpu_perf",
            "system.gpu_health",
            "system.cache_stats",
            "system.token_report",
            "system.pipeline_status",
            "system.budget_status",
            "security.last_scan",
            "security.health_snapshot",
            "security.status",
            "security.threat_lookup",
            "security.ip_lookup",
            "security.url_lookup",
            "knowledge.rag_query",
            "knowledge.rag_qa",
            "knowledge.ingest_docs",
            "knowledge.pattern_search",
            "knowledge.task_patterns",
            "gaming.profiles",
            "gaming.mangohud_preset",
            "logs.health_trend",
            "logs.scan_history",
            "logs.anomalies",
            "logs.search",
            "logs.stats",
            "security.cve_check",
            "security.sandbox_submit",
            "security.threat_summary",
            "security.run_scan",
            "security.run_health",
            "security.run_ingest",
            "security.correlate",
            "security.recommend_action",
            "code.search",
            "code.rag_query",
            "agents.security_audit",
            "agents.performance_tuning",
            "agents.knowledge_storage",
            "agents.code_quality",
            "agents.timer_health",
        }
        assert set(allowlist["tools"].keys()) == expected


class TestSubprocessTools:
    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_disk_usage(self, mock_exec):
        proc = AsyncMock()
        proc.communicate.return_value = (
            b"Filesystem  Size  Used  Avail  Use%\n/dev/sda1  100G  42G  58G  42%",
            b"",
        )  # noqa: E501
        proc.returncode = 0
        mock_exec.return_value = proc

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("system.disk_usage", {})
        assert "/dev/sda1" in result

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_output_truncation_at_4kb(self, mock_exec):
        proc = AsyncMock()
        proc.communicate.return_value = (b"x" * 5000, b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("system.disk_usage", {})
        assert len(result) <= 4096 + len("...[truncated]")
        assert result.endswith("...[truncated]")

    @pytest.mark.asyncio
    async def test_unknown_tool_rejected(self):
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            await execute_tool("system.format_disk", {})

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_command_not_found(self, mock_exec):
        mock_exec.side_effect = FileNotFoundError("sensors not found")

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("system.cpu_temps", {})
        assert "[Command not found]" in result

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_command_timeout(self, mock_exec):
        proc = AsyncMock()
        proc.communicate.side_effect = TimeoutError()
        proc.kill = MagicMock()
        mock_exec.return_value = proc

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("system.uptime", {})
        assert "[Tool timed out]" in result


class TestFileTail:
    """Unit tests for _read_file_tail logrotate fallback logic."""

    def test_file_tail_reads_normal_log(self, tmp_path):
        from ai.mcp_bridge.tools import _read_file_tail

        log = tmp_path / "health-2026-03-27-0800.log"
        log.write_text("line1\nline2\nline3")
        result = _read_file_tail(str(tmp_path), 10, "health-*.log")
        assert "line3" in result

    def test_file_tail_skips_zero_byte_log(self, tmp_path):
        from ai.mcp_bridge.tools import _read_file_tail

        # Primary .log is empty (logrotated); no rotated fallback either
        (tmp_path / "health-2026-03-21-1841.log").write_text("")
        with pytest.raises(FileNotFoundError):
            _read_file_tail(str(tmp_path), 10, "health-*.log")

    def test_file_tail_falls_back_to_rotated_file(self, tmp_path):
        from ai.mcp_bridge.tools import _read_file_tail

        # Primary .log is 0 bytes; data lives in the logrotated copy
        (tmp_path / "health-2026-03-21-1841.log").write_text("")
        rotated = tmp_path / "health-2026-03-21-1841.log-20260323"
        rotated.write_text("snapshot data\ngpu: ok\n")
        result = _read_file_tail(str(tmp_path), 10, "health-*.log")
        assert "snapshot data" in result
        assert "gpu: ok" in result

    def test_file_tail_prefers_primary_over_rotated(self, tmp_path):
        from ai.mcp_bridge.tools import _read_file_tail

        primary = tmp_path / "health-2026-03-27-0800.log"
        primary.write_text("fresh data")
        rotated = tmp_path / "health-2026-03-21-1841.log-20260323"
        rotated.write_text("old rotated data")
        result = _read_file_tail(str(tmp_path), 10, "health-*.log")
        assert "fresh data" in result
        assert "old rotated data" not in result

    def test_file_tail_symlink_to_nonempty_resolved(self, tmp_path):
        from ai.mcp_bridge.tools import _read_file_tail

        real_file = tmp_path / "health-2026-03-27-0800.log"
        real_file.write_text("real content")
        symlink = tmp_path / "health-latest.log"
        symlink.symlink_to(real_file)
        # Only symlink present, but target is non-empty → should read it
        result = _read_file_tail(str(tmp_path), 10, "health-latest.log")
        assert "real content" in result

    def test_file_tail_symlink_to_empty_falls_back_to_rotated(self, tmp_path):
        from ai.mcp_bridge.tools import _read_file_tail

        empty = tmp_path / "health-2026-03-21-1841.log"
        empty.write_text("")
        symlink = tmp_path / "health-latest.log"
        symlink.symlink_to(empty)
        rotated = tmp_path / "health-2026-03-21-1841.log-20260323"
        rotated.write_text("rotated content")
        result = _read_file_tail(str(tmp_path), 10, "health-*.log")
        assert "rotated content" in result


class TestFileTools:
    @pytest.mark.asyncio
    async def test_last_scan_missing_file(self):
        with patch("ai.mcp_bridge.tools._read_file_tail", side_effect=FileNotFoundError()):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("security.last_scan", {})
            assert "No data yet" in result

    @pytest.mark.asyncio
    async def test_health_snapshot_redacts_paths(self):
        fake_log = "/home/lch/security/some/path was checked\nResult: OK"
        with patch("ai.mcp_bridge.tools._read_file_tail", return_value=fake_log):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("security.health_snapshot", {})
            assert "/home/lch" not in result
            assert "[HOME]" in result


class TestStatusTool:
    @pytest.mark.asyncio
    async def test_status_whitelists_keys(self):
        full_status = {
            "state": "idle",
            "scan_type": "quick",
            "last_scan_time": "2026-03-25T10:00:00",
            "result": "clean",
            "health_status": "ok",
            "health_issues": [],
            "internal_pid": 12345,
            "secret_data": "should be stripped",
        }
        with patch("ai.mcp_bridge.tools._read_status_file", return_value=full_status):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("security.status", {})
            data = json.loads(result)
            assert "state" in data
            assert "internal_pid" not in data
            assert "secret_data" not in data


class TestRunHealth:
    def setup_method(self):
        import ai.mcp_bridge.tools as t

        t._global_call_times.clear()
        t._per_tool_call_times.clear()

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_run_health_success_message(self, mock_exec):
        proc = AsyncMock()
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("security.run_health", {})
        data = json.loads(result)
        assert data["triggered"] is True
        assert "health_snapshot" in data["message"]
        assert "run_ingest" in data["message"]

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_run_health_service_not_found(self, mock_exec):
        proc = AsyncMock()
        proc.communicate.return_value = (
            b"",
            b"Failed to start system-health.service: Unit not found.",
        )
        proc.returncode = 5
        mock_exec.return_value = proc

        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("security.run_health", {})
        data = json.loads(result)
        assert data["triggered"] is False
        assert "Unit not found" in data["error"]

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_run_health_clears_stale_lock(self, mock_exec, tmp_path):
        """Stale lock file (>5 min old) is removed before starting the service."""
        import time

        proc = AsyncMock()
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        lock_file = tmp_path / ".health-snapshot.lock"
        lock_file.write_text("")
        # Make it appear 10 minutes old
        old_time = time.time() - 600
        import os

        os.utime(lock_file, (old_time, old_time))

        with patch("ai.mcp_bridge.tools.Path") as mock_path_cls:
            # Route only the lock path through our tmp_path
            real_path = Path

            def _path_factory(arg):
                if arg == "/var/log/system-health/.health-snapshot.lock":
                    return lock_file
                return real_path(arg)

            mock_path_cls.side_effect = _path_factory
            # execute_tool imports Path at the top, so patch at usage site
            from ai.mcp_bridge import tools as _tools

            orig_path = _tools.Path
            _tools.Path = _path_factory  # type: ignore[assignment]
            try:
                from ai.mcp_bridge.tools import execute_tool

                result = await execute_tool("security.run_health", {})
            finally:
                _tools.Path = orig_path

        assert not lock_file.exists()
        data = json.loads(result)
        assert data["triggered"] is True
        assert "stale lock" in data["message"]

    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_run_health_keeps_fresh_lock(self, mock_exec, tmp_path):
        """Lock file younger than 5 minutes is NOT deleted."""
        import time

        proc = AsyncMock()
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        lock_file = tmp_path / ".health-snapshot.lock"
        lock_file.write_text("")
        # 60 seconds old — still fresh
        recent = time.time() - 60
        import os

        os.utime(lock_file, (recent, recent))

        from ai.mcp_bridge import tools as _tools

        real_path = _tools.Path

        def _path_factory(arg):
            if arg == "/var/log/system-health/.health-snapshot.lock":
                return lock_file
            return real_path(arg)

        _tools.Path = _path_factory  # type: ignore[assignment]
        try:
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("security.run_health", {})
        finally:
            _tools.Path = real_path

        assert lock_file.exists()  # not deleted
        data = json.loads(result)
        assert "stale lock" not in data["message"]


class TestConcurrencySemaphore:
    @pytest.mark.asyncio
    async def test_max_4_concurrent(self):
        """At most 4 subprocess tools should run concurrently."""
        from ai.mcp_bridge.tools import _subprocess_semaphore

        assert _subprocess_semaphore._value == 4


class TestMcpManifest:
    def setup_method(self):
        import ai.mcp_bridge.tools as t

        t._global_call_times.clear()
        t._per_tool_call_times.clear()

    @pytest.mark.asyncio
    async def test_llm_status_reads_json_file(self, tmp_path):
        status_data = {
            "updated_at": "2026-03-22T00:00:00+00:00",
            "providers": {"gemini": {"score": 0.9, "auth_broken": False}},
            "usage": {"fast": {"prompt_tokens": 10, "completion_tokens": 5, "requests": 1}},
            "models": {"fast": "gemini/gemini-2.0-flash"},
        }
        status_file = tmp_path / "llm-status.json"
        status_file.write_text(json.dumps(status_data))

        with patch(
            "ai.mcp_bridge.tools._load_allowlist",
            return_value={
                "system.llm_status": {
                    "source": "json_file",
                    "path": str(status_file),
                    "args": None,
                }
            },
        ):
            from ai.mcp_bridge.tools import execute_tool

            result = await execute_tool("system.llm_status", {})
            data = json.loads(result)
            assert "providers" in data
            assert "usage" in data
            assert "models" in data

    @pytest.mark.asyncio
    async def test_manifest_valid_json_with_tool_count(self, allowlist):
        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("system.mcp_manifest", {})
        data = json.loads(result)
        assert data["tool_count"] == len(allowlist["tools"])
        assert set(data["tools"].keys()) == set(allowlist["tools"].keys())

    @pytest.mark.asyncio
    async def test_manifest_output_under_4096_bytes(self):
        from ai.mcp_bridge.tools import execute_tool

        result = await execute_tool("system.mcp_manifest", {})
        assert len(result.encode()) < 8192

    def test_tool_output_limits(self):
        from ai.mcp_bridge.tools import _DEFAULT_OUTPUT_LIMIT, _TOOL_OUTPUT_LIMITS

        assert _DEFAULT_OUTPUT_LIMIT == 4096
        assert _TOOL_OUTPUT_LIMITS.get("system.mcp_manifest") == 16384
