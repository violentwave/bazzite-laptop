"""Tests for MCP tool governance module.

P101: MCP Tool Governance + Analytics Platform
"""

from datetime import datetime

import pytest

from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics
from ai.mcp_bridge.governance.governance_engine import ToolGovernanceEngine
from ai.mcp_bridge.governance.lifecycle import ToolLifecycleManager
from ai.mcp_bridge.governance.models import (
    Anomaly,
    CircuitBreakerState,
    GovernancePolicy,
    LifecycleState,
)
from ai.mcp_bridge.governance.monitoring import ToolMonitor


class TestToolUsageAnalytics:
    """Test usage analytics functionality."""

    @pytest.fixture
    async def analytics(self):
        """Create fresh analytics instance."""
        return ToolUsageAnalytics()

    @pytest.mark.asyncio
    async def test_record_invocation(self):
        """Test recording a single invocation."""
        analytics = ToolUsageAnalytics()

        await analytics.record_invocation(
            tool_name="test.tool",
            category="test",
            duration_ms=100.0,
            error=None,
            token_usage=50,
            cost_usd=0.001,
        )

        # Buffer should have one entry
        assert len(analytics._invocation_buffer) == 1

    @pytest.mark.asyncio
    async def test_record_invocation_with_error(self):
        """Test recording an invocation with error."""
        analytics = ToolUsageAnalytics()

        await analytics.record_invocation(
            tool_name="test.tool",
            category="test",
            duration_ms=100.0,
            error=ValueError("test error"),
        )

        assert len(analytics._invocation_buffer) == 1
        assert analytics._invocation_buffer[0]["error"] is True

    @pytest.mark.asyncio
    async def test_get_usage_summary_empty(self):
        """Test summary with no data."""
        analytics = ToolUsageAnalytics()

        summary = await analytics.get_usage_summary()

        assert summary.total_invocations == 0
        assert summary.total_errors == 0
        assert summary.overall_error_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_tool_rankings_empty(self):
        """Test rankings with no data."""
        analytics = ToolUsageAnalytics()

        rankings = await analytics.get_tool_rankings()

        assert len(rankings) == 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_empty(self):
        """Test anomaly detection with no data."""
        analytics = ToolUsageAnalytics()

        anomalies = await analytics.detect_anomalies()

        assert len(anomalies) == 0

    @pytest.mark.asyncio
    async def test_get_usage_trends_insufficient_data(self):
        """Test trends with insufficient data."""
        analytics = ToolUsageAnalytics()

        trends = await analytics.get_usage_trends(tool_name="test.tool")

        assert trends["trend"] == "insufficient_data"


class TestToolGovernanceEngine:
    """Test governance engine functionality."""

    @pytest.fixture
    def engine(self):
        """Create fresh governance engine."""
        return ToolGovernanceEngine()

    @pytest.mark.asyncio
    async def test_default_policies_loaded(self):
        """Test that default policies are loaded."""
        engine = ToolGovernanceEngine()
        policies = await engine.list_policies()

        assert len(policies) > 0

    @pytest.mark.asyncio
    async def test_audit_elevated_tool(self):
        """Test auditing an elevated tool."""
        engine = ToolGovernanceEngine()

        audit = await engine.audit_tool_permissions("security.run_scan")

        assert audit.tool_name == "security.run_scan"
        assert audit.requires_elevated is True
        assert len(audit.recommendations) > 0

    @pytest.mark.asyncio
    async def test_audit_standard_tool(self):
        """Test auditing a standard tool."""
        engine = ToolGovernanceEngine()

        audit = await engine.audit_tool_permissions("system.disk_usage")

        assert audit.tool_name == "system.disk_usage"
        assert audit.requires_elevated is False

    @pytest.mark.asyncio
    async def test_evaluate_security_score_high_risk(self):
        """Test security score for high-risk tool."""
        engine = ToolGovernanceEngine()

        score = await engine.evaluate_security_score("shell.execute_command")

        assert score.tool_name == "shell.execute_command"
        assert score.score < 80  # Should be lower due to risk factors
        assert len(score.factors) > 0

    @pytest.mark.asyncio
    async def test_evaluate_security_score_low_risk(self):
        """Test security score for low-risk tool."""
        engine = ToolGovernanceEngine()

        score = await engine.evaluate_security_score("system.disk_usage")

        assert score.tool_name == "system.disk_usage"
        assert score.score >= 80  # Should be high

    @pytest.mark.asyncio
    async def test_evaluate_access_policy_allowed(self):
        """Test policy evaluation allowing access."""
        engine = ToolGovernanceEngine()

        result = await engine.evaluate_access_policy(
            "system.disk_usage",
            session_level="standard",
        )

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_add_and_remove_policy(self):
        """Test adding and removing a policy."""
        engine = ToolGovernanceEngine()

        policy = GovernancePolicy(
            id="test-policy",
            name="Test Policy",
            description="A test policy",
            applies_to="test.*",
            rules=[{"type": "rate_limit", "max": 10}],
        )

        await engine.add_policy(policy)
        policies = await engine.list_policies()
        assert any(p.id == "test-policy" for p in policies)

        removed = await engine.remove_policy("test-policy")
        assert removed is True

        policies = await engine.list_policies()
        assert not any(p.id == "test-policy" for p in policies)


class TestToolLifecycleManager:
    """Test lifecycle manager functionality."""

    @pytest.fixture
    def lifecycle(self):
        """Create fresh lifecycle manager."""
        return ToolLifecycleManager()

    @pytest.mark.asyncio
    async def test_builtin_tools_initialized(self):
        """Test that built-in tools are initialized."""
        lifecycle = ToolLifecycleManager()

        stats = await lifecycle.get_statistics()

        assert stats["total"] > 0
        assert stats["active"] > 0

    @pytest.mark.asyncio
    async def test_get_lifecycle_state_existing(self):
        """Test getting state for existing tool."""
        lifecycle = ToolLifecycleManager()

        state = await lifecycle.get_lifecycle_state("system.disk_usage")

        assert state is not None
        assert state.tool_name == "system.disk_usage"
        assert state.current_state == LifecycleState.ACTIVE

    @pytest.mark.asyncio
    async def test_get_lifecycle_state_nonexistent(self):
        """Test getting state for non-existent tool."""
        lifecycle = ToolLifecycleManager()

        state = await lifecycle.get_lifecycle_state("nonexistent.tool")

        assert state is None

    @pytest.mark.asyncio
    async def test_deprecate_tool(self):
        """Test deprecating a tool."""
        lifecycle = ToolLifecycleManager()

        state = await lifecycle.deprecate_tool(
            "system.disk_usage",
            replacement_tool="system.new_disk",
            sunset_days=30,
        )

        assert state.current_state == LifecycleState.DEPRECATED
        assert state.replacement_tool == "system.new_disk"
        assert state.sunset_date is not None

    @pytest.mark.asyncio
    async def test_deprecate_nonexistent_tool(self):
        """Test deprecating a non-existent tool raises error."""
        lifecycle = ToolLifecycleManager()

        with pytest.raises(ValueError, match="not found"):
            await lifecycle.deprecate_tool("nonexistent.tool")

    @pytest.mark.asyncio
    async def test_retire_tool(self):
        """Test retiring a tool."""
        lifecycle = ToolLifecycleManager()

        # First deprecate
        await lifecycle.deprecate_tool("system.disk_usage")

        # Then retire
        state = await lifecycle.retire_tool("system.disk_usage")

        assert state.current_state == LifecycleState.RETIRED
        assert state.retired_at is not None

    @pytest.mark.asyncio
    async def test_list_tools_by_state(self):
        """Test listing tools filtered by state."""
        lifecycle = ToolLifecycleManager()

        tools = await lifecycle.list_tools_by_state(LifecycleState.ACTIVE)

        assert len(tools) > 0
        assert all(t.current_state == LifecycleState.ACTIVE for t in tools)

    @pytest.mark.asyncio
    async def test_check_deprecated_tools(self):
        """Test checking for overdue deprecated tools."""
        lifecycle = ToolLifecycleManager()

        # Deprecate with past sunset date
        await lifecycle.deprecate_tool(
            "system.disk_usage",
            sunset_days=-1,  # Past
        )

        overdue = await lifecycle.check_deprecated_tools()

        assert len(overdue) > 0

    @pytest.mark.asyncio
    async def test_reactivate_tool(self):
        """Test reactivating a deprecated tool."""
        lifecycle = ToolLifecycleManager()

        # Deprecate
        await lifecycle.deprecate_tool("system.disk_usage")

        # Reactivate
        state = await lifecycle.reactivate_tool("system.disk_usage")

        assert state.current_state == LifecycleState.ACTIVE
        assert state.deprecated_at is None
        assert state.sunset_date is None


class TestToolMonitor:
    """Test tool monitor functionality."""

    @pytest.fixture
    def monitor(self):
        """Create fresh monitor instance."""
        return ToolMonitor()

    @pytest.mark.asyncio
    async def test_record_success(self):

        monitor = ToolMonitor()
        """Test recording a successful invocation."""

        monitor = ToolMonitor()

        await monitor.record_invocation_result(
            "test.tool",
            success=True,
            duration_ms=100.0,
        )

        cb = await monitor.check_circuit_breaker("test.tool")
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_trip(self):

        monitor = ToolMonitor()
        """Test circuit breaker trips after failures."""


        # Record many failures
        for _ in range(15):
            await monitor.record_invocation_result(
                "test.tool",
                success=False,
                duration_ms=100.0,
            )

        cb = await monitor.check_circuit_breaker("test.tool")
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.opened_at is not None

    @pytest.mark.asyncio
    async def test_can_execute_closed(self):

        monitor = ToolMonitor()
        """Test execution check when closed."""


        can_execute, reason = await monitor.can_execute("test.tool")

        assert can_execute is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_can_execute_open(self):

        monitor = ToolMonitor()
        """Test execution check when open."""


        # Trip the breaker
        for _ in range(15):
            await monitor.record_invocation_result(
                "test.tool",
                success=False,
                duration_ms=100.0,
            )

        can_execute, reason = await monitor.can_execute("test.tool")

        assert can_execute is False
        assert reason is not None
        assert "OPEN" in reason

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):

        monitor = ToolMonitor()
        """Test health check for healthy tool."""


        # Record some successes
        for _ in range(5):
            await monitor.record_invocation_result(
                "test.tool",
                success=True,
                duration_ms=100.0,
            )

        status = await monitor.health_check("test.tool")

        assert status.tool_name == "test.tool"
        assert status.healthy is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):

        monitor = ToolMonitor()
        """Test health check for unhealthy tool."""


        # Trip circuit breaker
        for _ in range(15):
            await monitor.record_invocation_result(
                "test.tool",
                success=False,
                duration_ms=100.0,
            )

        status = await monitor.health_check("test.tool")

        assert status.healthy is False
        assert len(status.issues) > 0

    @pytest.mark.asyncio
    async def test_add_and_get_anomalies(self):

        monitor = ToolMonitor()
        """Test adding and retrieving anomalies."""


        anomaly = Anomaly(
            tool_name="test.tool",
            anomaly_type="error_spike",
            severity="high",
            detected_at=datetime.utcnow(),
            description="Error rate spike detected",
        )

        await monitor.add_anomaly(anomaly)

        anomalies = await monitor.get_active_anomalies(min_severity="medium")

        assert len(anomalies) == 1
        assert anomalies[0].tool_name == "test.tool"

    @pytest.mark.asyncio
    async def test_generate_health_report(self):

        monitor = ToolMonitor()
        """Test generating health report."""


        report = await monitor.generate_health_report()

        assert report.generated_at is not None
        assert report.healthy_tools >= 0
        assert report.degraded_tools >= 0
        assert report.unhealthy_tools >= 0

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self):

        monitor = ToolMonitor()
        """Test manually resetting circuit breaker."""


        # Trip the breaker
        for _ in range(15):
            await monitor.record_invocation_result(
                "test.tool",
                success=False,
                duration_ms=100.0,
            )

        # Reset
        await monitor.reset_circuit_breaker("test.tool")

        cb = await monitor.check_circuit_breaker("test.tool")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_summary(self):

        monitor = ToolMonitor()
        """Test getting circuit breaker summary."""


        summary = await monitor.get_circuit_breaker_summary()

        assert "closed" in summary
        assert "open" in summary
        assert "half_open" in summary


class TestGovernanceModels:
    """Test governance model validation."""

    def test_lifecycle_state_enum(self):
        """Test lifecycle state enum values."""
        assert LifecycleState.ACTIVE.value == "active"
        assert LifecycleState.DEPRECATED.value == "deprecated"
        assert LifecycleState.LEGACY.value == "legacy"
        assert LifecycleState.RETIRED.value == "retired"

    def test_circuit_breaker_state_enum(self):
        """Test circuit breaker state enum values."""
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_governance_policy_creation(self):
        """Test creating a governance policy."""
        policy = GovernancePolicy(
            id="test-policy",
            name="Test Policy",
            description="A test policy",
            applies_to="test.*",
            rules=[{"type": "rate_limit", "max": 10}],
        )

        assert policy.id == "test-policy"
        assert policy.enabled is True

    def test_anomaly_creation(self):
        """Test creating an anomaly."""
        anomaly = Anomaly(
            tool_name="test.tool",
            anomaly_type="latency_spike",
            severity="high",
            detected_at=datetime.utcnow(),
            description="High latency detected",
            expected_value=100.0,
            actual_value=500.0,
        )

        assert anomaly.tool_name == "test.tool"
        assert anomaly.severity == "high"


class TestIntegration:
    """Integration tests for governance components."""

    @pytest.mark.asyncio
    async def test_analytics_to_monitoring_integration(self):
        """Test analytics data flows to monitoring."""
        analytics = ToolUsageAnalytics()
        monitor = ToolMonitor()


        # Record invocations through analytics
        await analytics.record_invocation(
            tool_name="test.tool",
            category="test",
            duration_ms=100.0,
            error=None,
        )

        # Monitor should be able to track independently
        await monitor.record_invocation_result(
            "test.tool",
            success=True,
            duration_ms=100.0,
        )

        status = await monitor.health_check("test.tool")
        assert status.healthy is True

    @pytest.mark.asyncio
    async def test_governance_policy_enforcement(self):
        """Test end-to-end policy enforcement."""
        engine = ToolGovernanceEngine()


        # Evaluate policy
        result = await engine.evaluate_access_policy(
            "security.run_scan",
            session_level="standard",
        )

        # Policy should require elevated session
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_lifecycle_with_monitoring(self):
        """Test lifecycle changes affect monitoring."""
        lifecycle = ToolLifecycleManager()
        monitor = ToolMonitor()


        # Deprecate a tool
        await lifecycle.deprecate_tool("system.disk_usage")

        state = await lifecycle.get_lifecycle_state("system.disk_usage")
        assert state.current_state == LifecycleState.DEPRECATED

        # Monitor should still track the tool
        await monitor.record_invocation_result(
            "system.disk_usage",
            success=True,
            duration_ms=100.0,
        )

        status = await monitor.health_check("system.disk_usage")
        assert status.tool_name == "system.disk_usage"
