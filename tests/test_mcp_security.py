"""Security tests for the MCP bridge.

Validates input sanitization, key scoping, unknown tool rejection,
concurrency limits, and bridge-level rate limiting.
"""

import asyncio
import re
from unittest.mock import patch

import pytest


class TestInputValidation:
    """Argument validation before tool execution."""

    def test_sha256_regex_accepts_valid(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hash": {"type": "string", "pattern": "^[a-fA-F0-9]{32,64}$", "required": True}}
        }
        _validate_args(tool_def, {"hash": "a" * 64})  # Should not raise

    def test_sha256_regex_accepts_32_chars(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hash": {"type": "string", "pattern": "^[a-fA-F0-9]{32,64}$", "required": True}}
        }
        _validate_args(tool_def, {"hash": "A" * 32})  # MD5-length also valid

    def test_sha256_regex_rejects_short(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hash": {"type": "string", "pattern": "^[a-fA-F0-9]{32,64}$", "required": True}}
        }
        with pytest.raises(ValueError, match="does not match"):
            _validate_args(tool_def, {"hash": "abc"})

    def test_sha256_regex_rejects_injection(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hash": {"type": "string", "pattern": "^[a-fA-F0-9]{32,64}$", "required": True}}
        }
        with pytest.raises(ValueError, match="does not match"):
            _validate_args(tool_def, {"hash": "'; DROP TABLE hashes; --"})

    def test_sha256_regex_rejects_non_hex(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hash": {"type": "string", "pattern": "^[a-fA-F0-9]{32,64}$", "required": True}}
        }
        with pytest.raises(ValueError, match="does not match"):
            _validate_args(tool_def, {"hash": "z" * 64})

    def test_rag_length_accepts_valid(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"question": {"type": "string", "max_length": 500, "required": True}}
        }
        _validate_args(tool_def, {"question": "What is a CVE?"})

    def test_rag_length_accepts_exactly_500(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"question": {"type": "string", "max_length": 500, "required": True}}
        }
        _validate_args(tool_def, {"question": "x" * 500})  # Boundary: should not raise

    def test_rag_length_rejects_too_long(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"question": {"type": "string", "max_length": 500, "required": True}}
        }
        with pytest.raises(ValueError, match="exceeds max length"):
            _validate_args(tool_def, {"question": "x" * 501})

    def test_required_arg_missing(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hash": {"type": "string", "pattern": "^[a-fA-F0-9]{32,64}$", "required": True}}
        }
        with pytest.raises(ValueError, match="required"):
            _validate_args(tool_def, {})

    def test_no_args_definition_passes(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {}  # No args key
        _validate_args(tool_def, {"ignored": "value"})  # Should not raise

    def test_optional_arg_absent_passes(self):
        from ai.mcp_bridge.tools import _validate_args

        tool_def = {
            "args": {"hint": {"type": "string", "max_length": 100, "required": False}}
        }
        _validate_args(tool_def, {})  # Missing optional arg: should not raise


class TestKeyScoping:
    """LLM keys must NEVER be loaded in the bridge process."""

    def test_bridge_never_loads_llm_keys(self):
        """The MCP bridge must only load threat_intel scoped keys."""
        from ai.config import KEY_SCOPES

        llm_keys = KEY_SCOPES["llm"]
        threat_keys = KEY_SCOPES["threat_intel"]
        assert llm_keys.isdisjoint(threat_keys), (
            "LLM and threat_intel key sets must not overlap — "
            f"shared keys: {llm_keys & threat_keys}"
        )

    def test_key_scopes_llm_contains_expected_providers(self):
        """LLM scope must cover all cloud LLM providers used by ai/router.py."""
        from ai.config import KEY_SCOPES

        expected = {"GROQ_API_KEY", "ZAI_API_KEY", "GEMINI_API_KEY"}
        assert expected.issubset(KEY_SCOPES["llm"]), (
            f"LLM scope missing expected keys: {expected - KEY_SCOPES['llm']}"
        )

    def test_key_scopes_threat_intel_contains_expected_providers(self):
        """Threat intel scope must cover VT, OTX, AbuseIPDB."""
        from ai.config import KEY_SCOPES

        expected = {"VT_API_KEY", "OTX_API_KEY", "ABUSEIPDB_KEY"}
        assert expected.issubset(KEY_SCOPES["threat_intel"]), (
            f"threat_intel scope missing expected keys: {expected - KEY_SCOPES['threat_intel']}"
        )

    def test_bridge_startup_uses_scoped_load(self):
        """server.py must call load_keys(scope='threat_intel'), not load_keys()."""
        from pathlib import Path

        server_path = Path(__file__).parent.parent / "ai" / "mcp_bridge" / "server.py"
        if not server_path.exists():
            pytest.skip("server.py not yet created (Task 7)")
        source = server_path.read_text()
        assert 'load_keys(scope="threat_intel")' in source or "load_keys(scope='threat_intel')" in source, (
            "server.py must use scoped key loading: load_keys(scope='threat_intel')"
        )


class TestUnknownToolRejection:
    """Unknown or path-traversal tool names must be rejected before any I/O."""

    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self):
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            await execute_tool("admin.delete_everything", {})

    @pytest.mark.asyncio
    async def test_dotdot_in_tool_name_rejected(self):
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            await execute_tool("../etc/passwd", {})

    @pytest.mark.asyncio
    async def test_empty_tool_name_rejected(self):
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            await execute_tool("", {})

    @pytest.mark.asyncio
    async def test_null_byte_tool_name_rejected(self):
        from ai.mcp_bridge.tools import execute_tool

        with pytest.raises(ValueError, match="Unknown tool"):
            await execute_tool("system.disk_usage\x00", {})


class TestConcurrencySemaphore:
    """Subprocess concurrency must be capped at 4."""

    def test_semaphore_value_is_4(self):
        from ai.mcp_bridge.tools import _subprocess_semaphore

        assert _subprocess_semaphore._value == 4

    @pytest.mark.asyncio
    async def test_fifth_call_blocks(self):
        """5th concurrent subprocess call should block until one completes."""
        from ai.mcp_bridge.tools import _subprocess_semaphore

        # Acquire 4 slots
        for _ in range(4):
            await _subprocess_semaphore.acquire()

        # 5th acquire should not complete immediately
        acquired = asyncio.Event()

        async def try_acquire():
            await _subprocess_semaphore.acquire()
            acquired.set()

        task = asyncio.create_task(try_acquire())
        await asyncio.sleep(0.1)
        assert not acquired.is_set(), "5th concurrent call should block"

        # Release one slot — 5th call should now proceed
        _subprocess_semaphore.release()
        await asyncio.sleep(0.1)
        assert acquired.is_set(), "Should unblock after release"

        # Clean up: release the 4 remaining acquired slots + the one from try_acquire
        for _ in range(4):
            _subprocess_semaphore.release()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestBridgeRateLimiting:
    """Bridge-level rate limit constants must be defined and correct."""

    def test_rate_limiter_config_exists(self):
        from ai.mcp_bridge.tools import _BRIDGE_RATE_GLOBAL, _BRIDGE_RATE_PER_TOOL

        assert _BRIDGE_RATE_GLOBAL == 10, f"Expected global rate 10, got {_BRIDGE_RATE_GLOBAL}"
        assert _BRIDGE_RATE_PER_TOOL == 2, f"Expected per-tool rate 2, got {_BRIDGE_RATE_PER_TOOL}"

    def test_rate_limit_tracking_structures_exist(self):
        """Call-time tracking lists must be importable module-level names."""
        from ai.mcp_bridge.tools import _global_call_times, _per_tool_call_times

        assert isinstance(_global_call_times, list)
        assert isinstance(_per_tool_call_times, dict)

    def test_check_bridge_rate_raises_on_global_overflow(self):
        """_check_bridge_rate should raise when global limit is exceeded."""
        import time
        from ai.mcp_bridge import tools

        now = time.time()
        original = list(tools._global_call_times)
        try:
            # Fill the global window with exactly _BRIDGE_RATE_GLOBAL entries
            tools._global_call_times[:] = [now] * tools._BRIDGE_RATE_GLOBAL
            with pytest.raises(ValueError, match="rate limited"):
                tools._check_bridge_rate("system.disk_usage")
        finally:
            tools._global_call_times[:] = original

    def test_check_bridge_rate_raises_on_per_tool_overflow(self):
        """_check_bridge_rate should raise when per-tool limit is exceeded."""
        import time
        from ai.mcp_bridge import tools

        tool_name = "security.threat_lookup"
        now = time.time()
        original = tools._per_tool_call_times.get(tool_name, [])
        try:
            tools._per_tool_call_times[tool_name] = [now] * tools._BRIDGE_RATE_PER_TOOL
            # Also make sure global bucket is not full
            tools._global_call_times.clear()
            with pytest.raises(ValueError, match="rate limited"):
                tools._check_bridge_rate(tool_name)
        finally:
            tools._per_tool_call_times[tool_name] = original
