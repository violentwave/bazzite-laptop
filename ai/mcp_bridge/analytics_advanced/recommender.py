"""Optimization recommender for P104.

Generates actionable optimization recommendations by combining
insights from all advanced analytics components.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from ai.mcp_bridge.analytics_advanced.anomaly_detector import AnomalyDetector
from ai.mcp_bridge.analytics_advanced.cost_analyzer import CostAnalyzer
from ai.mcp_bridge.analytics_advanced.models import (
    OptimizationCategory,
    OptimizationRecommendation,
    RecommendationPriority,
)
from ai.mcp_bridge.analytics_advanced.performance_scorer import PerformanceScorer
from ai.mcp_bridge.analytics_advanced.stale_detector import StaleDetector
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics

logger = logging.getLogger("ai.mcp_bridge.analytics_advanced.recommender")


class OptimizationRecommender:
    """Generates actionable optimization recommendations.

    Combines insights from anomaly detection, cost analysis,
    performance scoring, and stale tool detection to provide
    comprehensive optimization recommendations.
    """

    def __init__(self, analytics: ToolUsageAnalytics):
        """Initialize the recommender.

        Args:
            analytics: Tool usage analytics instance
        """
        self._analytics = analytics
        self._anomaly_detector = AnomalyDetector(analytics)
        self._cost_analyzer = CostAnalyzer(analytics)
        self._performance_scorer = PerformanceScorer(analytics)
        self._stale_detector = StaleDetector(analytics)

    async def generate_recommendations(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_recommendations: int = 20,
    ) -> list[OptimizationRecommendation]:
        """Generate comprehensive optimization recommendations.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period
            max_recommendations: Maximum number of recommendations to return

        Returns:
            List of prioritized optimization recommendations
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        recommendations: list[OptimizationRecommendation] = []

        anomaly_recs = await self._anomaly_detector.generate_recommendations(start_time, end_time)
        recommendations.extend(anomaly_recs)

        cost_recs = await self._generate_cost_recommendations(start_time, end_time)
        recommendations.extend(cost_recs)

        performance_recs = await self._generate_performance_recommendations(start_time, end_time)
        recommendations.extend(performance_recs)

        stale_recs = await self._generate_stale_recommendations(start_time, end_time)
        recommendations.extend(stale_recs)

        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations = self._sort_by_priority(recommendations)

        return recommendations[:max_recommendations]

    async def _generate_cost_recommendations(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[OptimizationRecommendation]:
        """Generate cost-based recommendations."""
        recommendations = []

        cost_report = await self._cost_analyzer.generate_cost_report(start_time, end_time)

        for rec in cost_report.recommendations:
            if "accounts for" in rec and "%" in rec:
                tool_name = self._extract_tool_name_from_rec(rec)
                recommendations.append(
                    OptimizationRecommendation(
                        category=OptimizationCategory.COST,
                        priority=RecommendationPriority.HIGH,
                        title=f"Optimize costs for {tool_name}",
                        description=rec,
                        tool_name=tool_name,
                        estimated_impact="medium",
                        affected_tools=[tool_name] if tool_name else [],
                    )
                )
            elif "increasing costs" in rec:
                recommendations.append(
                    OptimizationRecommendation(
                        category=OptimizationCategory.COST,
                        priority=RecommendationPriority.MEDIUM,
                        title="Implement cost monitoring",
                        description=rec,
                        estimated_impact="high",
                    )
                )

        return recommendations

    async def _generate_performance_recommendations(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[OptimizationRecommendation]:
        """Generate performance-based recommendations."""
        recommendations = []

        ranking = await self._performance_scorer.generate_performance_ranking(start_time, end_time)

        for score in ranking.rankings:
            if score.grade in ("D", "F"):
                recommendations.append(
                    OptimizationRecommendation(
                        category=OptimizationCategory.PERFORMANCE,
                        priority=(
                            RecommendationPriority.HIGH
                            if score.grade == "F"
                            else RecommendationPriority.MEDIUM
                        ),
                        title=f"Improve performance for {score.tool_name}",
                        description=(
                            f"Tool has {score.grade} grade with "
                            f"{score.overall_score:.1f} overall score"
                        ),
                        tool_name=score.tool_name,
                        estimated_impact="medium",
                        affected_tools=[score.tool_name],
                    )
                )

            for issue in score.issues:
                recommendations.append(
                    OptimizationRecommendation(
                        category=OptimizationCategory.RELIABILITY,
                        priority=RecommendationPriority.MEDIUM,
                        title=f"Address reliability issue in {score.tool_name}",
                        description=issue,
                        tool_name=score.tool_name,
                        estimated_impact="medium",
                        affected_tools=[score.tool_name],
                    )
                )

        return recommendations

    async def _generate_stale_recommendations(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[OptimizationRecommendation]:
        """Generate stale tool recommendations."""
        recommendations = []

        stale_summary = await self._stale_detector.get_stale_summary(start_time, end_time)

        if stale_summary["unused"] > 0:
            rec = f"Found {stale_summary['unused']} unused tools"
            recommendations.append(
                OptimizationRecommendation(
                    category=OptimizationCategory.GOVERNANCE,
                    priority=RecommendationPriority.MEDIUM,
                    title="Clean up unused tools",
                    description=rec,
                    estimated_impact="low",
                    implementation_effort="medium",
                )
            )

        if stale_summary["underutilized"] > 0:
            rec = f"Found {stale_summary['underutilized']} underutilized tools"
            recommendations.append(
                OptimizationRecommendation(
                    category=OptimizationCategory.COST,
                    priority=RecommendationPriority.MEDIUM,
                    title="Review underutilized tools",
                    description=rec,
                    estimated_impact="medium",
                )
            )

        if stale_summary["potential_savings"] > 0:
            rec = f"Potential yearly savings: ${stale_summary['potential_savings']:.2f}"
            recommendations.append(
                OptimizationRecommendation(
                    category=OptimizationCategory.COST,
                    priority=RecommendationPriority.HIGH,
                    title="Capture potential cost savings",
                    description=rec,
                    estimated_impact="high",
                )
            )

        return recommendations

    def _extract_tool_name_from_rec(self, rec: str) -> str | None:
        """Extract tool name from recommendation string."""
        import re

        match = re.search(r"'(.+?)'", rec)
        return match.group(1) if match else None

    def _deduplicate_recommendations(
        self,
        recommendations: list[OptimizationRecommendation],
    ) -> list[OptimizationRecommendation]:
        """Remove duplicate recommendations."""
        seen: dict[tuple[str, str], int] = {}
        unique: list[OptimizationRecommendation] = []

        for i, rec in enumerate(recommendations):
            key = (rec.title, rec.tool_name or "")
            if key not in seen:
                seen[key] = i
                unique.append(rec)

        return unique

    def _sort_by_priority(
        self,
        recommendations: list[OptimizationRecommendation],
    ) -> list[OptimizationRecommendation]:
        """Sort recommendations by priority."""
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
        }

        return sorted(
            recommendations,
            key=lambda r: (
                priority_order.get(r.priority, 99),
                -len(r.affected_tools),
            ),
        )
