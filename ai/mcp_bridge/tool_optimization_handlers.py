"""MCP tool handlers for P104 optimization tools.

Provides handlers for:
- tool.optimization.recommend
- tool.optimization.stale_tools
- tool.optimization.cost_report
- tool.optimization.latency_report
- tool.optimization.anomalies
- tool.optimization.forecast
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from ai.mcp_bridge.analytics_advanced import (
    AnomalyDetector,
    CostAnalyzer,
    OptimizationRecommender,
    PerformanceScorer,
    StaleDetector,
    UsageForecaster,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.tool_optimization_handlers")

_analytics_instance: ToolUsageAnalytics | None = None


def _get_analytics() -> ToolUsageAnalytics:
    """Get or create analytics instance."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = ToolUsageAnalytics()
    return _analytics_instance


async def handle_tool_optimization_recommend(
    start_time: str | None = None,
    end_time: str | None = None,
    max_recommendations: int = 20,
) -> str:
    """Generate actionable optimization recommendations.

    Args:
        start_time: Start of analysis period (ISO 8601)
        end_time: End of analysis period (ISO 8601)
        max_recommendations: Maximum number of recommendations

    Returns:
        JSON string with optimization recommendations
    """
    try:
        start = None
        end = None

        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        analytics = _get_analytics()
        recommender = OptimizationRecommender(analytics)

        recommendations = await recommender.generate_recommendations(
            start_time=start,
            end_time=end,
            max_recommendations=max_recommendations,
        )

        result = {
            "status": "success",
            "count": len(recommendations),
            "recommendations": [
                {
                    "id": r.id,
                    "category": r.category.value,
                    "priority": r.priority.value,
                    "title": r.title,
                    "description": r.description,
                    "tool_name": r.tool_name,
                    "estimated_impact": r.estimated_impact,
                    "implementation_effort": r.implementation_effort,
                    "affected_tools": r.affected_tools,
                    "created_at": r.created_at.isoformat(),
                }
                for r in recommendations
            ],
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_optimization_stale_tools(

    start_time: str | None = None,
    end_time: str | None = None,
    unused_days: int = 30,
) -> str:
    """Detect stale, unused, and underutilized tools.

    Args:
        start_time: Start of analysis period (ISO 8601)
        end_time: End of analysis period (ISO 8601)
        unused_days: Days without usage to consider unused

    Returns:
        JSON string with stale tool information
    """
    try:
        start = None
        end = None

        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        analytics = _get_analytics()
        detector = StaleDetector(analytics, unused_days_threshold=unused_days)

        stale_tools = await detector.detect_stale_tools(start, end)
        summary = await detector.get_stale_summary(start, end)

        result = {
            "status": "success",
            "summary": summary,
            "stale_tools": [
                {
                    "tool_name": t.tool_name,
                    "category": t.category,
                    "status": t.status.value,
                    "last_used": t.last_used.isoformat() if t.last_used else None,
                    "invocation_count": t.invocation_count,
                    "days_since_last_use": t.days_since_last_use,
                    "recommendation": t.recommendation,
                    "replacement_tool": t.replacement_tool,
                    "estimated_cost_savings": t.estimated_cost_savings,
                }
                for t in stale_tools
            ],
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error detecting stale tools: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_optimization_cost_report(

    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Generate cost analysis report.

    Args:
        start_time: Start of analysis period (ISO 8601)
        end_time: End of analysis period (ISO 8601)

    Returns:
        JSON string with cost report
    """
    try:
        start = None
        end = None

        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        analytics = _get_analytics()
        analyzer = CostAnalyzer(analytics)

        report = await analyzer.generate_cost_report(start, end)

        result = {
            "status": "success",
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "total_cost_usd": report.total_cost_usd,
            "tool_costs": [
                {
                    "tool_name": c.tool_name,
                    "total_cost_usd": c.total_cost_usd,
                    "cost_per_invocation": c.cost_per_invocation,
                    "daily_cost": c.daily_cost,
                    "monthly_cost": c.monthly_cost,
                    "yearly_cost": c.yearly_cost,
                    "trend": c.trend,
                    "percent_of_total": c.percent_of_total,
                }
                for c in report.tool_costs
            ],
            "top_cost_tools": report.top_cost_tools,
            "cost_by_category": report.cost_by_category,
            "trend_summary": report.trend_summary,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error generating cost report: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_optimization_latency_report(

    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Generate latency analysis report.

    Args:
        start_time: Start of analysis period (ISO 8601)
        end_time: End of analysis period (ISO 8601)

    Returns:
        JSON string with latency report
    """
    try:
        start = None
        end = None

        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        analytics = _get_analytics()
        scorer = PerformanceScorer(analytics)

        report = await scorer.generate_latency_report(start, end)

        result = {
            "status": "success",
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "overall_avg_ms": report.overall_avg_ms,
            "slowest_tools": report.slowest_tools,
            "fastest_tools": report.fastest_tools,
            "grade_distribution": report.grade_distribution,
            "tool_latencies": [
                {
                    "tool_name": lat.tool_name,
                    "avg_latency_ms": lat.avg_latency_ms,
                    "p50_latency_ms": lat.p50_latency_ms,
                    "p95_latency_ms": lat.p95_latency_ms,
                    "p99_latency_ms": lat.p99_latency_ms,
                    "max_latency_ms": lat.max_latency_ms,
                    "trend": lat.trend,
                    "grade": lat.grade,
                }
                for lat in report.tool_latencies[:20]
            ],
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error generating latency report: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_optimization_anomalies(

    start_time: str | None = None,
    end_time: str | None = None,
    sensitivity: str = "medium",
) -> str:
    """Detect anomalies in tool usage patterns.

    Args:
        start_time: Start of analysis period (ISO 8601)
        end_time: End of analysis period (ISO 8601)
        sensitivity: Detection sensitivity (low, medium, high)

    Returns:
        JSON string with anomaly report
    """
    try:
        start = None
        end = None

        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        analytics = _get_analytics()
        detector = AnomalyDetector(analytics)

        report = await detector.detect_all_anomalies(start, end, sensitivity)

        result = {
            "status": "success",
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "anomalies_detected": report.anomalies_detected,
            "critical_anomalies": report.critical_anomalies,
            "high_anomalies": report.high_anomalies,
            "medium_anomalies": report.medium_anomalies,
            "low_anomalies": report.low_anomalies,
            "affected_tools": report.affected_tools,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        return json.dumps({"status": "error", "error": str(e)})


async def handle_tool_optimization_forecast(

    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Generate usage forecasting report.

    Args:
        start_time: Start of historical period (ISO 8601)
        end_time: End of historical period (ISO 8601)

    Returns:
        JSON string with forecast report
    """
    try:
        start = None
        end = None

        if start_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        analytics = _get_analytics()
        forecaster = UsageForecaster(analytics)

        report = await forecaster.forecast_usage(start, end)

        result = {
            "status": "success",
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "total_invocations_current": report.total_invocations_current,
            "total_invocations_forecast_7d": report.total_invocations_forecast_7d,
            "total_invocations_forecast_30d": report.total_invocations_forecast_30d,
            "total_cost_current": report.total_cost_current,
            "total_cost_forecast_7d": report.total_cost_forecast_7d,
            "total_cost_forecast_30d": report.total_cost_forecast_30d,
            "peak_usage_tools": report.peak_usage_tools,
            "growth_rate": report.growth_rate,
            "tool_forecasts": [
                {
                    "tool_name": f.tool_name,
                    "current_value": f.current_value,
                    "forecast_7d": f.forecast_7d,
                    "forecast_30d": f.forecast_30d,
                    "confidence": f.confidence,
                    "trend": f.trend,
                }
                for f in report.tool_forecasts[:20]
            ],
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        return json.dumps({"status": "error", "error": str(e)})
