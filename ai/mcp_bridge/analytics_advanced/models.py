"""Advanced analytics models for P104.

Defines models for optimization recommendations, cost analysis,
latency reports, anomaly detection, forecasting, and stale tool detection.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OptimizationCategory(StrEnum):
    """Categories of optimization recommendations."""

    COST = "cost"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    SECURITY = "security"
    GOVERNANCE = "governance"


class RecommendationPriority(StrEnum):
    """Priority levels for recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OptimizationRecommendation(BaseModel):
    """An actionable optimization recommendation."""

    id: str = Field(default_factory=lambda: f"rec_{datetime.utcnow().timestamp()}")
    category: OptimizationCategory
    priority: RecommendationPriority
    title: str
    description: str
    tool_name: str | None = None
    estimated_impact: str
    implementation_effort: str = "low"
    affected_tools: list[str] = Field(default_factory=list)
    metrics_before: dict[str, float] = Field(default_factory=dict)
    metrics_after: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StaleToolStatus(StrEnum):
    """Status of a stale tool."""

    UNUSED = "unused"
    DEPRECATED = "deprecated"
    REPLACED = "replaced"
    UNDERUTILIZED = "underutilized"


class StaleTool(BaseModel):
    """Tool identified as stale or underutilized."""

    tool_name: str
    category: str
    status: StaleToolStatus
    last_used: datetime | None = None
    invocation_count: int = 0
    days_since_last_use: int | None = None
    recommendation: str
    replacement_tool: str | None = None
    estimated_cost_savings: float = 0.0


class CostMetric(BaseModel):
    """Cost metric for a tool."""

    tool_name: str
    total_cost_usd: float = 0.0
    cost_per_invocation: float = 0.0
    cost_per_1k_tokens: float = 0.0
    daily_cost: float = 0.0
    monthly_cost: float = 0.0
    yearly_cost: float = 0.0
    trend: str = "stable"  # increasing, decreasing, stable
    percent_of_total: float = 0.0


class CostReport(BaseModel):
    """Comprehensive cost analysis report."""

    period_start: datetime
    period_end: datetime
    total_cost_usd: float = 0.0
    tool_costs: list[CostMetric] = Field(default_factory=list)
    top_cost_tools: list[str] = Field(default_factory=list)
    cost_by_category: dict[str, float] = Field(default_factory=dict)
    trend_summary: str = "stable"
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class LatencyMetric(BaseModel):
    """Latency metric for a tool."""

    tool_name: str
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    std_deviation_ms: float = 0.0
    invocations: int = 0
    trend: str = "stable"
    grade: str = "A"  # A-F


class LatencyReport(BaseModel):
    """Comprehensive latency analysis report."""

    period_start: datetime
    period_end: datetime
    overall_avg_ms: float = 0.0
    tool_latencies: list[LatencyMetric] = Field(default_factory=list)
    slowest_tools: list[str] = Field(default_factory=list)
    fastest_tools: list[str] = Field(default_factory=list)
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AnomalyReport(BaseModel):
    """Report of detected anomalies in tool usage."""

    period_start: datetime
    period_end: datetime
    anomalies_detected: int = 0
    critical_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    high_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    medium_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    low_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    affected_tools: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ForecastMetric(BaseModel):
    """Forecasted metric for a tool."""

    tool_name: str
    metric_name: str
    current_value: float
    forecast_1d: float = 0.0
    forecast_7d: float = 0.0
    forecast_30d: float = 0.0
    confidence: float = 0.0  # 0-1
    trend: str = "stable"  # increasing, decreasing, stable


class ForecastReport(BaseModel):
    """Usage forecasting report."""

    period_start: datetime
    period_end: datetime
    total_invocations_current: int = 0
    total_invocations_forecast_7d: int = 0
    total_invocations_forecast_30d: int = 0
    total_cost_current: float = 0.0
    total_cost_forecast_7d: float = 0.0
    total_cost_forecast_30d: float = 0.0
    tool_forecasts: list[ForecastMetric] = Field(default_factory=list)
    peak_usage_tools: list[str] = Field(default_factory=list)
    growth_rate: float = 0.0
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ToolPerformanceScore(BaseModel):
    """Performance score for a tool."""

    tool_name: str
    category: str
    overall_score: float = Field(ge=0, le=100)
    latency_score: float = Field(ge=0, le=100)
    reliability_score: float = Field(ge=0, le=100)
    cost_efficiency_score: float = Field(ge=0, le=100)
    usage_score: float = Field(ge=0, le=100)
    grade: str = "B"
    percentile_rank: int = 0
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class PerformanceRanking(BaseModel):
    """Ranking of tools by performance."""

    period_start: datetime
    period_end: datetime
    rankings: list[ToolPerformanceScore] = Field(default_factory=list)
    total_tools: int = 0
    average_score: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
