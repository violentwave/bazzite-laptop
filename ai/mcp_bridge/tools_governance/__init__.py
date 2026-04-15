"""MCP tool handlers for governance operations.

P101: MCP Tool Governance + Analytics Platform

Provides MCP tools for querying and managing tool governance.
"""

from datetime import datetime, timedelta
from typing import Any

from ai.mcp_bridge.governance import (
    ToolGovernanceEngine,
    ToolLifecycleManager,
    ToolMonitor,
    ToolUsageAnalytics,
)
from ai.mcp_bridge.governance.models import (
    GovernancePolicy,
    LifecycleState,
)
from ai.mcp_bridge.governance.models import (
    MigrationPath as MigrationPath,  # noqa: F401
)

# Initialize shared instances
_analytics = ToolUsageAnalytics()
_governance = ToolGovernanceEngine()
_lifecycle = ToolLifecycleManager()
_monitor = ToolMonitor()


async def tool_analytics_summary(
    hours: int = 24,
) -> dict[str, Any]:
    """Get usage summary for time range.

    Args:
        hours: Number of hours to include (default: 24)

    Returns:
        Usage summary with total invocations, errors, and top tools
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    summary = await _analytics.get_usage_summary(start_time, end_time)

    return {
        "start_time": summary.start_time.isoformat(),
        "end_time": summary.end_time.isoformat(),
        "total_invocations": summary.total_invocations,
        "total_errors": summary.total_errors,
        "overall_error_rate": f"{summary.overall_error_rate:.2%}",
        "avg_latency_ms": round(summary.avg_latency_ms, 2),
        "top_tools": [
            {
                "rank": t.rank,
                "tool_name": t.tool_name,
                "category": t.category,
                "invocations": int(t.metric_value),
            }
            for t in summary.top_tools[:10]
        ],
        "categories": summary.categories,
    }


async def tool_analytics_ranking(
    metric: str = "invocations",
    limit: int = 20,
) -> dict[str, Any]:
    """Get tool rankings by various metrics.

    Args:
        metric: Metric to rank by (invocations, errors, latency, cost)
        limit: Maximum number of results

    Returns:
        Ranked list of tools
    """
    rankings = await _analytics.get_tool_rankings(metric, limit)

    return {
        "metric": metric,
        "total_ranked": len(rankings),
        "rankings": [
            {
                "rank": r.rank,
                "tool_name": r.tool_name,
                "category": r.category,
                "value": round(r.metric_value, 4),
            }
            for r in rankings
        ],
    }


async def tool_analytics_trends(
    tool_name: str | None = None,
    periods: int = 7,
) -> dict[str, Any]:
    """Get usage trend analysis.

    Args:
        tool_name: Optional specific tool to analyze
        periods: Number of time periods to analyze

    Returns:
        Trend analysis data
    """
    trends = await _analytics.get_usage_trends(tool_name, periods)

    return {
        "tool_name": trends.get("tool_name", tool_name or "all_tools"),
        "trend": trends["trend"],
        "growth_rate": f"{trends.get('growth_rate', 0):.2%}",
        "recent_invocations": trends.get("recent_invocations", 0),
        "previous_invocations": trends.get("previous_invocations", 0),
    }


async def tool_governance_audit(
    tool_name: str,
) -> dict[str, Any]:
    """Run permission/security audit on a tool.

    Args:
        tool_name: Name of the tool to audit

    Returns:
        Audit results with findings and recommendations
    """
    audit = await _governance.audit_tool_permissions(tool_name)

    return {
        "tool_name": audit.tool_name,
        "audit_timestamp": audit.audit_timestamp.isoformat(),
        "requires_elevated": audit.requires_elevated,
        "accesses_sensitive_data": audit.accesses_sensitive_data,
        "data_exposure_risk": audit.data_exposure_risk,
        "compliant": audit.compliant,
        "recommendations": audit.recommendations,
    }


async def tool_governance_score(
    tool_name: str,
) -> dict[str, Any]:
    """Get security score for a tool.

    Args:
        tool_name: Name of the tool to evaluate

    Returns:
        Security score with factor breakdown
    """
    score = await _governance.evaluate_security_score(tool_name)

    return {
        "tool_name": score.tool_name,
        "score": score.score,
        "category": score.category,
        "factors": score.factors,
        "recommendations": score.recommendations,
        "evaluated_at": score.evaluated_at.isoformat(),
    }


async def tool_governance_policies(
    action: str = "list",
    policy_id: str | None = None,
    policy_data: dict | None = None,
) -> dict[str, Any]:
    """List or manage governance policies.

    Args:
        action: Action to perform (list, add, remove)
        policy_id: Policy ID for remove action
        policy_data: Policy data for add action

    Returns:
        Policy information
    """
    if action == "list":
        policies = await _governance.list_policies()
        return {
            "count": len(policies),
            "policies": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "applies_to": p.applies_to,
                    "enabled": p.enabled,
                    "rules": p.rules,
                }
                for p in policies
            ],
        }

    elif action == "add" and policy_data:
        policy = GovernancePolicy(**policy_data)
        await _governance.add_policy(policy)
        return {
            "success": True,
            "message": f"Policy {policy.id} added",
        }

    elif action == "remove" and policy_id:
        removed = await _governance.remove_policy(policy_id)
        return {
            "success": removed,
            "message": f"Policy {policy_id} {'removed' if removed else 'not found'}",
        }

    return {
        "success": False,
        "message": "Invalid action or missing parameters",
    }


async def tool_lifecycle_status(
    tool_name: str,
) -> dict[str, Any]:
    """Get lifecycle state of a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Lifecycle state information
    """
    state = await _lifecycle.get_lifecycle_state(tool_name)

    if not state:
        return {
            "found": False,
            "tool_name": tool_name,
            "message": "Tool not found in lifecycle registry",
        }

    return {
        "found": True,
        "tool_name": state.tool_name,
        "current_state": state.current_state.value,
        "version": state.version,
        "introduced_at": state.introduced_at.isoformat(),
        "deprecated_at": state.deprecated_at.isoformat() if state.deprecated_at else None,
        "sunset_date": state.sunset_date.isoformat() if state.sunset_date else None,
        "retired_at": state.retired_at.isoformat() if state.retired_at else None,
        "replacement_tool": state.replacement_tool,
        "migration_guide": state.migration_guide,
    }


async def tool_lifecycle_deprecate(
    tool_name: str,
    replacement_tool: str | None = None,
    sunset_days: int = 30,
    reason: str = "",
) -> dict[str, Any]:
    """Deprecate a tool.

    Args:
        tool_name: Name of the tool to deprecate
        replacement_tool: Optional replacement tool name
        sunset_days: Days until retirement
        reason: Deprecation reason

    Returns:
        Deprecation result
    """
    try:
        state = await _lifecycle.deprecate_tool(
            tool_name=tool_name,
            replacement_tool=replacement_tool,
            migration_guide=reason,
            sunset_days=sunset_days,
        )

        return {
            "success": True,
            "tool_name": tool_name,
            "new_state": state.current_state.value,
            "sunset_date": state.sunset_date.isoformat() if state.sunset_date else None,
            "replacement_tool": replacement_tool,
        }
    except ValueError as e:
        return {
            "success": False,
            "tool_name": tool_name,
            "error": str(e),
        }


async def tool_lifecycle_list(
    state_filter: str | None = None,
) -> dict[str, Any]:
    """List tools by lifecycle state.

    Args:
        state_filter: Optional state filter (active, deprecated, legacy, retired)

    Returns:
        List of tools matching the filter
    """
    state = None
    if state_filter:
        try:
            state = LifecycleState(state_filter)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid state filter: {state_filter}",
            }

    tools = await _lifecycle.list_tools_by_state(state)
    stats = await _lifecycle.get_statistics()

    return {
        "success": True,
        "statistics": stats,
        "tools": [
            {
                "tool_name": t.tool_name,
                "state": t.current_state.value,
                "version": t.version,
            }
            for t in tools
        ],
    }


async def tool_monitoring_health(
    tool_name: str,
) -> dict[str, Any]:
    """Get health status of a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Health status information
    """
    status = await _monitor.health_check(tool_name)

    return {
        "tool_name": status.tool_name,
        "healthy": status.healthy,
        "last_check": status.last_check.isoformat(),
        "error_rate_24h": f"{status.error_rate_24h:.2%}",
        "avg_latency_24h": round(status.avg_latency_24h, 2),
        "availability_24h": f"{status.availability_24h:.1f}%",
        "issues": status.issues,
    }


async def tool_monitoring_alerts(
    min_severity: str = "medium",
) -> dict[str, Any]:
    """Get active monitoring alerts.

    Args:
        min_severity: Minimum severity (low, medium, high, critical)

    Returns:
        List of active alerts
    """
    anomalies = await _monitor.get_active_anomalies(min_severity=min_severity)

    return {
        "count": len(anomalies),
        "min_severity": min_severity,
        "alerts": [
            {
                "tool_name": a.tool_name,
                "type": a.anomaly_type,
                "severity": a.severity,
                "detected_at": a.detected_at.isoformat(),
                "description": a.description,
            }
            for a in anomalies
        ],
    }


async def tool_monitoring_report() -> dict[str, Any]:
    """Generate comprehensive monitoring report.

    Returns:
        Health report with all tools
    """
    report = await _monitor.generate_health_report()

    return {
        "generated_at": report.generated_at.isoformat(),
        "summary": {
            "healthy_tools": report.healthy_tools,
            "degraded_tools": report.degraded_tools,
            "unhealthy_tools": report.unhealthy_tools,
        },
        "circuit_breakers_tripped": report.circuit_breakers_tripped,
        "recent_anomalies_count": len(report.recent_anomalies),
        "top_issues": report.top_issues,
    }


# Export tool handlers
TOOL_HANDLERS = {
    "tool.analytics.summary": tool_analytics_summary,
    "tool.analytics.ranking": tool_analytics_ranking,
    "tool.analytics.trends": tool_analytics_trends,
    "tool.governance.audit": tool_governance_audit,
    "tool.governance.score": tool_governance_score,
    "tool.governance.policies": tool_governance_policies,
    "tool.lifecycle.status": tool_lifecycle_status,
    "tool.lifecycle.deprecate": tool_lifecycle_deprecate,
    "tool.lifecycle.list": tool_lifecycle_list,
    "tool.monitoring.health": tool_monitoring_health,
    "tool.monitoring.alerts": tool_monitoring_alerts,
    "tool.monitoring.report": tool_monitoring_report,
}
