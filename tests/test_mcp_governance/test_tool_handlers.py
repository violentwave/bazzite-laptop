"""Tests for MCP governance tool handlers.

P101: MCP Tool Governance + Analytics Platform
"""

import pytest

from ai.mcp_bridge.tools_governance import (
    tool_analytics_ranking,
    tool_analytics_summary,
    tool_analytics_trends,
    tool_governance_audit,
    tool_governance_policies,
    tool_governance_score,
    tool_lifecycle_deprecate,
    tool_lifecycle_list,
    tool_lifecycle_status,
    tool_monitoring_alerts,
    tool_monitoring_health,
    tool_monitoring_report,
)


class TestToolAnalyticsHandlers:
    """Test analytics tool handlers."""

    @pytest.mark.asyncio
    async def test_tool_analytics_summary(self):
        """Test usage summary handler."""
        result = await tool_analytics_summary(hours=24)

        assert "start_time" in result
        assert "end_time" in result
        assert "total_invocations" in result
        assert "top_tools" in result
        assert isinstance(result["top_tools"], list)

    @pytest.mark.asyncio
    async def test_tool_analytics_ranking(self):
        """Test ranking handler."""
        result = await tool_analytics_ranking(metric="invocations", limit=10)

        assert result["metric"] == "invocations"
        assert "rankings" in result
        assert isinstance(result["rankings"], list)

    @pytest.mark.asyncio
    async def test_tool_analytics_ranking_errors(self):
        """Test ranking by errors."""
        result = await tool_analytics_ranking(metric="errors", limit=5)

        assert result["metric"] == "errors"
        assert "rankings" in result

    @pytest.mark.asyncio
    async def test_tool_analytics_trends(self):
        """Test trends handler."""
        result = await tool_analytics_trends(tool_name="system.disk_usage")

        assert "tool_name" in result
        assert "trend" in result
        assert "growth_rate" in result

    @pytest.mark.asyncio
    async def test_tool_analytics_trends_all_tools(self):
        """Test trends for all tools."""
        result = await tool_analytics_trends()

        assert result["tool_name"] == "all_tools"
        assert "trend" in result


class TestToolGovernanceHandlers:
    """Test governance tool handlers."""

    @pytest.mark.asyncio
    async def test_tool_governance_audit(self):
        """Test audit handler."""
        result = await tool_governance_audit(tool_name="security.run_scan")

        assert result["tool_name"] == "security.run_scan"
        assert "audit_timestamp" in result
        assert "requires_elevated" in result
        assert "data_exposure_risk" in result
        assert "compliant" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_tool_governance_audit_standard_tool(self):
        """Test audit for standard tool."""
        result = await tool_governance_audit(tool_name="system.disk_usage")

        assert result["tool_name"] == "system.disk_usage"
        assert result["requires_elevated"] is False

    @pytest.mark.asyncio
    async def test_tool_governance_score(self):
        """Test security score handler."""
        result = await tool_governance_score(tool_name="system.disk_usage")

        assert result["tool_name"] == "system.disk_usage"
        assert "score" in result
        assert "category" in result
        assert "factors" in result
        assert "recommendations" in result
        assert result["score"] >= 0 and result["score"] <= 100

    @pytest.mark.asyncio
    async def test_tool_governance_score_high_risk(self):
        """Test security score for high-risk tool."""
        result = await tool_governance_score(tool_name="shell.execute_command")

        assert result["tool_name"] == "shell.execute_command"
        assert result["score"] < 80  # Should be lower due to risk

    @pytest.mark.asyncio
    async def test_tool_governance_policies_list(self):
        """Test policies list handler."""
        result = await tool_governance_policies(action="list")

        assert result["count"] > 0
        assert "policies" in result
        assert isinstance(result["policies"], list)

    @pytest.mark.asyncio
    async def test_tool_governance_policies_invalid_action(self):
        """Test policies with invalid action."""
        result = await tool_governance_policies(action="invalid")

        assert result["success"] is False


class TestToolLifecycleHandlers:
    """Test lifecycle tool handlers."""

    @pytest.mark.asyncio
    async def test_tool_lifecycle_status_existing(self):
        """Test status handler for existing tool."""
        result = await tool_lifecycle_status(tool_name="system.disk_usage")

        assert result["found"] is True
        assert result["tool_name"] == "system.disk_usage"
        assert "current_state" in result
        assert "version" in result
        assert "introduced_at" in result

    @pytest.mark.asyncio
    async def test_tool_lifecycle_status_nonexistent(self):
        """Test status handler for non-existent tool."""
        result = await tool_lifecycle_status(tool_name="nonexistent.tool.xyz")

        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_tool_lifecycle_list_all(self):
        """Test list handler without filter."""
        result = await tool_lifecycle_list()

        assert result["success"] is True
        assert "statistics" in result
        assert "tools" in result
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0

    @pytest.mark.asyncio
    async def test_tool_lifecycle_list_filtered(self):
        """Test list handler with state filter."""
        result = await tool_lifecycle_list(state_filter="active")

        assert result["success"] is True
        assert "tools" in result

    @pytest.mark.asyncio
    async def test_tool_lifecycle_list_invalid_filter(self):
        """Test list handler with invalid filter."""
        result = await tool_lifecycle_list(state_filter="invalid")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_tool_lifecycle_deprecate(self):
        """Test deprecate handler."""
        # First reactivate in case it's already deprecated
        from ai.mcp_bridge.tools_governance import _lifecycle

        await _lifecycle.reactivate_tool("system.disk_usage")

        result = await tool_lifecycle_deprecate(
            tool_name="system.disk_usage",
            replacement_tool="system.new_disk",
            sunset_days=30,
            reason="Testing deprecation",
        )

        assert result["success"] is True
        assert result["tool_name"] == "system.disk_usage"
        assert result["new_state"] == "deprecated"
        assert result["replacement_tool"] == "system.new_disk"

    @pytest.mark.asyncio
    async def test_tool_lifecycle_deprecate_nonexistent(self):
        """Test deprecate handler for non-existent tool."""
        result = await tool_lifecycle_deprecate(
            tool_name="nonexistent.tool.xyz",
            sunset_days=30,
        )

        assert result["success"] is False
        assert "error" in result


class TestToolMonitoringHandlers:
    """Test monitoring tool handlers."""

    @pytest.mark.asyncio
    async def test_tool_monitoring_health(self):
        """Test health handler."""
        result = await tool_monitoring_health(tool_name="system.disk_usage")

        assert result["tool_name"] == "system.disk_usage"
        assert "healthy" in result
        assert "last_check" in result
        assert "error_rate_24h" in result
        assert "availability_24h" in result
        assert "issues" in result

    @pytest.mark.asyncio
    async def test_tool_monitoring_alerts(self):
        """Test alerts handler."""
        result = await tool_monitoring_alerts(min_severity="low")

        assert "count" in result
        assert "min_severity" in result
        assert "alerts" in result
        assert isinstance(result["alerts"], list)

    @pytest.mark.asyncio
    async def test_tool_monitoring_alerts_high_severity(self):
        """Test alerts handler with high severity filter."""
        result = await tool_monitoring_alerts(min_severity="high")

        assert result["min_severity"] == "high"

    @pytest.mark.asyncio
    async def test_tool_monitoring_report(self):
        """Test report handler."""
        result = await tool_monitoring_report()

        assert "generated_at" in result
        assert "summary" in result
        assert "healthy_tools" in result["summary"]
        assert "degraded_tools" in result["summary"]
        assert "unhealthy_tools" in result["summary"]
        assert "circuit_breakers_tripped" in result
        assert "recent_anomalies_count" in result


class TestToolHandlerExports:
    """Test that all handlers are exported correctly."""

    def test_tool_handlers_exported(self):
        """Test TOOL_HANDLERS contains all expected tools."""
        from ai.mcp_bridge.tools_governance import TOOL_HANDLERS

        expected_tools = [
            "tool.analytics.summary",
            "tool.analytics.ranking",
            "tool.analytics.trends",
            "tool.governance.audit",
            "tool.governance.score",
            "tool.governance.policies",
            "tool.lifecycle.status",
            "tool.lifecycle.deprecate",
            "tool.lifecycle.list",
            "tool.monitoring.health",
            "tool.monitoring.alerts",
            "tool.monitoring.report",
        ]

        for tool_name in expected_tools:
            assert tool_name in TOOL_HANDLERS
            assert callable(TOOL_HANDLERS[tool_name])

    def test_tool_handlers_count(self):
        """Test correct number of tool handlers."""
        from ai.mcp_bridge.tools_governance import TOOL_HANDLERS

        assert len(TOOL_HANDLERS) == 12
