"""Unit tests for ai/mcp_bridge/server.py — FastMCP server core."""


import pytest


# Test skeleton: MCP bridge server
class TestMCPBridgeServer:
    """Test MCP bridge server initialization and health checks."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Health check returns ok when all systems operational."""
        from ai.mcp_bridge.server import health_check

        result = await health_check()
        assert result["status"] == "ok"
        assert "tools" in result

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_router_unhealthy(self):
        """Health check returns degraded status when router has issues."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_create_app_loads_allowlist(self):
        """Server initialization loads and validates allowlist."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_create_app_fails_on_missing_allowlist(self):
        """Server fails fast if allowlist.yaml is missing."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_concurrent_health_checks_dont_race(self):
        """Multiple concurrent health checks don't corrupt state."""
        # TODO: Implement - test with asyncio.gather()
        pass


class TestMCPServerErrorHandling:
    """Test error handling in MCP server."""

    @pytest.mark.asyncio
    async def test_server_handles_tool_execution_timeout(self):
        """Tool execution timeout is caught and returned as error."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_server_handles_malformed_request(self):
        """Malformed JSON request returns 400 error."""
        # TODO: Implement
        pass

    @pytest.mark.asyncio
    async def test_server_handles_router_initialization_failure(self):
        """Server degrades gracefully if router init fails."""
        # TODO: Implement
        pass
