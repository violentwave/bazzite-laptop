"""Test coverage for ai/mcp_bridge/tools.py."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBridgeRateLimiting:
    """Test bridge-level rate limiting."""

    @pytest.mark.asyncio
    async def test_global_rate_limit_enforcement(self):
        """Enforces global rate limit of BRIDGE_RATE_GLOBAL req/s."""
        # Clear state
        from ai.mcp_bridge.tools import (
            _BRIDGE_RATE_GLOBAL,
            _check_bridge_rate,
            _global_call_times,
            _per_tool_call_times,
        )
        _global_call_times.clear()
        _per_tool_call_times.clear()

        # Use unique tool names to avoid per-tool limit while testing global limit
        for i in range(_BRIDGE_RATE_GLOBAL):
            _check_bridge_rate(f"test.tool{i}")  # Should not raise

        # Next call should raise (global limit exhausted)
        with pytest.raises(ValueError, match="Bridge rate limited"):
            _check_bridge_rate("test.tool_extra")

    @pytest.mark.asyncio
    async def test_per_tool_rate_limit_enforcement(self):
        """Enforces per-tool rate limit of BRIDGE_RATE_PER_TOOL req/s."""
        from ai.mcp_bridge.tools import (
            _BRIDGE_RATE_PER_TOOL,
            _check_bridge_rate,
            _global_call_times,
            _per_tool_call_times,
        )
        _global_call_times.clear()
        _per_tool_call_times.clear()

        # Should allow up to BRIDGE_RATE_PER_TOOL calls for same tool
        for _ in range(_BRIDGE_RATE_PER_TOOL):
            _check_bridge_rate("specific.tool")

        # Next call to same tool should raise
        with pytest.raises(ValueError, match="Bridge rate limited"):
            _check_bridge_rate("specific.tool")

        # But different tool should work
        _check_bridge_rate("other.tool")  # Should not raise


class TestValidateArgs:
    """Test argument validation."""

    def test_validates_required_args(self):
        """Raises ValueError when required arg is missing."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "required_arg": {
                    "required": True,
                }
            }
        }

        with pytest.raises(ValueError, match="required"):
            _validate_args(tool_def, {})

    def test_validates_arg_pattern(self):
        """Raises ValueError when arg doesn't match pattern."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "hash": {
                    "pattern": r"^[0-9a-fA-F]{64}$",
                }
            }
        }

        # Valid SHA256
        _validate_args(tool_def, {"hash": "a" * 64})  # Should not raise

        # Invalid pattern
        with pytest.raises(ValueError, match="pattern"):
            _validate_args(tool_def, {"hash": "invalid"})

    def test_validates_max_length(self):
        """Raises ValueError when arg exceeds max_length."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "query": {
                    "max_length": 10,
                }
            }
        }

        _validate_args(tool_def, {"query": "short"})  # Should not raise

        with pytest.raises(ValueError, match="max length"):
            _validate_args(tool_def, {"query": "this is way too long"})

    def test_allows_optional_args_to_be_missing(self):
        """Allows optional args to be None or missing."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "optional_arg": {
                    "required": False,
                }
            }
        }

        _validate_args(tool_def, {})  # Should not raise

    def test_requires_string_type(self):
        """Raises ValueError when arg is not a string."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {
                "text": {}
            }
        }

        with pytest.raises(ValueError, match="must be a string"):
            _validate_args(tool_def, {"text": 123})


class TestOutputTruncation:
    """Test output truncation and redaction."""

    def test_truncates_output_at_limit(self):
        """Truncates output to DEFAULT_OUTPUT_LIMIT and adds marker."""
        from ai.mcp_bridge.tools import _DEFAULT_OUTPUT_LIMIT, _truncate

        long_text = "x" * (_DEFAULT_OUTPUT_LIMIT + 1000)
        result = _truncate(long_text)

        assert len(result) == _DEFAULT_OUTPUT_LIMIT + len("...[truncated]")
        assert result.endswith("...[truncated]")

    def test_preserves_short_output(self):
        """Doesn't truncate output under the limit."""
        from ai.mcp_bridge.tools import _truncate

        short_text = "short text"
        result = _truncate(short_text)

        assert result == short_text

    def test_redacts_home_paths(self):
        """Replaces /home/lch with [HOME]."""
        from ai.mcp_bridge.tools import _redact_paths

        text = "File at /home/lch/secret/file.txt"
        result = _redact_paths(text)

        assert "/home/lch" not in result
        assert "[HOME]" in result


class TestReadFileTail:
    """Test log file reading with fallback."""

    def test_reads_last_n_lines(self, tmp_path):
        """Reads last N lines from a file."""
        from ai.mcp_bridge.tools import _read_file_tail

        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join([f"line{i}" for i in range(100)]))

        result = _read_file_tail(str(log_file), lines=5)
        lines = result.split("\n")

        assert len(lines) == 5
        assert "line99" in lines[-1]

    def test_handles_directory_with_pattern(self, tmp_path):
        """Finds latest non-empty file matching pattern in directory."""
        from ai.mcp_bridge.tools import _read_file_tail

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # Create multiple log files
        (log_dir / "health-old.log").write_text("")
        (log_dir / "health-new.log").write_text("content")

        result = _read_file_tail(str(log_dir), lines=10, pattern="health-*.log")

        assert "content" in result

    def test_follows_symlink_if_nonempty(self, tmp_path):
        """Resolves symlink target if non-empty."""
        from ai.mcp_bridge.tools import _read_file_tail

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        target = log_dir / "actual.log"
        target.write_text("target content")

        symlink = log_dir / "health-latest.log"
        symlink.symlink_to(target)

        result = _read_file_tail(str(log_dir), lines=10, pattern="health-*.log")

        assert "target content" in result

    def test_falls_back_to_rotated_files(self, tmp_path):
        """Falls back to logrotated files when primary files are empty."""
        from ai.mcp_bridge.tools import _read_file_tail

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # Primary file is empty (logrotated)
        (log_dir / "health-snapshot.log").write_text("")

        # Rotated file has content
        (log_dir / "health-snapshot.log-20260402").write_text("rotated content")

        result = _read_file_tail(str(log_dir), lines=10, pattern="health-*.log")

        assert "rotated content" in result

    def test_raises_when_no_nonempty_files(self, tmp_path):
        """Raises FileNotFoundError when all files are empty."""
        from ai.mcp_bridge.tools import _read_file_tail

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        (log_dir / "health-snapshot.log").write_text("")
        (log_dir / "health-snapshot.log-20260401").write_text("")

        with pytest.raises(FileNotFoundError, match="No non-empty files"):
            _read_file_tail(str(log_dir), lines=10, pattern="health-*.log")


class TestGpuHealthTool:
    """Test GPU health monitoring."""

    @pytest.mark.asyncio
    async def test_gpu_health_parses_throttle_reasons(self):
        """Decodes throttle reason bitmask into active reasons."""
        from ai.mcp_bridge.tools import _execute_gpu_tool

        # Mock nvidia-smi output
        nvidia_output = "75,P0,1800,4000,120,4096,2048,6144,85,0x08"

        with patch("ai.mcp_bridge.tools._run_subprocess", return_value=nvidia_output):
            result = await _execute_gpu_tool("system.gpu_health")

            data = json.loads(result)

            assert data["is_throttling"] is True
            assert "HW_SLOWDOWN" in data["throttle_active"]

    @pytest.mark.asyncio
    async def test_gpu_health_warns_on_low_headroom(self):
        """Fires desktop notification when headroom is dangerously low."""
        from ai.mcp_bridge.tools import _execute_gpu_tool

        # Temperature 77°C, threshold 83°C → headroom 6°C < 8°C warning
        nvidia_output = "77,P0,1800,4000,120,4096,2048,6144,85,0x00"

        with patch("ai.mcp_bridge.tools._run_subprocess", return_value=nvidia_output):
            result = await _execute_gpu_tool("system.gpu_health")

            data = json.loads(result)

            assert "warning" in data
            assert "headroom only 6°C" in data["warning"]

    @pytest.mark.asyncio
    async def test_gpu_health_handles_nvidia_smi_missing(self):
        """Returns error when nvidia-smi not available."""
        from ai.mcp_bridge.tools import _execute_gpu_tool

        with patch("ai.mcp_bridge.tools._run_subprocess", return_value="[Command not found]"):
            result = await _execute_gpu_tool("system.gpu_health")

            data = json.loads(result)

            assert "error" in data


class TestSubprocessExecution:
    """Test subprocess command execution."""

    @pytest.mark.asyncio
    async def test_runs_command_with_timeout(self):
        """Executes command and returns stdout."""
        from ai.mcp_bridge.tools import _run_subprocess

        result = await _run_subprocess(["echo", "test"])

        assert "test" in result

    @pytest.mark.asyncio
    async def test_handles_command_not_found(self):
        """Returns sentinel when command doesn't exist."""
        from ai.mcp_bridge.tools import _run_subprocess

        result = await _run_subprocess(["nonexistent-command-xyz"])

        assert result == "[Command not found]"

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """Kills process and returns sentinel on timeout."""
        from ai.mcp_bridge.tools import _run_subprocess

        # Command that sleeps longer than timeout
        with patch("ai.mcp_bridge.tools._SUBPROCESS_TIMEOUT_S", 0.1):
            result = await _run_subprocess(["sleep", "10"])

            assert result == "[Tool timed out]"

    @pytest.mark.asyncio
    async def test_enforces_concurrency_limit(self):
        """Limits concurrent subprocess execution."""
        from ai.mcp_bridge.tools import _run_subprocess

        # Set semaphore to 1 for testing
        with patch("ai.mcp_bridge.tools._subprocess_semaphore", asyncio.Semaphore(1)):
            # Start first command (holds semaphore)
            task1 = asyncio.create_task(_run_subprocess(["sleep", "0.1"]))

            # Give it time to acquire semaphore
            await asyncio.sleep(0.01)

            # Second command should wait
            task2 = asyncio.create_task(_run_subprocess(["echo", "test"]))

            # Wait for both
            results = await asyncio.gather(task1, task2)

            assert len(results) == 2


class TestPythonToolExecution:
    """Test Python module tool execution."""

    @pytest.mark.asyncio
    async def test_threat_lookup_sanitizes_output(self):
        """Strips raw_data from threat lookup results."""
        from ai.mcp_bridge.tools import _execute_python_tool

        tool_def = {"source": "python"}
        args = {"hash": "a" * 64}

        mock_result = {
            "hash": "a" * 64,
            "source": "virustotal",
            "risk_level": "high",
            "raw_data": {"sensitive": "data"},  # Should be stripped
        }

        with patch("ai.threat_intel.lookup.lookup_hash", return_value=mock_result):
            result = await _execute_python_tool("security.threat_lookup", tool_def, args)

            data = json.loads(result)

            assert "raw_data" not in data
            assert data["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_rag_query_truncates_output(self):
        """Truncates RAG query output to limit."""
        from ai.mcp_bridge.tools import _execute_python_tool

        tool_def = {"source": "python"}
        args = {"query": "test question"}

        mock_result = MagicMock()
        mock_result.answer = "x" * 10000

        with patch("ai.rag.query.rag_query", return_value=mock_result):
            result = await _execute_python_tool("knowledge.rag_query", tool_def, args)

            assert len(result) <= 4096 + len("...[truncated]")

    @pytest.mark.asyncio
    async def test_handles_import_errors(self):
        """Returns error message on module import failure."""
        from ai.mcp_bridge.tools import _execute_python_tool

        tool_def = {"source": "python"}
        args = {"hash": "a" * 64}

        with patch(
            "ai.threat_intel.lookup.lookup_hash",
            side_effect=ImportError("Module not found"),
        ):
            result = await _execute_python_tool("security.threat_lookup", tool_def, args)

            assert "[Module not available" in result


class TestExecuteTool:
    """Test execute_tool dispatcher."""

    @pytest.mark.asyncio
    async def test_rejects_unknown_tools(self):
        """Raises ValueError for tools not in allowlist."""
        from ai.mcp_bridge.tools import execute_tool

        with patch("ai.mcp_bridge.tools._load_allowlist", return_value={}):
            with pytest.raises(ValueError, match="Unknown tool"):
                await execute_tool("nonexistent.tool", {})

    @pytest.mark.asyncio
    async def test_enforces_rate_limiting(self):
        """Checks bridge rate limit before execution."""
        from ai.mcp_bridge.tools import _BRIDGE_RATE_GLOBAL, execute_tool

        allowlist = {
            "test.tool": {
                "command": ["echo", "test"],
            }
        }

        with patch("ai.mcp_bridge.tools._load_allowlist", return_value=allowlist):
            # Clear rate limit state
            from ai.mcp_bridge.tools import _global_call_times, _per_tool_call_times
            _global_call_times.clear()
            _per_tool_call_times.clear()

            # Exhaust global rate limit (use unique tool names to avoid per-tool limit)
            for i in range(_BRIDGE_RATE_GLOBAL):
                allowlist[f"test.tool{i}"] = {"command": ["echo", "test"]}
                await execute_tool(f"test.tool{i}", {})

            # Next call should raise (global limit exhausted)
            allowlist["test.tool_extra"] = {"command": ["echo", "test"]}
            with pytest.raises(ValueError, match="Bridge rate limited"):
                await execute_tool("test.tool_extra", {})

    @pytest.mark.asyncio
    async def test_validates_args_before_execution(self):
        """Validates arguments before running tool."""
        from ai.mcp_bridge.tools import execute_tool

        allowlist = {
            "test.tool": {
                "args": {
                    "required_arg": {"required": True},
                },
                "command": ["echo", "test"],
            }
        }

        from ai.mcp_bridge.tools import _global_call_times, _per_tool_call_times
        _global_call_times.clear()
        _per_tool_call_times.clear()

        with patch("ai.mcp_bridge.tools._load_allowlist", return_value=allowlist):
            with pytest.raises(ValueError, match="required"):
                await execute_tool("test.tool", {})

    @pytest.mark.asyncio
    async def test_handles_service_status_split_scopes(self):
        """Splits service_status into system and user scope calls."""
        from ai.mcp_bridge.tools import execute_tool

        allowlist = {
            "system.service_status": {
                "command": [],  # Not used for this tool
            }
        }

        with patch("ai.mcp_bridge.tools._load_allowlist", return_value=allowlist):
            with patch(
                "ai.mcp_bridge.tools._run_subprocess",
                side_effect=["system output", "user output"],
            ):
                result = await execute_tool("system.service_status", {})

                assert "[system]" in result
                assert "[user]" in result


class TestTokenReport:
    """Test LLM token usage reporting."""

    @pytest.mark.asyncio
    async def test_generates_token_report_from_status(self, tmp_path):
        """Parses llm-status.json and generates usage report."""
        from ai.mcp_bridge.tools import _execute_token_report

        status_file = tmp_path / "llm-status.json"
        status_data = {
            "generated_at": "2026-04-02T12:00:00Z",
            "usage": {
                "fast": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "requests": 10,
                },
                "reason": {
                    "prompt_tokens": 2000,
                    "completion_tokens": 1000,
                    "requests": 5,
                },
            },
            "providers": {
                "groq": {"score": 1.0, "auth_broken": False},
                "mistral": {"score": 0.8, "auth_broken": False},
            },
        }
        status_file.write_text(json.dumps(status_data))

        with patch("ai.mcp_bridge.tools._LLM_STATUS_PATH", status_file):
            result = await _execute_token_report()

            data = json.loads(result)

            assert data["usage"]["total_tokens"] == 4500  # 1000+500+2000+1000
            assert data["usage"]["by_task"]["fast"]["requests"] == 10
            assert "groq" in data["providers"]

    @pytest.mark.asyncio
    async def test_handles_missing_status_file(self):
        """Returns error when status file doesn't exist."""
        from ai.mcp_bridge.tools import _execute_token_report

        with patch("ai.mcp_bridge.tools._LLM_STATUS_PATH", Path("/nonexistent/file.json")):
            result = await _execute_token_report()

            data = json.loads(result)

            assert "error" in data

    @pytest.mark.asyncio
    async def test_includes_freshness_warning(self, tmp_path):
        """Adds freshness warning when status is stale."""
        from datetime import UTC, datetime, timedelta

        from ai.mcp_bridge.tools import _execute_token_report

        status_file = tmp_path / "llm-status.json"

        # Status from 2 hours ago
        old_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        status_data = {
            "generated_at": old_time,
            "usage": {},
        }
        status_file.write_text(json.dumps(status_data))

        with patch("ai.mcp_bridge.tools._LLM_STATUS_PATH", status_file):
            result = await _execute_token_report()

            data = json.loads(result)

            assert "freshness_warning" in data
