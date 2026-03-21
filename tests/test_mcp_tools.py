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
    def test_has_22_tools(self, allowlist):
        assert len(allowlist["tools"]) == 22

    def test_all_expected_tools_present(self, allowlist):
        expected = {
            "system.disk_usage", "system.cpu_temps", "system.gpu_status",
            "system.memory_usage", "system.uptime", "system.service_status",
            "system.llm_models",
            "security.last_scan", "security.health_snapshot", "security.status",
            "security.threat_lookup", "knowledge.rag_query",
            "gaming.profiles", "gaming.mangohud_preset",
            "logs.health_trend", "logs.scan_history", "logs.anomalies",
            "logs.search", "logs.stats",
            "security.run_scan", "security.run_health", "security.run_ingest",
        }
        assert set(allowlist["tools"].keys()) == expected


class TestSubprocessTools:
    @pytest.mark.asyncio
    @patch("ai.mcp_bridge.tools.asyncio.create_subprocess_exec")
    async def test_disk_usage(self, mock_exec):
        proc = AsyncMock()
        proc.communicate.return_value = (b"Filesystem  Size  Used  Avail  Use%\n/dev/sda1  100G  42G  58G  42%", b"")  # noqa: E501
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


class TestConcurrencySemaphore:
    @pytest.mark.asyncio
    async def test_max_4_concurrent(self):
        """At most 4 subprocess tools should run concurrently."""
        from ai.mcp_bridge.tools import _subprocess_semaphore

        assert _subprocess_semaphore._value == 4
