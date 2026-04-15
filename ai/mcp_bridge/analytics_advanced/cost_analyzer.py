"""Cost analysis for P104.

Provides detailed cost analysis, breakdown, and trends for tool usage.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any

from ai.mcp_bridge.analytics_advanced.models import (
    CostMetric,
    CostReport,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.analytics_advanced.cost")


class CostAnalyzer:
    """Analyzes tool usage costs.

    Provides detailed cost breakdown by tool, category,
    and time period with trend analysis.
    """

    def __init__(self, analytics: ToolUsageAnalytics):
        """Initialize the cost analyzer.

        Args:
            analytics: Tool usage analytics instance for data access
        """
        self._analytics = analytics

    async def generate_cost_report(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> CostReport:
        """Generate comprehensive cost report.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            Cost report with detailed breakdowns
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        tool_costs: list[CostMetric] = []
        cost_by_category: dict[str, float] = {}
        total_cost = 0.0
        top_cost_tools: list[str] = []

        cost_data: dict[str, dict[str, Any]] = {}

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if not tool_metrics:
                continue

            total_tool_cost = sum(m.cost_usd for m in tool_metrics)
            invocations = sum(m.invocations for m in tool_metrics)

            if total_tool_cost > 0:
                cost_per_inv = total_tool_cost / invocations if invocations > 0 else 0
            else:
                cost_per_inv = 0.0

            total_cost += total_tool_cost
            category = metric.category

            if category not in cost_by_category:
                cost_by_category[category] = 0.0
            cost_by_category[category] += total_tool_cost

            costs = [m.cost_usd for m in tool_metrics]
            trend = self._detect_cost_trend(costs)

            cost_data[tool_name] = {
                "tool_name": tool_name,
                "category": category,
                "total_cost_usd": total_tool_cost,
                "cost_per_invocation": cost_per_inv,
                "invocations": invocations,
                "costs": costs,
                "trend": trend,
            }

        for tool_name, data in cost_data.items():
            percent = (data["total_cost_usd"] / total_cost * 100) if total_cost > 0 else 0

            daily_cost = data["total_cost_usd"] / 7
            monthly_cost = daily_cost * 30
            yearly_cost = daily_cost * 365

            tool_costs.append(
                CostMetric(
                    tool_name=tool_name,
                    total_cost_usd=data["total_cost_usd"],
                    cost_per_invocation=data["cost_per_invocation"],
                    cost_per_1k_tokens=0.01,
                    daily_cost=daily_cost,
                    monthly_cost=monthly_cost,
                    yearly_cost=yearly_cost,
                    trend=data["trend"],
                    percent_of_total=percent,
                )
            )

        tool_costs.sort(key=lambda x: x.total_cost_usd, reverse=True)
        top_cost_tools = [c.tool_name for c in tool_costs[:10]]

        return CostReport(
            period_start=start_time,
            period_end=end_time,
            total_cost_usd=total_cost,
            tool_costs=tool_costs,
            top_cost_tools=top_cost_tools,
            cost_by_category=cost_by_category,
            trend_summary=self._detect_cost_trend([c.total_cost_usd for c in tool_costs]),
            recommendations=self._generate_cost_recommendations(tool_costs, cost_by_category),
        )

    def _detect_cost_trend(self, costs: list[float]) -> str:
        """Detect cost trend direction.

        Args:
            costs: List of cost values over time

        Returns:
            Trend: increasing, decreasing, or stable
        """
        if len(costs) < 3:
            return "stable"

        first_half = statistics.mean(costs[: len(costs) // 2])
        second_half = statistics.mean(costs[len(costs) // 2 :])

        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        return "stable"

    def _generate_cost_recommendations(
        self,
        tool_costs: list[CostMetric],
        cost_by_category: dict[str, float],
    ) -> list[str]:
        """Generate cost optimization recommendations."""
        recommendations = []

        if tool_costs and tool_costs[0].percent_of_total > 30:
            rec = (
                f"Tool '{tool_costs[0].tool_name}' accounts for "
                f"{tool_costs[0].percent_of_total:.1f}% of costs"
            )
            recommendations.append(rec)

        increasing_costs = [c for c in tool_costs if c.trend == "increasing"]
        if len(increasing_costs) > 3:
            rec = f"{len(increasing_costs)} tools showing increasing costs"
            recommendations.append(rec)

        high_monthly = [c for c in tool_costs if c.monthly_cost > 10]
        if high_monthly:
            recommendations.append(
                f"{len(high_monthly)} tools exceed $10/month - consider optimization or caching"
            )

        return recommendations
