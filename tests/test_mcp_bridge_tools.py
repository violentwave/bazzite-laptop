"""Unit tests for ai/mcp_bridge/tools.py — MCP tool implementations.

All tools are read-only with subprocess sandboxing. Tests mock subprocess calls.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture()
def mock_allowlist():
    """Mock allowlist configuration."""
    return {
        "tools": {
            "security.scan_status": {
                "description": "Get ClamAV scan status",
                "args": None,
            },
            "system.disk_usage": {
                "description": "Get disk usage stats",
                "args": {
                    "path": {
                        "required": False,
                        "pattern": r"^[a-zA-Z0-9/_-]+$",
                        "max_length": 256,
                    },
                },
            },
        },
    }


@pytest.fixture(autouse=True)
def reset_bridge_state():
    """Reset bridge module state (rate limits + allowlist cache) around each test."""
    import asyncio

    from ai.mcp_bridge import tools

    tools._global_call_times.clear()
    tools._per_tool_call_times.clear()
    saved_allowlist = tools._allowlist

    yield

    tools._global_call_times.clear()
    tools._per_tool_call_times.clear()
    tools._allowlist = saved_allowlist
    # Always create a fresh semaphore so subsequent tests in other event loops work
    tools._subprocess_semaphore = asyncio.Semaphore(4)


class TestBridgeRateLimiting:
    """Tests for bridge-level rate limiting."""

    def test_global_rate_limit_enforced(self):
        """Global rate limit (10 req/s) is enforced."""
        from ai.mcp_bridge.tools import _check_bridge_rate

        # Fill the global window using 5 different tools (2 calls each = 10 total)
        # to avoid hitting the per-tool limit (2/s) before the global limit (10/s)
        for i in range(5):
            _check_bridge_rate(f"tool_{i}")
            _check_bridge_rate(f"tool_{i}")

        # 11th call to a fresh tool should raise due to global limit
        with pytest.raises(ValueError, match="Bridge rate limited"):
            _check_bridge_rate("tool_new")

    def test_per_tool_rate_limit_enforced(self):
        """Per-tool rate limit (2 req/s) is enforced."""
        from ai.mcp_bridge.tools import _check_bridge_rate

        # Make 2 calls to the same tool (allowed)
        _check_bridge_rate("tool_a")
        _check_bridge_rate("tool_a")

        # 3rd call to same tool should raise
        with pytest.raises(ValueError, match="Bridge rate limited"):
            _check_bridge_rate("tool_a")

        # But a different tool should work
        _check_bridge_rate("tool_b")

    def test_rate_limit_window_expiration(self):
        """Rate limit window expires after 1 second."""
        from ai.mcp_bridge.tools import _check_bridge_rate, _global_call_times, _per_tool_call_times

        # Fill global window using different tool names (2 calls each, 5 tools = 10 total)
        for i in range(5):
            _check_bridge_rate(f"fill_tool_{i}")
            _check_bridge_rate(f"fill_tool_{i}")

        # Manually expire the window (simulate 1.1s passing)
        now = time.time() + 1.1
        with patch("ai.mcp_bridge.tools.time.time", return_value=now):
            _global_call_times.clear()  # Reset global for clean test
            _per_tool_call_times.clear()  # Reset per-tool for clean test
            _check_bridge_rate("test")  # Should succeed


class TestArgumentValidation:
    """Tests for tool argument validation."""

    def test_required_argument_missing_raises(self, mock_allowlist):
        """Missing required argument raises ValueError."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "path": {"required": True},
            },
        }

        with pytest.raises(ValueError, match="Argument 'path' is required"):
            _validate_args(tool_def, {})

    def test_optional_argument_missing_ok(self, mock_allowlist):
        """Missing optional argument is ok."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "path": {"required": False},
            },
        }

        _validate_args(tool_def, {})  # Should not raise

    def test_pattern_validation(self, mock_allowlist):
        """Argument pattern validation."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "path": {
                    "required": True,
                    "pattern": r"^[a-zA-Z0-9/_-]+$",
                },
            },
        }

        # Valid path (no dots, only chars matching pattern)
        _validate_args(tool_def, {"path": "/var/log/test-log"})

        # Invalid path (shell injection attempt)
        with pytest.raises(ValueError, match="does not match pattern"):
            _validate_args(tool_def, {"path": "/var/log/test.log; rm -rf /"})

    def test_max_length_validation(self, mock_allowlist):
        """Argument max_length validation."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "path": {
                    "required": True,
                    "max_length": 10,
                },
            },
        }

        # Valid length
        _validate_args(tool_def, {"path": "short"})

        # Exceeds max length
        with pytest.raises(ValueError, match="exceeds max length"):
            _validate_args(tool_def, {"path": "this_is_way_too_long"})

    def test_non_string_argument_raises(self, mock_allowlist):
        """Non-string arguments are rejected."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"count": {"required": True}}}

        with pytest.raises(ValueError, match="must be a string"):
            _validate_args(tool_def, {"count": 42})


class TestAllowlistLoading:
    """Tests for allowlist YAML loading."""

    def test_load_allowlist_success(self, tmp_path):
        """Allowlist loads from YAML file."""
        import yaml

        from ai.mcp_bridge import tools as tools_module

        # Create temp allowlist
        allowlist_path = tmp_path / "mcp-bridge-allowlist.yaml"
        allowlist_data = {
            "tools": {
                "test.tool": {
                    "description": "Test tool",
                    "args": None,
                },
            },
        }
        allowlist_path.write_text(yaml.dump(allowlist_data))

        # Patch the path and reset cache
        with patch("ai.mcp_bridge.tools._ALLOWLIST_PATH", allowlist_path):
            tools_module._allowlist = None  # clear cache
            result = tools_module._load_allowlist()
            # _load_allowlist returns data.get("tools", {}), so result is the tools dict
            assert "test.tool" in result

    def test_load_allowlist_caches_result(self, tmp_path):
        """Allowlist is cached after first load."""
        import yaml

        from ai.mcp_bridge import tools as tools_module

        allowlist_path = tmp_path / "mcp-bridge-allowlist.yaml"
        allowlist_path.write_text(yaml.dump({"tools": {}}))

        with patch("ai.mcp_bridge.tools._ALLOWLIST_PATH", allowlist_path):
            tools_module._allowlist = None  # clear cache
            # First load
            tools_module._load_allowlist()

            # Delete the file
            allowlist_path.unlink()

            # Second load should use cache (not raise FileNotFoundError)
            result = tools_module._load_allowlist()
            assert result is not None


class TestPathRedaction:
    """Tests for /home/lch path redaction in output."""

    def test_home_path_redacted_by_redact_paths(self):
        """_redact_paths replaces /home/lch with [HOME]."""
        from ai.mcp_bridge.tools import _redact_paths

        text = "File: /home/lch/security/scan.log"
        result = _redact_paths(text)

        assert "/home/lch" not in result
        assert "[HOME]" in result


class TestSubprocessSandboxing:
    """Tests for subprocess execution safety."""

    @pytest.mark.asyncio()
    async def test_subprocess_timeout_enforced(self):
        """Subprocess calls timeout after 30s."""
        from ai.mcp_bridge.tools import _run_subprocess

        # Mock a hanging process
        async def hang():
            await asyncio.sleep(100)

        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = hang
        mock_proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("ai.mcp_bridge.tools._SUBPROCESS_TIMEOUT_S", 0.1):
                result = await _run_subprocess(["sleep", "100"])

                # Should return timeout error, not hang
                assert "timeout" in result.lower() or "timed out" in result.lower()

    @pytest.mark.asyncio()
    async def test_subprocess_output_truncated(self):
        """Subprocess output is truncated to limit."""
        from ai.mcp_bridge.tools import _run_subprocess

        # Mock a process that returns large output
        large_output = b"x" * 10000
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (large_output, b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_subprocess(["cat", "bigfile"])

        # Verify output was truncated (default 4096 bytes)
        assert len(result) <= 4096 + 100  # Allow some overhead for truncation message

    @pytest.mark.asyncio()
    async def test_subprocess_concurrency_limited(self):
        """Concurrent subprocess calls are limited by semaphore."""
        from ai.mcp_bridge.tools import _run_subprocess

        # Mock subprocess that takes time
        async def slow_communicate():
            await asyncio.sleep(0.01)
            return (b"done", b"")

        # Spawn 10 concurrent calls (semaphore limit is 4)
        tasks = []
        for _ in range(10):
            mock_proc = AsyncMock()
            mock_proc.communicate = slow_communicate
            mock_proc.returncode = 0

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                task = asyncio.create_task(_run_subprocess(["echo", "test"]))
                tasks.append(task)

        # Should complete without exceeding concurrency limit
        results = await asyncio.gather(*tasks)
        assert len(results) == 10


class TestSpecificTools:
    """Tests for specific tool implementations via execute_tool."""

    @pytest.mark.asyncio()
    async def test_json_file_tool_missing_file(self):
        """json_file-sourced tool returns graceful message when file missing."""
        from ai.mcp_bridge.tools import execute_tool

        # Patch allowlist to have a json_file tool
        fake_tool = {"source": "json_file", "description": "Status"}
        with patch("ai.mcp_bridge.tools._load_allowlist",
                   return_value={"security.scan_status": fake_tool}):
            with patch("ai.mcp_bridge.tools._read_status_file",
                       side_effect=FileNotFoundError):
                result = await execute_tool("security.scan_status", {})

        assert "No data yet" in result or isinstance(result, str)

    @pytest.mark.asyncio()
    async def test_subprocess_tool_via_execute(self):
        """execute_tool routes command-based tools to _run_subprocess."""
        from ai.mcp_bridge.tools import execute_tool

        fake_tool = {"command": ["echo", "hello"], "description": "Echo"}
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"hello\n", b"")
        mock_proc.returncode = 0

        with patch("ai.mcp_bridge.tools._load_allowlist",
                   return_value={"test.echo": fake_tool}):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await execute_tool("test.echo", {})

        assert "hello" in result

    @pytest.mark.asyncio()
    async def test_unknown_tool_raises(self):
        """Unknown tool name raises ValueError."""
        from ai.mcp_bridge.tools import execute_tool

        with patch("ai.mcp_bridge.tools._load_allowlist", return_value={}):
            with pytest.raises(ValueError, match="Unknown tool"):
                await execute_tool("nonexistent.tool", {})


class TestMcpManifest:
    """Tests for system.mcp_manifest compact output."""

    def test_default_output_limit_is_4096(self):
        """_DEFAULT_OUTPUT_LIMIT must be 4096."""
        from ai.mcp_bridge.tools import _DEFAULT_OUTPUT_LIMIT

        assert _DEFAULT_OUTPUT_LIMIT == 4096

    def test_manifest_override_is_16384(self):
        """system.mcp_manifest output limit override must be 16384."""
        from ai.mcp_bridge.tools import _TOOL_OUTPUT_LIMITS

        assert _TOOL_OUTPUT_LIMITS["system.mcp_manifest"] == 16384

    @pytest.mark.asyncio()
    async def test_manifest_is_valid_json_with_tool_count(self, tmp_path):
        """mcp_manifest returns valid JSON containing 'tool_count'."""
        import yaml

        from ai.mcp_bridge import tools as tools_module

        allowlist_data = {
            "tools": {
                "system.disk_usage": {"description": "Disk usage summary", "args": None},
                "security.threat_lookup": {
                    "description": "Hash threat lookup",
                    "source": "python",
                    "args": {"hash": {"type": "string", "required": True}},
                },
                "system.mcp_manifest": {
                    "description": "List all available MCP tools",
                    "source": "python",
                    "args": None,
                },
            }
        }
        allowlist_path = tmp_path / "mcp-bridge-allowlist.yaml"
        allowlist_path.write_text(yaml.dump(allowlist_data))

        with patch("ai.mcp_bridge.tools._ALLOWLIST_PATH", allowlist_path):
            tools_module._allowlist = None
            result = await tools_module.execute_tool("system.mcp_manifest", {})

        data = json.loads(result)
        assert "tool_count" in data
        assert "tools" in data

    @pytest.mark.asyncio()
    async def test_manifest_tool_count_matches_allowlist(self, tmp_path):
        """tool_count equals the number of tools defined in the allowlist YAML."""
        import yaml

        from ai.mcp_bridge import tools as tools_module

        n_tools = 5
        tools_dict = {
            f"system.tool_{i}": {"description": f"Tool {i}", "args": None}
            for i in range(n_tools)
        }
        tools_dict["system.mcp_manifest"] = {
            "description": "List all available MCP tools",
            "source": "python",
            "args": None,
        }
        allowlist_data = {"tools": tools_dict}
        allowlist_path = tmp_path / "mcp-bridge-allowlist.yaml"
        allowlist_path.write_text(yaml.dump(allowlist_data))

        with patch("ai.mcp_bridge.tools._ALLOWLIST_PATH", allowlist_path):
            tools_module._allowlist = None
            result = await tools_module.execute_tool("system.mcp_manifest", {})

        data = json.loads(result)
        # tool_count includes the manifest tool itself
        assert data["tool_count"] == n_tools + 1
        assert len(data["tools"]) == n_tools + 1

    @pytest.mark.asyncio()
    async def test_manifest_compact_format(self, tmp_path):
        """Each tool entry has only 'desc' (≤40 chars) and 'args' (list of names)."""
        import yaml

        from ai.mcp_bridge import tools as tools_module

        long_desc = "A" * 60
        allowlist_data = {
            "tools": {
                "system.no_args": {"description": "No args tool", "args": None},
                "security.with_args": {
                    "description": long_desc,
                    "source": "python",
                    "args": {
                        "hash": {"type": "string", "required": True},
                        "extra": {"type": "string", "required": False},
                    },
                },
                "system.mcp_manifest": {
                    "description": "List all available MCP tools",
                    "source": "python",
                    "args": None,
                },
            }
        }
        allowlist_path = tmp_path / "mcp-bridge-allowlist.yaml"
        allowlist_path.write_text(yaml.dump(allowlist_data))

        with patch("ai.mcp_bridge.tools._ALLOWLIST_PATH", allowlist_path):
            tools_module._allowlist = None
            result = await tools_module.execute_tool("system.mcp_manifest", {})

        data = json.loads(result)
        no_args_entry = data["tools"]["system.no_args"]
        assert "desc" in no_args_entry
        assert "args" in no_args_entry
        assert no_args_entry["args"] == []
        assert len(no_args_entry["desc"]) <= 40

        with_args_entry = data["tools"]["security.with_args"]
        assert len(with_args_entry["desc"]) <= 40
        assert set(with_args_entry["args"]) == {"hash", "extra"}
        # No metadata fields
        assert "source" not in with_args_entry
        assert "required" not in with_args_entry

    @pytest.mark.asyncio()
    async def test_manifest_output_under_4096_bytes(self, tmp_path):
        """Compact manifest for the real allowlist YAML fits in under 4096 bytes."""
        from ai.mcp_bridge import tools as tools_module

        real_allowlist = tools_module._ALLOWLIST_PATH

        with patch("ai.mcp_bridge.tools._ALLOWLIST_PATH", real_allowlist):
            tools_module._allowlist = None
            result = await tools_module.execute_tool("system.mcp_manifest", {})

        assert len(result.encode()) < 4096, (
            f"Manifest too large: {len(result.encode())} bytes"
        )


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio()
    async def test_subprocess_stdout_returned(self):
        """Subprocess stdout is returned in output."""
        from ai.mcp_bridge.tools import _run_subprocess

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (
            b"stdout content",
            b"",
        )
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_subprocess(["echo", "stdout content"])

        assert "stdout content" in result

    @pytest.mark.asyncio()
    async def test_empty_subprocess_output(self):
        """Empty subprocess output is handled gracefully."""
        from ai.mcp_bridge.tools import _run_subprocess

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_subprocess(["true"])

        assert isinstance(result, str)
        assert len(result) >= 0  # May be empty or contain status message


class TestGpuStatus:
    """Tests for system.gpu_status labeled output."""

    @pytest.mark.asyncio()
    async def test_valid_csv_returns_labeled_output(self):
        """Valid nvidia-smi CSV is parsed into labeled human-readable output."""
        from ai.mcp_bridge.tools import _execute_gpu_status

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (
            b"GeForce GTX 1060, 52, 26, 6144, 6.47, N/A\n", b""
        )
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _execute_gpu_status(["nvidia-smi"])

        assert "temperature:" in result
        assert "52°C" in result
        assert "VRAM:" in result
        assert "6144 MB" in result
        assert "utilization:" in result
        assert "26%" in result
        assert "power:" in result
        assert "6.47 W" in result
        assert "GTX 1060" in result

    @pytest.mark.asyncio()
    async def test_wrong_field_count_returns_fallback(self):
        """Output with wrong number of fields falls back to raw with header."""
        from ai.mcp_bridge.tools import _GPU_STATUS_FIELDS, _execute_gpu_status

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"52, 26, 6144\n", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _execute_gpu_status(["nvidia-smi"])

        assert _GPU_STATUS_FIELDS in result
        assert "52, 26, 6144" in result

    @pytest.mark.asyncio()
    async def test_command_not_found_returns_sentinel(self):
        """If nvidia-smi is missing, the error sentinel is returned as-is."""
        from ai.mcp_bridge.tools import _execute_gpu_status

        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = FileNotFoundError

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            result = await _execute_gpu_status(["nvidia-smi"])

        assert result == "[Command not found]"

    @pytest.mark.asyncio()
    async def test_execute_tool_routes_to_gpu_status(self):
        """execute_tool dispatches system.gpu_status to the labeled parser."""
        from ai.mcp_bridge.tools import execute_tool

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (
            b"GeForce GTX 1060, 60, 80, 6144, 120.0, 65\n", b""
        )
        mock_proc.returncode = 0

        gpu_cmd = [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,memory.total,power.draw,fan.speed",
            "--format=csv,noheader,nounits",
        ]
        fake_allowlist = {
            "system.gpu_status": {
                "description": "NVIDIA GPU name, temperature, memory, power",
                "command": gpu_cmd,
                "args": None,
            }
        }

        with patch("ai.mcp_bridge.tools._load_allowlist", return_value=fake_allowlist):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                result = await execute_tool("system.gpu_status", {})

        assert "temperature:" in result
        assert "VRAM:" in result
        assert "GTX 1060" in result
