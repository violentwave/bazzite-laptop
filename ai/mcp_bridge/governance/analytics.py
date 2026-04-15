"""Tool usage analytics service.

P101: MCP Tool Governance + Analytics Platform

Tracks and analyzes MCP tool usage patterns for optimization and governance.
"""

import asyncio
import statistics
from datetime import datetime, timedelta
from typing import Any

from ai.mcp_bridge.governance.models import (
    Anomaly,
    InvocationContext,
    ToolRanking,
    ToolUsageMetric,
    UsageSummary,
)


class ToolUsageAnalytics:
    """Tracks and analyzes MCP tool usage patterns.

    Provides real-time metrics collection, usage aggregation,
    anomaly detection, and trend analysis for all MCP tools.
    """

    def __init__(self, storage_backend: Any | None = None):
        """Initialize analytics service.

        Args:
            storage_backend: Optional storage backend for persistence.
                            If None, uses in-memory storage.
        """
        self._storage = storage_backend
        self._invocation_buffer: list[dict] = []
        self._buffer_lock = asyncio.Lock()
        self._metrics_cache: dict[str, list[ToolUsageMetric]] = {}
        self._cache_lock = asyncio.Lock()

    async def record_invocation(
        self,
        tool_name: str,
        category: str,
        duration_ms: float,
        error: Exception | None = None,
        context: InvocationContext | None = None,
        token_usage: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Record a tool invocation with timing and outcome.

        Args:
            tool_name: Name of the tool invoked
            category: Tool category (e.g., "security", "system")
            duration_ms: Invocation duration in milliseconds
            error: Optional exception if invocation failed
            context: Optional invocation context
            token_usage: Number of tokens consumed
            cost_usd: Cost in USD for this invocation
        """
        invocation = {
            "tool_name": tool_name,
            "category": category,
            "duration_ms": duration_ms,
            "error": error is not None,
            "error_type": type(error).__name__ if error else None,
            "timestamp": datetime.utcnow(),
            "session_id": context.session_id if context else None,
            "token_usage": token_usage,
            "cost_usd": cost_usd,
        }

        async with self._buffer_lock:
            self._invocation_buffer.append(invocation)

        # Flush buffer if it gets large
        if len(self._invocation_buffer) >= 100:
            await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush invocation buffer to storage."""
        async with self._buffer_lock:
            buffer = self._invocation_buffer.copy()
            self._invocation_buffer = []

        if not buffer:
            return

        # Aggregate invocations into metrics
        aggregated = self._aggregate_invocations(buffer)

        # Store in cache
        async with self._cache_lock:
            for metric in aggregated:
                if metric.tool_name not in self._metrics_cache:
                    self._metrics_cache[metric.tool_name] = []
                self._metrics_cache[metric.tool_name].append(metric)

        # Persist to storage if available
        if self._storage:
            await self._persist_metrics(aggregated)

    def _aggregate_invocations(self, invocations: list[dict]) -> list[ToolUsageMetric]:
        """Aggregate raw invocations into metrics by tool.

        Args:
            invocations: List of raw invocation records

        Returns:
            List of aggregated ToolUsageMetric objects
        """
        from collections import defaultdict

        grouped = defaultdict(list)
        for inv in invocations:
            key = (inv["tool_name"], inv["category"])
            grouped[key].append(inv)

        metrics = []
        for (tool_name, category), group in grouped.items():
            durations = [inv["duration_ms"] for inv in group]
            errors = sum(1 for inv in group if inv["error"])
            tokens = sum(inv["token_usage"] for inv in group)
            cost = sum(inv["cost_usd"] for inv in group)
            unique_sessions = len(set(inv["session_id"] for inv in group if inv["session_id"]))

            metric = ToolUsageMetric(
                timestamp=datetime.utcnow(),
                tool_name=tool_name,
                category=category,
                invocations=len(group),
                avg_latency_ms=statistics.mean(durations) if durations else 0.0,
                p95_latency_ms=self._calculate_p95(durations) if durations else 0.0,
                error_count=errors,
                error_rate=errors / len(group) if group else 0.0,
                unique_callers=unique_sessions,
                token_usage=tokens,
                cost_usd=cost,
            )
            metrics.append(metric)

        return metrics

    def _calculate_p95(self, values: list[float]) -> float:
        """Calculate P95 percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * 0.95)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    async def _persist_metrics(self, metrics: list[ToolUsageMetric]) -> None:
        """Persist metrics to storage backend."""
        # Placeholder for storage backend integration
        pass

    async def get_usage_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> UsageSummary:
        """Get aggregated usage statistics for a time range.

        Args:
            start_time: Start of time range (defaults to 24h ago)
            end_time: End of time range (defaults to now)

        Returns:
            UsageSummary with aggregated statistics
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=24)

        # Flush any pending data
        await self._flush_buffer()

        # Get metrics from cache
        all_metrics = []
        async with self._cache_lock:
            for tool_metrics in self._metrics_cache.values():
                for metric in tool_metrics:
                    if start_time <= metric.timestamp <= end_time:
                        all_metrics.append(metric)

        if not all_metrics:
            return UsageSummary(
                start_time=start_time,
                end_time=end_time,
                total_invocations=0,
                total_errors=0,
                overall_error_rate=0.0,
                avg_latency_ms=0.0,
                top_tools=[],
                categories={},
            )

        # Calculate aggregates
        total_invocations = sum(m.invocations for m in all_metrics)
        total_errors = sum(m.error_count for m in all_metrics)
        latencies = [m.avg_latency_ms for m in all_metrics if m.invocations > 0]

        # Calculate top tools by invocations
        tool_totals = {}
        for m in all_metrics:
            if m.tool_name not in tool_totals:
                tool_totals[m.tool_name] = {"invocations": 0, "category": m.category}
            tool_totals[m.tool_name]["invocations"] += m.invocations

        top_tools = [
            ToolRanking(
                tool_name=name,
                category=data["category"],
                rank=idx + 1,
                metric_value=data["invocations"],
                metric_name="invocations",
            )
            for idx, (name, data) in enumerate(
                sorted(tool_totals.items(), key=lambda x: x[1]["invocations"], reverse=True)[:10]
            )
        ]

        # Calculate categories
        categories = {}
        for m in all_metrics:
            categories[m.category] = categories.get(m.category, 0) + m.invocations

        return UsageSummary(
            start_time=start_time,
            end_time=end_time,
            total_invocations=total_invocations,
            total_errors=total_errors,
            overall_error_rate=total_errors / total_invocations if total_invocations > 0 else 0.0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            top_tools=top_tools,
            categories=categories,
        )

    async def get_tool_rankings(
        self,
        metric: str = "invocations",
        limit: int = 20,
    ) -> list[ToolRanking]:
        """Rank tools by various metrics.

        Args:
            metric: Metric to rank by (invocations, errors, latency, cost)
            limit: Maximum number of results

        Returns:
            List of ToolRanking objects
        """
        await self._flush_buffer()

        async with self._cache_lock:
            tool_stats = {}

            for tool_name, metrics in self._metrics_cache.items():
                if not metrics:
                    continue

                latest = metrics[-1]
                value = 0.0

                if metric == "invocations":
                    value = sum(m.invocations for m in metrics)
                elif metric == "errors":
                    value = sum(m.error_count for m in metrics)
                elif metric == "latency":
                    latencies = [m.avg_latency_ms for m in metrics if m.invocations > 0]
                    value = statistics.mean(latencies) if latencies else 0.0
                elif metric == "cost":
                    value = sum(m.cost_usd for m in metrics)

                tool_stats[tool_name] = {
                    "value": value,
                    "category": latest.category,
                }

        # Sort and create rankings
        sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1]["value"], reverse=True)

        return [
            ToolRanking(
                tool_name=name,
                category=data["category"],
                rank=idx + 1,
                metric_value=data["value"],
                metric_name=metric,
            )
            for idx, (name, data) in enumerate(sorted_tools[:limit])
        ]

    async def detect_anomalies(
        self,
        tool_name: str | None = None,
        sensitivity: str = "medium",
    ) -> list[Anomaly]:
        """Detect unusual usage patterns using statistical analysis.

        Args:
            tool_name: Optional specific tool to analyze
            sensitivity: Detection sensitivity (low, medium, high)

        Returns:
            List of detected anomalies
        """
        await self._flush_buffer()

        thresholds = {
            "low": 3.0,
            "medium": 2.0,
            "high": 1.5,
        }
        threshold = thresholds.get(sensitivity, 2.0)

        anomalies = []

        async with self._cache_lock:
            tools_to_check = [tool_name] if tool_name else list(self._metrics_cache.keys())

            for name in tools_to_check:
                if name not in self._metrics_cache:
                    continue

                metrics = self._metrics_cache[name]
                if len(metrics) < 5:
                    continue

                # Check for error rate anomalies
                recent_errors = [m.error_rate for m in metrics[-5:]]
                historical_errors = [m.error_rate for m in metrics[:-5]]

                if historical_errors and recent_errors:
                    hist_mean = statistics.mean(historical_errors)
                    hist_std = (
                        statistics.stdev(historical_errors) if len(historical_errors) > 1 else 0
                    )
                    recent_mean = statistics.mean(recent_errors)

                    if hist_std > 0 and recent_mean > hist_mean + threshold * hist_std:
                        anomalies.append(
                            Anomaly(
                                tool_name=name,
                                anomaly_type="error_rate_spike",
                                severity="high" if recent_mean > 0.5 else "medium",
                                detected_at=datetime.utcnow(),
                                description=(
                                    f"Error rate spike: {recent_mean:.2%} "
                                    f"vs baseline {hist_mean:.2%}"
                                ),
                                expected_value=hist_mean,
                                actual_value=recent_mean,
                            )
                        )

                # Check for latency anomalies
                recent_latencies = [m.avg_latency_ms for m in metrics[-5:] if m.invocations > 0]
                historical_latencies = [m.avg_latency_ms for m in metrics[:-5] if m.invocations > 0]

                if historical_latencies and recent_latencies:
                    hist_mean = statistics.mean(historical_latencies)
                    hist_std = (
                        statistics.stdev(historical_latencies)
                        if len(historical_latencies) > 1
                        else 0
                    )
                    recent_mean = statistics.mean(recent_latencies)

                    if hist_std > 0 and recent_mean > hist_mean + threshold * hist_std:
                        anomalies.append(
                            Anomaly(
                                tool_name=name,
                                anomaly_type="latency_spike",
                                severity="medium",
                                detected_at=datetime.utcnow(),
                                description=(
                                    f"Latency spike: {recent_mean:.1f}ms "
                                    f"vs baseline {hist_mean:.1f}ms"
                                ),
                                expected_value=hist_mean,
                                actual_value=recent_mean,
                            )
                        )

        return anomalies

    async def get_usage_trends(
        self,
        tool_name: str | None = None,
        periods: int = 7,
    ) -> dict[str, Any]:
        """Get usage trend analysis.

        Args:
            tool_name: Optional specific tool to analyze
            periods: Number of time periods to analyze

        Returns:
            Dictionary with trend data
        """
        await self._flush_buffer()

        # Calculate trend direction and rate
        async with self._cache_lock:
            if tool_name:
                metrics = self._metrics_cache.get(tool_name, [])
                if len(metrics) < 2:
                    return {"trend": "insufficient_data", "growth_rate": 0.0}

                recent = sum(m.invocations for m in metrics[-periods:])
                previous = sum(m.invocations for m in metrics[-periods * 2 : -periods])

                if previous == 0:
                    growth_rate = float("inf") if recent > 0 else 0.0
                else:
                    growth_rate = (recent - previous) / previous

                if growth_rate > 0.2:
                    trend = "increasing"
                elif growth_rate < -0.2:
                    trend = "decreasing"
                else:
                    trend = "stable"

                return {
                    "tool_name": tool_name,
                    "trend": trend,
                    "growth_rate": growth_rate,
                    "recent_invocations": recent,
                    "previous_invocations": previous,
                }
            else:
                # System-wide trends
                all_recent = 0
                all_previous = 0

                for metrics in self._metrics_cache.values():
                    if len(metrics) >= periods * 2:
                        all_recent += sum(m.invocations for m in metrics[-periods:])
                        all_previous += sum(m.invocations for m in metrics[-periods * 2 : -periods])

                if all_previous == 0:
                    growth_rate = float("inf") if all_recent > 0 else 0.0
                else:
                    growth_rate = (all_recent - all_previous) / all_previous

                return {
                    "trend": "increasing"
                    if growth_rate > 0.1
                    else "decreasing"
                    if growth_rate < -0.1
                    else "stable",
                    "growth_rate": growth_rate,
                    "recent_invocations": all_recent,
                    "previous_invocations": all_previous,
                }
