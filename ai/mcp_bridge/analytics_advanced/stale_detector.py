"""Stale tool detection for P104.

Identifies tools that are unused, deprecated, replaced, or underutilized.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from ai.mcp_bridge.analytics_advanced.models import (
    StaleTool,
    StaleToolStatus,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.analytics_advanced.stale")


class StaleDetector:
    """Detects stale, unused, and underutilized tools.

    Identifies tools that:
    - Haven't been used in a specified period
    - Are marked as deprecated
    - Have been replaced by newer tools
    - Are significantly underutilized compared to peers
    """

    def __init__(
        self,
        analytics: ToolUsageAnalytics,
        unused_days_threshold: int = 30,
        underutilization_threshold: float = 0.1,
    ):
        """Initialize the stale detector.

        Args:
            analytics: Tool usage analytics instance
            unused_days_threshold: Days without usage to consider unused
            underutilization_threshold: Usage ratio threshold (0.1 = 10% of average)
        """
        self._analytics = analytics
        self._unused_days_threshold = unused_days_threshold
        self._underutilization_threshold = underutilization_threshold

    async def detect_stale_tools(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[StaleTool]:
        """Detect all stale tools.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            List of identified stale tools
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=self._unused_days_threshold)

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        stale_tools: list[StaleTool] = []
        all_tools_in_period = set(m.tool_name for m in summary.top_tools)

        avg_invocations = self._calculate_average_invocations(summary.top_tools)
        min_invocations = avg_invocations * self._underutilization_threshold

        for tool_name in all_tools_in_period:
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if not tool_metrics:
                stale_tools.append(
                    StaleTool(
                        tool_name=tool_name,
                        category=summary.categories.get(tool_name, "unknown"),
                        status=StaleToolStatus.UNUSED,
                        last_used=None,
                        invocation_count=0,
                        days_since_last_use=self._unused_days_threshold,
                        recommendation="Consider removing or archiving this tool",
                        estimated_cost_savings=0.0,
                    )
                )
                continue

            invocations = sum(m.invocations for m in tool_metrics)
            last_used = max(m.timestamp for m in tool_metrics)
            days_since_last_use = (end_time - last_used).days

            if days_since_last_use >= self._unused_days_threshold:
                stale_tools.append(
                    StaleTool(
                        tool_name=tool_name,
                        category=summary.categories.get(tool_name, "unknown"),
                        status=StaleToolStatus.UNUSED,
                        last_used=last_used,
                        invocation_count=invocations,
                        days_since_last_use=days_since_last_use,
                        recommendation="Tool has not been used recently - review for removal",
                        estimated_cost_savings=0.0,
                    )
                )
            elif invocations < min_invocations and avg_invocations > 10:
                avg_cost = sum(m.cost_usd for m in tool_metrics) / max(invocations, 1)
                estimated_savings = avg_cost * invocations * 12

                stale_tools.append(
                    StaleTool(
                        tool_name=tool_name,
                        category=summary.categories.get(tool_name, "unknown"),
                        status=StaleToolStatus.UNDERUTILIZED,
                        last_used=last_used,
                        invocation_count=invocations,
                        days_since_last_use=days_since_last_use,
                        recommendation=(
                            "Tool is significantly underutilized - consider optimization or removal"
                        ),
                        estimated_cost_savings=estimated_savings,
                    )
                )

        return stale_tools

    def _calculate_average_invocations(self, top_tools: list[Any]) -> float:
        """Calculate average invocations across tools."""
        if not top_tools:
            return 0.0

        invocations = [t.metric_value for t in top_tools]
        return sum(invocations) / len(invocations) if invocations else 0.0

    async def get_stale_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get summary of stale tools analysis.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            Summary dictionary with counts and recommendations
        """
        stale_tools = await self.detect_stale_tools(start_time, end_time)

        unused_count = sum(1 for t in stale_tools if t.status == StaleToolStatus.UNUSED)
        deprecated_count = sum(1 for t in stale_tools if t.status == StaleToolStatus.DEPRECATED)
        replaced_count = sum(1 for t in stale_tools if t.status == StaleToolStatus.REPLACED)
        underutilized_count = sum(
            1 for t in stale_tools if t.status == StaleToolStatus.UNDERUTILIZED
        )

        total_savings = sum(t.estimated_cost_savings for t in stale_tools)

        recommendations = []
        if unused_count > 5:
            recommendations.append(f"{unused_count} unused tools found - review for cleanup")
        if underutilized_count > 3:
            recommendations.append(
                f"{underutilized_count} underutilized tools - consider optimization or removal"
            )
        if total_savings > 0:
            recommendations.append(f"Potential yearly savings: ${total_savings:.2f}")

        return {
            "total_stale_tools": len(stale_tools),
            "unused": unused_count,
            "deprecated": deprecated_count,
            "replaced": replaced_count,
            "underutilized": underutilized_count,
            "potential_savings": total_savings,
            "recommendations": recommendations,
        }
