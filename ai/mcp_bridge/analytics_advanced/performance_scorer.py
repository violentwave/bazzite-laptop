"""Performance scoring for P104.

Provides comprehensive performance scoring for tools based on
latency, reliability, cost efficiency, and usage patterns.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any

from ai.mcp_bridge.analytics_advanced.models import (
    LatencyMetric,
    LatencyReport,
    PerformanceRanking,
    ToolPerformanceScore,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.analytics_advanced.performance")


class PerformanceScorer:
    """Scores tool performance across multiple dimensions.

    Provides comprehensive performance analysis including
    latency grades, reliability scores, and cost efficiency.
    """

    def __init__(self, analytics: ToolUsageAnalytics):
        """Initialize the performance scorer.

        Args:
            analytics: Tool usage analytics instance for data access
        """
        self._analytics = analytics

    async def generate_latency_report(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> LatencyReport:
        """Generate comprehensive latency report.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            Latency report with detailed breakdowns
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        tool_latencies: list[LatencyMetric] = []
        slowest_tools: list[str] = []
        fastest_tools: list[str] = []
        all_latencies: list[float] = []

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if not tool_metrics:
                continue

            latencies = [m.avg_latency_ms for m in tool_metrics if m.invocations > 0]
            invocations = sum(m.invocations for m in tool_metrics)

            if not latencies:
                continue

            avg = statistics.mean(latencies)
            all_latencies.extend(latencies)

            sorted_lat = sorted(latencies)
            p50 = sorted_lat[len(sorted_lat) // 2]
            p95_val = sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 1 else avg
            p99_val = sorted_lat[int(len(sorted_lat) * 0.99)] if len(sorted_lat) > 1 else avg
            max_lat = max(latencies)
            min_lat = min(latencies)
            std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0.0

            grade = self._calculate_latency_grade(avg)
            trend = self._detect_latency_trend(latencies)

            tool_latencies.append(
                LatencyMetric(
                    tool_name=tool_name,
                    avg_latency_ms=avg,
                    p50_latency_ms=p50,
                    p95_latency_ms=p95_val,
                    p99_latency_ms=p99_val,
                    max_latency_ms=max_lat,
                    min_latency_ms=min_lat,
                    std_deviation_ms=std_dev,
                    invocations=invocations,
                    trend=trend,
                    grade=grade,
                )
            )

        tool_latencies.sort(key=lambda x: x.avg_latency_ms, reverse=True)
        slowest_tools = [t.tool_name for t in tool_latencies[:5]]
        fastest_tools = [t.tool_name for t in tool_latencies[-5:]]

        grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for t in tool_latencies:
            if t.grade in grade_distribution:
                grade_distribution[t.grade] += 1

        return LatencyReport(
            period_start=start_time,
            period_end=end_time,
            overall_avg_ms=statistics.mean(all_latencies) if all_latencies else 0.0,
            tool_latencies=tool_latencies,
            slowest_tools=slowest_tools,
            fastest_tools=fastest_tools,
            grade_distribution=grade_distribution,
            recommendations=self._generate_latency_recommendations(tool_latencies),
        )

    async def generate_performance_ranking(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> PerformanceRanking:
        """Generate comprehensive performance ranking.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            Performance ranking with scores for all tools
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        scores: list[ToolPerformanceScore] = []

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            category = metric.category
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if not tool_metrics:
                continue

            latency_score = self._calculate_latency_score(tool_metrics)
            reliability_score = self._calculate_reliability_score(tool_metrics)
            cost_efficiency_score = self._calculate_cost_efficiency_score(tool_metrics)
            usage_score = self._calculate_usage_score(tool_metrics, summary)

            overall = (
                latency_score * 0.3
                + reliability_score * 0.3
                + cost_efficiency_score * 0.2
                + usage_score * 0.2
            )

            grade = self._calculate_overall_grade(overall)
            percentile = self._calculate_percentile_rank(
                overall, [s.overall_score for s in scores] + [overall]
            )

            issues = self._identify_performance_issues(
                tool_metrics, latency_score, reliability_score
            )

            scores.append(
                ToolPerformanceScore(
                    tool_name=tool_name,
                    category=category,
                    overall_score=overall,
                    latency_score=latency_score,
                    reliability_score=reliability_score,
                    cost_efficiency_score=cost_efficiency_score,
                    usage_score=usage_score,
                    grade=grade,
                    percentile_rank=percentile,
                    issues=issues,
                    recommendations=self._generate_performance_recommendations(tool_name, issues),
                )
            )

        scores.sort(key=lambda x: x.overall_score, reverse=True)

        return PerformanceRanking(
            period_start=start_time,
            period_end=end_time,
            rankings=scores,
            total_tools=len(scores),
            average_score=statistics.mean([s.overall_score for s in scores]) if scores else 0.0,
        )

    def _calculate_latency_grade(self, avg_latency: float) -> str:
        """Calculate latency grade based on average latency."""
        if avg_latency < 50:
            return "A"
        elif avg_latency < 150:
            return "B"
        elif avg_latency < 300:
            return "C"
        elif avg_latency < 500:
            return "D"
        return "F"

    def _detect_latency_trend(self, latencies: list[float]) -> str:
        """Detect latency trend."""
        if len(latencies) < 3:
            return "stable"

        first_half = statistics.mean(latencies[: len(latencies) // 2])
        second_half = statistics.mean(latencies[len(latencies) // 2 :])

        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        return "stable"

    def _calculate_latency_score(self, metrics: list[Any]) -> float:
        """Calculate latency score (0-100)."""
        if not metrics:
            return 50.0

        avg_latencies = [m.avg_latency_ms for m in metrics if m.invocations > 0]
        if not avg_latencies:
            return 50.0

        avg = statistics.mean(avg_latencies)

        if avg < 10:
            return 100.0
        elif avg < 50:
            return 90.0
        elif avg < 100:
            return 75.0
        elif avg < 200:
            return 60.0
        elif avg < 500:
            return 40.0
        return 20.0

    def _calculate_reliability_score(self, metrics: list[Any]) -> float:
        """Calculate reliability score based on error rate."""
        if not metrics:
            return 50.0

        error_rates = [m.error_rate for m in metrics]
        if not error_rates:
            return 50.0

        avg_error = statistics.mean(error_rates)

        return max(0, 100 - (avg_error * 200))

    def _calculate_cost_efficiency_score(self, metrics: list[Any]) -> float:
        """Calculate cost efficiency score."""
        if not metrics:
            return 50.0

        costs = [m.cost_usd for m in metrics]
        invocations = [m.invocations for m in metrics]

        if not costs or sum(invocations) == 0:
            return 50.0

        avg_cost_per_inv = sum(costs) / sum(invocations) if sum(invocations) > 0 else 0

        if avg_cost_per_inv < 0.001:
            return 100.0
        elif avg_cost_per_inv < 0.01:
            return 80.0
        elif avg_cost_per_inv < 0.1:
            return 60.0
        elif avg_cost_per_inv < 1.0:
            return 40.0
        return 20.0

    def _calculate_usage_score(self, metrics: list[Any], summary: Any) -> float:
        """Calculate usage score based on invocation count."""
        if not metrics:
            return 50.0

        total_invocations = sum(m.invocations for m in metrics)
        max_invocations = max(m.metric_value for m in summary.top_tools) if summary.top_tools else 1

        return min(100, (total_invocations / max_invocations * 100))

    def _calculate_overall_grade(self, score: float) -> str:
        """Calculate overall letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        return "F"

    def _calculate_percentile_rank(self, score: float, all_scores: list[float]) -> int:
        """Calculate percentile rank."""
        if not all_scores:
            return 0

        sorted_scores = sorted(all_scores, reverse=True)
        position = next(
            (i for i, s in enumerate(sorted_scores, 1) if s <= score), len(sorted_scores)
        )
        return int((position / len(sorted_scores)) * 100)

    def _identify_performance_issues(
        self,
        metrics: list[Any],
        latency_score: float,
        reliability_score: float,
    ) -> list[str]:
        """Identify specific performance issues."""
        issues = []

        if latency_score < 60:
            issues.append("High latency - consider optimization or caching")

        if reliability_score < 70:
            issues.append("Reliability issues - high error rate detected")

        if metrics:
            recent_errors = [m.error_rate for m in metrics[-3:]]
            if recent_errors and statistics.mean(recent_errors) > 0.1:
                issues.append("Recent error rate degradation")

        return issues

    def _generate_latency_recommendations(
        self,
        tool_latencies: list[LatencyMetric],
    ) -> list[str]:
        """Generate latency-specific recommendations."""
        recommendations = []

        slow_count = sum(1 for t in tool_latencies if t.grade in ("D", "F"))
        if slow_count > 3:
            recommendations.append(
                f"{slow_count} tools have poor latency grades - prioritize optimization"
            )

        increasing_count = sum(1 for t in tool_latencies if t.trend == "increasing")
        if increasing_count > 2:
            recommendations.append(
                f"{increasing_count} tools showing increasing latency - investigate root cause"
            )

        return recommendations

    def _generate_performance_recommendations(
        self,
        tool_name: str,
        issues: list[str],
    ) -> list[str]:
        """Generate tool-specific performance recommendations."""
        recommendations = []

        for issue in issues:
            if "latency" in issue.lower():
                recommendations.append(f"{tool_name}: Review query patterns and add caching")
            if "error" in issue.lower():
                recommendations.append(f"{tool_name}: Implement retry logic and error handling")

        return recommendations
