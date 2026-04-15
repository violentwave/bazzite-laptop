"""Advanced anomaly detection for P104.

Provides enhanced anomaly detection with multiple detection methods,
severity scoring, and actionable recommendations.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any

from ai.mcp_bridge.analytics_advanced.models import (
    AnomalyReport,
    OptimizationCategory,
    OptimizationRecommendation,
    RecommendationPriority,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.analytics_advanced.anomaly")


class AnomalyDetector:
    """Advanced anomaly detection with multiple detection methods.

    Extends P101's basic anomaly detection with:
    - Multi-metric detection (latency, error, cost, usage)
    - Severity scoring and prioritization
    - Anomaly clustering and correlation
    - Actionable recommendations
    """

    def __init__(self, analytics: ToolUsageAnalytics):
        """Initialize the anomaly detector.

        Args:
            analytics: Tool usage analytics instance for data access
        """
        self._analytics = analytics
        self._sensitivity_config = {
            "low": {"std_threshold": 3.0, "min_samples": 10},
            "medium": {"std_threshold": 2.0, "min_samples": 5},
            "high": {"std_threshold": 1.5, "min_samples": 3},
        }

    async def detect_all_anomalies(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        sensitivity: str = "medium",
    ) -> AnomalyReport:
        """Detect all anomalies across metrics.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period
            sensitivity: Detection sensitivity (low, medium, high)

        Returns:
            Comprehensive anomaly report
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=24)

        anomalies = (
            await self._detect_latency_anomalies(start_time, end_time, sensitivity)
            + await self._detect_error_anomalies(start_time, end_time, sensitivity)
            + await self._detect_cost_anomalies(start_time, end_time, sensitivity)
            + await self._detect_usage_anomalies(start_time, end_time, sensitivity)
        )

        return self._build_anomaly_report(anomalies, start_time, end_time)

    async def _detect_latency_anomalies(
        self,
        start_time: datetime,
        end_time: datetime,
        sensitivity: str,
    ) -> list[dict[str, Any]]:
        """Detect latency anomalies."""
        anomalies = []
        config = self._sensitivity_config.get(sensitivity, self._sensitivity_config["medium"])

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if len(tool_metrics) < config["min_samples"]:
                continue

            latencies = [m.avg_latency_ms for m in tool_metrics if m.invocations > 0]
            if len(latencies) < 3:
                continue

            mean = statistics.mean(latencies)
            std = statistics.stdev(latencies) if len(latencies) > 1 else 0

            if std > 0:
                recent = latencies[-3:]
                recent_mean = statistics.mean(recent)
                if recent_mean > mean + config["std_threshold"] * std:
                    severity = self._calculate_severity(recent_mean / mean)
                    anomalies.append(
                        {
                            "tool_name": tool_name,
                            "anomaly_type": "latency_spike",
                            "severity": severity,
                            "detected_at": datetime.utcnow(),
                            "description": (
                                f"Latency spike: {recent_mean:.1f}ms vs baseline {mean:.1f}ms"
                            ),
                            "expected_value": mean,
                            "actual_value": recent_mean,
                            "metric": "avg_latency_ms",
                        }
                    )

        return anomalies

    async def _detect_error_anomalies(
        self,
        start_time: datetime,
        end_time: datetime,
        sensitivity: str,
    ) -> list[dict[str, Any]]:
        """Detect error rate anomalies."""
        anomalies = []
        config = self._sensitivity_config.get(sensitivity, self._sensitivity_config["medium"])

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if len(tool_metrics) < config["min_samples"]:
                continue

            error_rates = [m.error_rate for m in tool_metrics]
            if len(error_rates) < 3:
                continue

            mean = statistics.mean(error_rates[:-3]) if len(error_rates) > 3 else 0
            std = statistics.stdev(error_rates[:-3]) if len(error_rates) > 4 else 0
            recent = error_rates[-3:]
            recent_mean = statistics.mean(recent)

            if std > 0 and recent_mean > mean + config["std_threshold"] * std:
                severity = (
                    "critical" if recent_mean > 0.5 else "high" if recent_mean > 0.2 else "medium"
                )
                anomalies.append(
                    {
                        "tool_name": tool_name,
                        "anomaly_type": "error_rate_spike",
                        "severity": severity,
                        "detected_at": datetime.utcnow(),
                        "description": (
                            f"Error rate spike: {recent_mean:.2%} vs baseline {mean:.2%}"
                        ),
                        "expected_value": mean,
                        "actual_value": recent_mean,
                        "metric": "error_rate",
                    }
                )

        return anomalies

    async def _detect_cost_anomalies(
        self,
        start_time: datetime,
        end_time: datetime,
        sensitivity: str,
    ) -> list[dict[str, Any]]:
        """Detect cost anomalies."""
        anomalies = []
        config = self._sensitivity_config.get(sensitivity, self._sensitivity_config["medium"])

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if len(tool_metrics) < config["min_samples"]:
                continue

            costs = [m.cost_usd for m in tool_metrics]
            if len(costs) < 3:
                continue

            mean = statistics.mean(costs[:-3]) if len(costs) > 3 else 0
            std = statistics.stdev(costs[:-3]) if len(costs) > 4 else 0
            recent = costs[-3:]
            recent_mean = statistics.mean(recent)

            if mean > 0 and std > 0 and recent_mean > mean + config["std_threshold"] * std:
                severity = "high" if recent_mean > mean * 2 else "medium"
                anomalies.append(
                    {
                        "tool_name": tool_name,
                        "anomaly_type": "cost_spike",
                        "severity": severity,
                        "detected_at": datetime.utcnow(),
                        "description": f"Cost spike: ${recent_mean:.4f} vs baseline ${mean:.4f}",
                        "expected_value": mean,
                        "actual_value": recent_mean,
                        "metric": "cost_usd",
                    }
                )

        return anomalies

    async def _detect_usage_anomalies(
        self,
        start_time: datetime,
        end_time: datetime,
        sensitivity: str,
    ) -> list[dict[str, Any]]:
        """Detect usage pattern anomalies (sudden drops/increases)."""
        anomalies = []
        config = self._sensitivity_config.get(sensitivity, self._sensitivity_config["medium"])

        summary = await self._analytics.get_usage_summary(start_time, end_time)

        for metric in summary.top_tools:
            tool_name = metric.tool_name
            tool_metrics = await self._analytics.get_tool_metrics(tool_name, start_time, end_time)

            if len(tool_metrics) < config["min_samples"]:
                continue

            invocations = [m.invocations for m in tool_metrics]
            if len(invocations) < 3:
                continue

            mean = statistics.mean(invocations[:-3]) if len(invocations) > 3 else 0
            std = statistics.stdev(invocations[:-3]) if len(invocations) > 4 else 0
            recent = invocations[-3:]
            recent_mean = statistics.mean(recent)

            if std > 0:
                if recent_mean < mean - config["std_threshold"] * std:
                    anomalies.append(
                        {
                            "tool_name": tool_name,
                            "anomaly_type": "usage_drop",
                            "severity": "medium",
                            "detected_at": datetime.utcnow(),
                            "description": (
                                f"Usage dropped: {recent_mean:.0f} vs baseline {mean:.0f}"
                            ),
                            "expected_value": mean,
                            "actual_value": recent_mean,
                            "metric": "invocations",
                        }
                    )
                elif recent_mean > mean + config["std_threshold"] * std:
                    anomalies.append(
                        {
                            "tool_name": tool_name,
                            "anomaly_type": "usage_spike",
                            "severity": "medium",
                            "detected_at": datetime.utcnow(),
                            "description": (
                                f"Usage spike: {recent_mean:.0f} vs baseline {mean:.0f} invocations"
                            ),
                            "expected_value": mean,
                            "actual_value": recent_mean,
                            "metric": "invocations",
                        }
                    )

        return anomalies

    def _calculate_severity(self, ratio: float) -> str:
        """Calculate severity based on metric ratio."""
        if ratio > 5:
            return "critical"
        elif ratio > 3:
            return "high"
        elif ratio > 1.5:
            return "medium"
        return "low"

    def _build_anomaly_report(
        self,
        anomalies: list[dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
    ) -> AnomalyReport:
        """Build comprehensive anomaly report."""
        critical = [a for a in anomalies if a.get("severity") == "critical"]
        high = [a for a in anomalies if a.get("severity") == "high"]
        medium = [a for a in anomalies if a.get("severity") == "medium"]
        low = [a for a in anomalies if a.get("severity") == "low"]

        affected = list(set(a.get("tool_name") for a in anomalies))

        recommendations = self._generate_anomaly_recommendations(anomalies)

        return AnomalyReport(
            period_start=start_time,
            period_end=end_time,
            anomalies_detected=len(anomalies),
            critical_anomalies=critical,
            high_anomalies=high,
            medium_anomalies=medium,
            low_anomalies=low,
            affected_tools=affected,
            recommendations=recommendations,
        )

    def _generate_anomaly_recommendations(
        self,
        anomalies: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on detected anomalies."""
        recommendations = []

        if any(a.get("anomaly_type") == "latency_spike" for a in anomalies):
            recommendations.append("Investigate latency spikes - check for resource contention")

        if any(a.get("anomaly_type") == "error_rate_spike" for a in anomalies):
            recommendations.append(
                "Review error logs for error rate spikes - may indicate service degradation"
            )

        if any(a.get("anomaly_type") == "cost_spike" for a in anomalies):
            recommendations.append(
                "Analyze cost drivers - consider implementing cost caps or optimization"
            )

        if any(a.get("anomaly_type") == "usage_drop" for a in anomalies):
            recommendations.append(
                "Investigate usage drops - may indicate integration issues or feature problems"
            )

        return recommendations

    async def generate_recommendations(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[OptimizationRecommendation]:
        """Generate optimization recommendations based on anomalies.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period

        Returns:
            List of actionable optimization recommendations
        """
        report = await self.detect_all_anomalies(start_time, end_time)
        recommendations = []

        for anomaly in report.critical_anomalies + report.high_anomalies:
            tool_name = anomaly.get("tool_name")
            anomaly_type = anomaly.get("anomaly_type")

            rec = OptimizationRecommendation(
                category=OptimizationCategory.RELIABILITY,
                priority=RecommendationPriority.HIGH
                if anomaly.get("severity") == "critical"
                else RecommendationPriority.MEDIUM,
                title=f"Fix {anomaly_type.replace('_', ' ').title()} for {tool_name}",
                description=anomaly.get("description", ""),
                tool_name=tool_name,
                estimated_impact="high",
                affected_tools=[tool_name] if tool_name else [],
            )
            recommendations.append(rec)

        return recommendations
