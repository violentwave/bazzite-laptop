"""Tests for P104 Advanced Tool Analytics.

Tests the optimization tools including:
- Anomaly detection
- Cost analysis
- Performance scoring
- Stale tool detection
- Forecasting
- Recommendations
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai.mcp_bridge.analytics_advanced import (
    AnomalyDetector,
    CostAnalyzer,
    OptimizationRecommender,
    PerformanceScorer,
    StaleDetector,
    UsageForecaster,
)
from ai.mcp_bridge.analytics_advanced.models import (
    AnomalyReport,
    CostMetric,
    CostReport,
    ForecastReport,
    LatencyMetric,
    LatencyReport,
    OptimizationCategory,
    OptimizationRecommendation,
    PerformanceRanking,
    RecommendationPriority,
    StaleTool,
    StaleToolStatus,
    ToolPerformanceScore,
)
from ai.mcp_bridge.governance.analytics import ToolUsageAnalytics
from ai.mcp_bridge.governance.models import ToolRanking, UsageSummary


class MockToolUsageMetric:
    def __init__(
        self,
        tool_name: str,
        category: str,
        invocations: int = 10,
        avg_latency_ms: float = 100.0,
        p95_latency_ms: float = 200.0,
        error_rate: float = 0.0,
        cost_usd: float = 0.01,
    ):
        self.timestamp = datetime.utcnow()
        self.tool_name = tool_name
        self.category = category
        self.invocations = invocations
        self.avg_latency_ms = avg_latency_ms
        self.p95_latency_ms = p95_latency_ms
        self.error_rate = error_rate
        self.cost_usd = cost_usd


@pytest.fixture
def mock_analytics():
    """Create mock analytics instance."""
    analytics = MagicMock(spec=ToolUsageAnalytics)

    mock_summary = MagicMock(spec=UsageSummary)
    mock_summary.top_tools = [
        ToolRanking(
            tool_name="test.tool",
            category="testing",
            rank=1,
            metric_value=100.0,
            metric_name="invocations",
        ),
        ToolRanking(
            tool_name="slow.tool",
            category="system",
            rank=2,
            metric_value=50.0,
            metric_name="invocations",
        ),
    ]
    mock_summary.categories = {"test.tool": "testing", "slow.tool": "system"}

    analytics.get_usage_summary = AsyncMock(return_value=mock_summary)
    analytics.get_tool_metrics = AsyncMock(
        return_value=[
            MockToolUsageMetric("test.tool", "testing", invocations=100),
            MockToolUsageMetric("test.tool", "testing", invocations=110),
            MockToolUsageMetric("test.tool", "testing", invocations=90),
        ]
    )

    return analytics


class TestAnomalyDetector:
    """Tests for AnomalyDetector."""

    @pytest.fixture
    def detector(self, mock_analytics):
        return AnomalyDetector(mock_analytics)

    @pytest.mark.asyncio
    async def test_detect_all_anomalies_empty(self, detector):
        report = await detector.detect_all_anomalies()
        assert isinstance(report, AnomalyReport)
        assert report.anomalies_detected >= 0

    @pytest.mark.asyncio
    async def test_detect_all_anomalies_with_time(self, detector):
        start = datetime.utcnow() - timedelta(days=1)
        end = datetime.utcnow()
        report = await detector.detect_all_anomalies(start, end, "medium")
        assert isinstance(report, AnomalyReport)
        assert report.period_start == start
        assert report.period_end == end

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, detector):
        recs = await detector.generate_recommendations()
        assert isinstance(recs, list)


class TestCostAnalyzer:
    """Tests for CostAnalyzer."""

    @pytest.fixture
    def analyzer(self, mock_analytics):
        return CostAnalyzer(mock_analytics)

    @pytest.mark.asyncio
    async def test_generate_cost_report(self, analyzer):
        report = await analyzer.generate_cost_report()
        assert isinstance(report, CostReport)
        assert report.total_cost_usd >= 0

    @pytest.mark.asyncio
    async def test_generate_cost_report_with_time(self, analyzer):
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()
        report = await analyzer.generate_cost_report(start, end)
        assert isinstance(report, CostReport)
        assert len(report.recommendations) >= 0


class TestPerformanceScorer:
    """Tests for PerformanceScorer."""

    @pytest.fixture
    def scorer(self, mock_analytics):
        return PerformanceScorer(mock_analytics)

    @pytest.mark.asyncio
    async def test_generate_latency_report(self, scorer):
        report = await scorer.generate_latency_report()
        assert isinstance(report, LatencyReport)
        assert report.overall_avg_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_performance_ranking(self, scorer):
        ranking = await scorer.generate_performance_ranking()
        assert isinstance(ranking, PerformanceRanking)
        assert ranking.total_tools >= 0


class TestStaleDetector:
    """Tests for StaleDetector."""

    @pytest.fixture
    def detector(self, mock_analytics):
        return StaleDetector(mock_analytics)

    @pytest.mark.asyncio
    async def test_detect_stale_tools(self, detector):
        stale = await detector.detect_stale_tools()
        assert isinstance(stale, list)

    @pytest.mark.asyncio
    async def test_get_stale_summary(self, detector):
        summary = await detector.get_stale_summary()
        assert isinstance(summary, dict)
        assert "total_stale_tools" in summary


class TestUsageForecaster:
    """Tests for UsageForecaster."""

    @pytest.fixture
    def forecaster(self, mock_analytics):
        return UsageForecaster(mock_analytics)

    @pytest.mark.asyncio
    async def test_forecast_usage(self, forecaster):
        report = await forecaster.forecast_usage()
        assert isinstance(report, ForecastReport)
        assert report.total_invocations_current >= 0


class TestOptimizationRecommender:
    """Tests for OptimizationRecommender."""

    @pytest.fixture
    def recommender(self, mock_analytics):
        return OptimizationRecommender(mock_analytics)

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, recommender):
        recs = await recommender.generate_recommendations()
        assert isinstance(recs, list)

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_limit(self, recommender):
        recs = await recommender.generate_recommendations(max_recommendations=5)
        assert len(recs) <= 5


class TestModels:
    """Tests for P104 models."""

    def test_optimization_recommendation_creation(self):
        rec = OptimizationRecommendation(
            category=OptimizationCategory.COST,
            priority=RecommendationPriority.HIGH,
            title="Test recommendation",
            description="Test description",
            tool_name="test.tool",
            estimated_impact="medium",
        )
        assert rec.category == OptimizationCategory.COST
        assert rec.priority == RecommendationPriority.HIGH

    def test_stale_tool_creation(self):
        tool = StaleTool(
            tool_name="test.tool",
            category="testing",
            status=StaleToolStatus.UNUSED,
            invocation_count=0,
            recommendation="Remove unused tool",
        )
        assert tool.status == StaleToolStatus.UNUSED

    def test_cost_metric_creation(self):
        metric = CostMetric(
            tool_name="test.tool",
            total_cost_usd=10.0,
            cost_per_invocation=0.01,
        )
        assert metric.total_cost_usd == 10.0

    def test_latency_metric_creation(self):
        metric = LatencyMetric(
            tool_name="test.tool",
            avg_latency_ms=100.0,
            p50_latency_ms=80.0,
            p95_latency_ms=200.0,
            grade="B",
        )
        assert metric.grade == "B"

    def test_performance_score_creation(self):
        score = ToolPerformanceScore(
            tool_name="test.tool",
            category="testing",
            overall_score=85.0,
            latency_score=90.0,
            reliability_score=80.0,
            cost_efficiency_score=85.0,
            usage_score=75.0,
            grade="B",
        )
        assert score.overall_score == 85.0


class TestToolOptimizationHandlers:
    """Tests for MCP tool handlers."""

    def test_handler_imports(self):
        from ai.mcp_bridge.tool_optimization_handlers import (
            handle_tool_optimization_anomalies,
            handle_tool_optimization_cost_report,
            handle_tool_optimization_forecast,
            handle_tool_optimization_latency_report,
            handle_tool_optimization_recommend,
            handle_tool_optimization_stale_tools,
        )

        assert callable(handle_tool_optimization_recommend)
        assert callable(handle_tool_optimization_stale_tools)
        assert callable(handle_tool_optimization_cost_report)
        assert callable(handle_tool_optimization_latency_report)
        assert callable(handle_tool_optimization_anomalies)
        assert callable(handle_tool_optimization_forecast)
