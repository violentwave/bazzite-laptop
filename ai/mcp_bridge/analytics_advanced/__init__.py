"""Advanced Analytics Module for P104.

Provides advanced tool analytics including:
- Anomaly detection with multiple detection methods
- Usage forecasting with trend analysis
- Cost analysis and reporting
- Performance scoring and ranking
- Stale tool detection
- Optimization recommendations

Extends P101 governance analytics with actionable optimization insights.
"""

from ai.mcp_bridge.analytics_advanced.anomaly_detector import AnomalyDetector
from ai.mcp_bridge.analytics_advanced.cost_analyzer import CostAnalyzer
from ai.mcp_bridge.analytics_advanced.forecaster import UsageForecaster
from ai.mcp_bridge.analytics_advanced.models import (
    AnomalyReport,
    CostReport,
    ForecastReport,
    LatencyReport,
    OptimizationRecommendation,
    PerformanceRanking,
    StaleTool,
    ToolPerformanceScore,
)
from ai.mcp_bridge.analytics_advanced.performance_scorer import PerformanceScorer
from ai.mcp_bridge.analytics_advanced.recommender import OptimizationRecommender
from ai.mcp_bridge.analytics_advanced.stale_detector import StaleDetector

__all__ = [
    "AnomalyDetector",
    "AnomalyReport",
    "CostAnalyzer",
    "CostReport",
    "ForecastReport",
    "LatencyReport",
    "OptimizationRecommender",
    "OptimizationRecommendation",
    "PerformanceRanking",
    "PerformanceScorer",
    "StaleDetector",
    "StaleTool",
    "ToolPerformanceScore",
    "UsageForecaster",
]
