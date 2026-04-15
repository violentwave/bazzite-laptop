"""Usage forecasting for P104.

Provides time-series forecasting for tool usage, costs, and performance.
Uses simple statistical methods for prediction.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta

from ai.mcp_bridge.analytics_advanced.models import (
    ForecastMetric,
    ForecastReport,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.analytics_advanced.forecast")


class UsageForecaster:
    """Forecasts tool usage and cost patterns.

    Uses simple statistical methods (linear regression, moving averages)
    to forecast future usage and costs.
    """

    def __init__(self, analytics: ToolUsageAnalytics):
        """Initialize the forecaster.

        Args:
            analytics: Tool usage analytics instance for data access
        """
        self._analytics = analytics

    async def forecast_usage(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ForecastReport:
        """Generate usage forecast report.

        Args:
            start_time: Start of historical period
            end_time: End of historical period

        Returns:
            Forecast report with predictions
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        tool_forecasts = []
        peak_tools = []
        total_invocations = 0
        total_cost = 0.0

        for metric in summary.top_tools[:20]:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if len(tool_metrics) < 2:
                continue

            invocations = [m.invocations for m in tool_metrics]
            costs = [m.cost_usd for m in tool_metrics]

            total_invocations += sum(invocations)
            total_cost += sum(costs)

            inv_forecast_7d = self._forecast_linear(invocations, 7)
            inv_forecast_30d = self._forecast_linear(invocations, 30)

            confidence = min(0.9, len(tool_metrics) / 10)

            tool_forecasts.append(
                ForecastMetric(
                    tool_name=tool_name,
                    metric_name="invocations",
                    current_value=sum(invocations),
                    forecast_1d=inv_forecast_7d / 7,
                    forecast_7d=inv_forecast_7d,
                    forecast_30d=inv_forecast_30d,
                    confidence=confidence,
                    trend=self._detect_trend(invocations),
                )
            )

            if inv_forecast_7d > sum(invocations) * 1.5:
                peak_tools.append(tool_name)

        growth_rate = self._calculate_growth_rate(
            [m.current_value for m in tool_forecasts],
            [m.forecast_7d for m in tool_forecasts],
        )

        return ForecastReport(
            period_start=start_time,
            period_end=end_time,
            total_invocations_current=total_invocations,
            total_invocations_forecast_7d=int(sum(m.forecast_7d for m in tool_forecasts)),
            total_invocations_forecast_30d=int(sum(m.forecast_30d for m in tool_forecasts)),
            total_cost_current=total_cost,
            total_cost_forecast_7d=sum(
                m.forecast_7d * (total_cost / max(total_invocations, 1)) for m in tool_forecasts
            ),
            total_cost_forecast_30d=sum(
                m.forecast_30d * (total_cost / max(total_invocations, 1)) for m in tool_forecasts
            ),
            tool_forecasts=tool_forecasts,
            peak_usage_tools=peak_tools,
            growth_rate=growth_rate,
            recommendations=self._generate_forecast_recommendations(tool_forecasts),
        )

    def _forecast_linear(
        self,
        values: list[float],
        periods: int,
    ) -> float:
        """Simple linear regression forecast.

        Args:
            values: Historical values
            periods: Number of periods to forecast

        Returns:
            Forecasted value
        """
        if len(values) < 2:
            return values[-1] if values else 0.0

        n = len(values)
        x = list(range(n))
        y = values

        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)

        try:
            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                return y_mean

            slope = numerator / denominator
            intercept = y_mean - slope * x_mean

            forecast = intercept + slope * (n + periods - 1)
            return max(0, forecast)
        except (ValueError, ZeroDivisionError):
            return statistics.mean(values)

    def _detect_trend(self, values: list[float]) -> str:
        """Detect trend direction.

        Args:
            values: Time series values

        Returns:
            Trend direction: increasing, decreasing, or stable
        """
        if len(values) < 3:
            return "stable"

        first_half = statistics.mean(values[: len(values) // 2])
        second_half = statistics.mean(values[len(values) // 2 :])

        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        return "stable"

    def _calculate_growth_rate(
        self,
        current: list[float],
        forecast: list[float],
    ) -> float:
        """Calculate growth rate percentage.

        Args:
            current: Current period values
            forecast: Forecasted values

        Returns:
            Growth rate as decimal
        """
        total_current = sum(current)
        total_forecast = sum(forecast)

        if total_current == 0:
            return 0.0

        return (total_forecast - total_current) / total_current

    def _generate_forecast_recommendations(
        self,
        forecasts: list[ForecastMetric],
    ) -> list[str]:
        """Generate recommendations based on forecasts."""
        recommendations = []

        increasing_tools = [f for f in forecasts if f.trend == "increasing"]
        if len(increasing_tools) > 5:
            recommendations.append(
                f"{len(increasing_tools)} tools showing increasing usage - review capacity planning"
            )

        high_confidence = [f for f in forecasts if f.confidence > 0.7]
        if high_confidence:
            recommendations.append(
                f"High forecast confidence for {len(high_confidence)} tools - reliable for planning"
            )

        return recommendations
