"""Pydantic models for MCP tool governance.

P101: MCP Tool Governance + Analytics Platform
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LifecycleState(StrEnum):
    """Tool lifecycle states."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    LEGACY = "legacy"
    RETIRED = "retired"


class CircuitBreakerState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class InvocationContext(BaseModel):
    """Context for a tool invocation."""

    session_id: str | None = None
    user_agent: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    arguments: dict = Field(default_factory=dict)


class ToolUsageMetric(BaseModel):
    """Usage metric for a single tool invocation or aggregation."""

    timestamp: datetime
    tool_name: str
    category: str
    invocations: int = 1
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    unique_callers: int = 0
    token_usage: int = 0
    cost_usd: float = 0.0


class ToolLifecycleState(BaseModel):
    """Lifecycle state for a tool."""

    tool_name: str
    current_state: LifecycleState = LifecycleState.ACTIVE
    version: str = "1.0.0"
    introduced_at: datetime = Field(default_factory=datetime.utcnow)
    deprecated_at: datetime | None = None
    sunset_date: datetime | None = None
    retired_at: datetime | None = None
    replacement_tool: str | None = None
    migration_guide: str | None = None


class ToolRanking(BaseModel):
    """Ranking information for a tool."""

    tool_name: str
    category: str
    rank: int
    metric_value: float
    metric_name: str


class Anomaly(BaseModel):
    """Detected anomaly in tool usage."""

    tool_name: str
    anomaly_type: str
    severity: str  # low, medium, high, critical
    detected_at: datetime
    description: str
    expected_value: float | None = None
    actual_value: float | None = None


class PermissionAudit(BaseModel):
    """Result of a permission audit."""

    tool_name: str
    audit_timestamp: datetime
    requires_elevated: bool = False
    accesses_sensitive_data: bool = False
    data_exposure_risk: str = "low"  # low, medium, high
    recommendations: list[str] = Field(default_factory=list)
    compliant: bool = True


class SecurityScore(BaseModel):
    """Security score for a tool."""

    tool_name: str
    score: int = Field(ge=0, le=100)
    category: str
    factors: dict[str, int] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class GovernancePolicy(BaseModel):
    """A governance policy."""

    id: str
    name: str
    description: str
    applies_to: str  # Tool name pattern (e.g., "security.*")
    rules: list[dict[str, Any]] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EnforcementResult(BaseModel):
    """Result of policy enforcement."""

    tool_name: str
    policy_id: str
    allowed: bool
    reason: str | None = None
    action_taken: str | None = None


class MigrationPath(BaseModel):
    """Migration path for deprecated tools."""

    from_tool: str
    to_tool: str
    compatibility_level: str  # full, partial, breaking
    migration_steps: list[str] = Field(default_factory=list)
    automation_available: bool = False


class HealthStatus(BaseModel):
    """Health status of a tool."""

    tool_name: str
    healthy: bool
    last_check: datetime
    error_rate_24h: float = 0.0
    avg_latency_24h: float = 0.0
    availability_24h: float = 100.0
    issues: list[str] = Field(default_factory=list)


class CircuitBreakerStatus(BaseModel):
    """Status of circuit breaker for a tool."""

    tool_name: str
    state: CircuitBreakerState
    failure_count: int = 0
    last_failure: datetime | None = None
    opened_at: datetime | None = None
    next_retry: datetime | None = None


class UsageSummary(BaseModel):
    """Summary of tool usage for a time range."""

    start_time: datetime
    end_time: datetime
    total_invocations: int
    total_errors: int
    overall_error_rate: float
    avg_latency_ms: float
    top_tools: list[ToolRanking]
    categories: dict[str, int]


class ComplianceReport(BaseModel):
    """System-wide governance compliance report."""

    generated_at: datetime
    total_tools: int
    compliant_tools: int
    non_compliant_tools: list[str]
    policy_violations: list[dict[str, Any]]
    security_scores: list[SecurityScore]
    recommendations: list[str]


class HealthReport(BaseModel):
    """Comprehensive health report."""

    generated_at: datetime
    healthy_tools: int
    degraded_tools: int
    unhealthy_tools: int
    circuit_breakers_tripped: list[str]
    recent_anomalies: list[Anomaly]
    top_issues: list[str]


class IngestionResult(BaseModel):
    """Result of a single ingestion target."""

    target_name: str
    success: bool
    records_processed: int = 0
    error_message: str | None = None
    duration_ms: float = 0.0


class CloseoutReport(BaseModel):
    """Complete closeout report."""

    phase_name: str
    run_id: str
    started_at: datetime
    completed_at: datetime
    results: list[IngestionResult]
    all_succeeded: bool
    partial_success: bool
    failure_count: int
    coverage_metrics: dict[str, Any]
