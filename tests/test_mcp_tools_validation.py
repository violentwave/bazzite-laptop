"""Unit tests for ai/mcp_bridge/tools.py — tool validation and execution."""

import pytest


class TestToolArgumentValidation:
    """Test _validate_args function with various argument constraints."""

    def test_required_arg_missing_raises_error(self):
        """Missing required argument raises ValueError."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"query": {"required": True}}}

        with pytest.raises(ValueError, match="required"):
            _validate_args(tool_def, {})

    def test_optional_arg_missing_passes(self):
        """Missing optional argument is allowed."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"limit": {"required": False}}}

        _validate_args(tool_def, {})  # Should not raise

    def test_pattern_validation_enforces_regex(self):
        """Argument pattern constraint enforces regex match."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"cve_id": {"pattern": r"^CVE-\d{4}-\d{4,}$", "required": True}}}

        # Valid CVE
        _validate_args(tool_def, {"cve_id": "CVE-2024-1234"})

        # Invalid CVE
        with pytest.raises(ValueError, match="pattern"):
            _validate_args(tool_def, {"cve_id": "INVALID"})

    def test_max_length_validation(self):
        """Argument max_length constraint is enforced."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"query": {"max_length": 100, "required": True}}}

        # Within limit
        _validate_args(tool_def, {"query": "x" * 50})

        # Exceeds limit
        with pytest.raises(ValueError, match="exceeds max length"):
            _validate_args(tool_def, {"query": "x" * 101})

    def test_non_string_argument_rejected(self):
        """Non-string arguments are rejected."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"count": {"required": True}}}

        with pytest.raises(ValueError, match="must be a string"):
            _validate_args(tool_def, {"count": 42})

    def test_integer_typed_argument_accepts_int(self):
        """Integer-typed args accept int values."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"limit": {"type": "integer", "required": True, "min": 1, "max": 100}}}

        _validate_args(tool_def, {"limit": 50})

    def test_integer_typed_argument_rejects_string(self):
        """Integer-typed args reject string values."""
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {"args": {"limit": {"type": "integer", "required": True}}}

        with pytest.raises(ValueError, match="must be an integer"):
            _validate_args(tool_def, {"limit": "50"})


class TestBridgeRateLimiting:
    """Test bridge-level rate limiting."""

    def test_global_rate_limit_exceeded(self):
        """Exceeding global rate limit raises ValueError."""
        import time

        from ai.mcp_bridge.tools import _check_bridge_rate, _global_call_times, _per_tool_call_times

        # Clear all rate limit state to avoid interference from prior tests
        _global_call_times.clear()
        _per_tool_call_times.clear()

        # Fill the global window directly (avoids per-tool limit triggering first)
        now = time.time()
        for _ in range(10):
            _global_call_times.append(now)

        # Next call should hit global rate limit
        with pytest.raises(ValueError, match="rate limited"):
            _check_bridge_rate("test.tool")

    def test_per_tool_rate_limit_exceeded(self):
        """Exceeding per-tool rate limit raises ValueError."""
        from ai.mcp_bridge.tools import _check_bridge_rate, _global_call_times, _per_tool_call_times

        # Clear all rate limit state to avoid interference from prior tests
        _global_call_times.clear()
        _per_tool_call_times.clear()

        # Fill up the per-tool limit (2 calls/sec)
        _check_bridge_rate("specific.tool")
        _check_bridge_rate("specific.tool")

        # 3rd call to same tool should fail
        with pytest.raises(ValueError, match="rate limited"):
            _check_bridge_rate("specific.tool")

    def test_rate_limit_window_expires(self):
        """Rate limit window slides and allows calls after 1 second."""
        # TODO: Implement with time.sleep(1.1) or time mocking
        pass


class TestPathRedaction:
    """Test _redact_paths function."""

    def test_home_path_redacted(self):
        """User home paths are replaced with [HOME]."""
        from ai.mcp_bridge.tools import _redact_paths

        text = "/home/lch/security/vector-db/data.lance"
        result = _redact_paths(text)
        assert result == "[HOME]/security/vector-db/data.lance"

    def test_multiple_home_paths_redacted(self):
        """Multiple home path occurrences are all redacted."""
        from ai.mcp_bridge.tools import _redact_paths

        text = "Found at /home/lch/file1 and /home/lch/file2"
        result = _redact_paths(text)
        assert result.count("/home/lch") == 0
        assert result.count("[HOME]") == 2

    def test_non_home_paths_preserved(self):
        """Paths outside home directory are preserved."""
        from ai.mcp_bridge.tools import _redact_paths

        text = "/var/log/system.log"
        result = _redact_paths(text)
        assert result == "/var/log/system.log"


class TestFileReading:
    """Test _read_file_tail function."""

    def test_read_file_tail_handles_empty_file(self):
        """Empty files are handled without error."""
        # TODO: Implement with temp file
        pass

    def test_read_file_tail_handles_missing_file(self):
        """Missing files return appropriate error message."""
        # TODO: Implement
        pass

    def test_read_file_tail_follows_symlinks(self):
        """Symlinks are resolved and target file is read."""
        # TODO: Implement with temp symlink
        pass

    def test_read_file_tail_falls_back_to_logrotated(self):
        """When primary file is empty, falls back to rotated files."""
        # TODO: Implement
        pass


class TestToolExecution:
    """Test execute_tool function."""

    @pytest.mark.asyncio
    async def test_execute_tool_checks_allowlist(self):
        """Tool execution validates against allowlist before running."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_execute_tool_enforces_rate_limits(self):
        """Tool execution enforces both global and per-tool rate limits."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_execute_tool_truncates_large_output(self):
        """Tool output exceeding limit is truncated with marker."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_execute_tool_respects_custom_limits(self):
        """Tools with custom output limits use those limits."""
        # TODO: Implement - test system.mcp_manifest (16KB)
        pass

    @pytest.mark.asyncio
    async def test_execute_tool_times_out_long_subprocess(self):
        """Subprocess calls timeout after 30 seconds."""
        # TODO: Implement with long-running mock subprocess
        pass

    @pytest.mark.asyncio
    async def test_execute_tool_respects_semaphore(self):
        """Concurrent subprocess calls respect semaphore (4 max)."""
        # TODO: Implement with asyncio.gather() and 10 concurrent calls
        pass
