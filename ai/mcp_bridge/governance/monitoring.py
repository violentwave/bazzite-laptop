"""Tool monitoring and circuit breakers.

P101: MCP Tool Governance + Analytics Platform

Provides health checks, circuit breakers, and alerting for MCP tools.
"""

import asyncio
from datetime import datetime, timedelta

from ai.mcp_bridge.governance.models import (
    Anomaly,
    CircuitBreakerState,
    CircuitBreakerStatus,
    HealthReport,
    HealthStatus,
)


class ToolMonitor:
    """Monitors tool health and manages circuit breakers.

    Provides health checks, circuit breaker pattern implementation,
    anomaly tracking, and health reporting for all MCP tools.
    """

    # Circuit breaker configuration
    FAILURE_THRESHOLD = 10
    FAILURE_WINDOW_SECONDS = 60
    OPEN_DURATION_SECONDS = 300  # 5 minutes
    HALF_OPEN_SUCCESS_THRESHOLD = 5

    def __init__(self):
        """Initialize tool monitor."""
        self._circuit_breakers: dict[str, CircuitBreakerStatus] = {}
        self._failure_history: dict[str, list[datetime]] = {}
        self._success_history: dict[str, list[datetime]] = {}
        self._health_cache: dict[str, HealthStatus] = {}
        self._anomalies: list[Anomaly] = []
        self._lock = asyncio.Lock()

    async def record_invocation_result(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        """Record the result of a tool invocation.

        Args:
            tool_name: Name of the tool
            success: Whether invocation succeeded
            duration_ms: Invocation duration
        """
        now = datetime.utcnow()

        async with self._lock:
            # Ensure circuit breaker exists
            if tool_name not in self._circuit_breakers:
                self._circuit_breakers[tool_name] = CircuitBreakerStatus(
                    tool_name=tool_name,
                    state=CircuitBreakerState.CLOSED,
                )

            cb = self._circuit_breakers[tool_name]

            if success:
                # Record success
                if tool_name not in self._success_history:
                    self._success_history[tool_name] = []
                self._success_history[tool_name].append(now)

                # Clean old successes
                cutoff = now - timedelta(seconds=self.FAILURE_WINDOW_SECONDS)
                self._success_history[tool_name] = [
                    t for t in self._success_history[tool_name] if t > cutoff
                ]

                # Handle half-open state
                if cb.state == CircuitBreakerState.HALF_OPEN:
                    recent_successes = len(self._success_history.get(tool_name, []))
                    if recent_successes >= self.HALF_OPEN_SUCCESS_THRESHOLD:
                        cb.state = CircuitBreakerState.CLOSED
                        cb.failure_count = 0
                        cb.opened_at = None
                        cb.next_retry = None

            else:
                # Record failure
                if tool_name not in self._failure_history:
                    self._failure_history[tool_name] = []
                self._failure_history[tool_name].append(now)
                cb.failure_count += 1
                cb.last_failure = now

                # Clean old failures
                cutoff = now - timedelta(seconds=self.FAILURE_WINDOW_SECONDS)
                self._failure_history[tool_name] = [
                    t for t in self._failure_history[tool_name] if t > cutoff
                ]

                # Check if circuit should trip
                recent_failures = len(self._failure_history.get(tool_name, []))
                if recent_failures >= self.FAILURE_THRESHOLD:
                    if cb.state != CircuitBreakerState.OPEN:
                        cb.state = CircuitBreakerState.OPEN
                        cb.opened_at = now
                        cb.next_retry = now + timedelta(seconds=self.OPEN_DURATION_SECONDS)

    async def check_circuit_breaker(self, tool_name: str) -> CircuitBreakerStatus:
        """Check circuit breaker state for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Circuit breaker status
        """
        now = datetime.utcnow()

        async with self._lock:
            if tool_name not in self._circuit_breakers:
                return CircuitBreakerStatus(
                    tool_name=tool_name,
                    state=CircuitBreakerState.CLOSED,
                )

            cb = self._circuit_breakers[tool_name]

            # Check if it's time to transition from OPEN to HALF_OPEN
            if cb.state == CircuitBreakerState.OPEN and cb.next_retry and now >= cb.next_retry:
                cb.state = CircuitBreakerState.HALF_OPEN
                cb.next_retry = None
                # Clear success history for half-open counting
                self._success_history[tool_name] = []

            return cb

    async def can_execute(self, tool_name: str) -> tuple[bool, str | None]:
        """Check if a tool can be executed.

        Args:
            tool_name: Name of the tool

        Returns:
            Tuple of (can_execute, reason_if_not)
        """
        cb = await self.check_circuit_breaker(tool_name)

        if cb.state == CircuitBreakerState.OPEN:
            return False, f"Circuit breaker OPEN until {cb.next_retry}"

        return True, None

    async def health_check(
        self,
        tool_name: str,
        analytics_data: dict | None = None,
    ) -> HealthStatus:
        """Perform health check on a tool.

        Args:
            tool_name: Name of the tool
            analytics_data: Optional usage analytics data

        Returns:
            Health status
        """
        now = datetime.utcnow()
        issues = []

        # Check circuit breaker state
        cb = await self.check_circuit_breaker(tool_name)
        if cb.state == CircuitBreakerState.OPEN:
            issues.append(f"Circuit breaker is OPEN (tripped at {cb.opened_at})")

        # Calculate error rate from recent history
        cutoff = now - timedelta(hours=24)
        recent_failures = len([t for t in self._failure_history.get(tool_name, []) if t > cutoff])
        recent_successes = len([t for t in self._success_history.get(tool_name, []) if t > cutoff])
        total = recent_failures + recent_successes
        error_rate = recent_failures / total if total > 0 else 0.0

        # Check for anomalies
        if error_rate > 0.1:
            issues.append(f"High error rate: {error_rate:.1%} in last 24h")

        # Calculate availability
        availability = (1 - error_rate) * 100 if total > 0 else 100.0

        healthy = len(issues) == 0 and cb.state != CircuitBreakerState.OPEN

        status = HealthStatus(
            tool_name=tool_name,
            healthy=healthy,
            last_check=now,
            error_rate_24h=error_rate,
            avg_latency_24h=0.0,  # Would be calculated from analytics
            availability_24h=availability,
            issues=issues,
        )

        self._health_cache[tool_name] = status
        return status

    async def add_anomaly(self, anomaly: Anomaly) -> None:
        """Add a detected anomaly.

        Args:
            anomaly: Anomaly to add
        """
        async with self._lock:
            self._anomalies.append(anomaly)
            # Keep only recent anomalies
            cutoff = datetime.utcnow() - timedelta(days=7)
            self._anomalies = [a for a in self._anomalies if a.detected_at > cutoff]

    async def get_active_anomalies(
        self,
        tool_name: str | None = None,
        min_severity: str = "low",
    ) -> list[Anomaly]:
        """Get active anomalies.

        Args:
            tool_name: Optional tool filter
            min_severity: Minimum severity level

        Returns:
            List of matching anomalies
        """
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order.get(min_severity, 0)

        anomalies = self._anomalies

        if tool_name:
            anomalies = [a for a in anomalies if a.tool_name == tool_name]

        return [a for a in anomalies if severity_order.get(a.severity, 0) >= min_level]

    async def generate_health_report(self) -> HealthReport:
        """Generate comprehensive health report.

        Returns:
            Health report
        """
        now = datetime.utcnow()

        healthy = 0
        degraded = 0
        unhealthy = 0
        tripped_breakers = []

        async with self._lock:
            for tool_name, cb in self._circuit_breakers.items():
                if cb.state == CircuitBreakerState.OPEN:
                    tripped_breakers.append(tool_name)
                    unhealthy += 1
                else:
                    # Check error rate
                    cutoff = now - timedelta(hours=24)
                    recent_failures = len(
                        [t for t in self._failure_history.get(tool_name, []) if t > cutoff]
                    )
                    recent_successes = len(
                        [t for t in self._success_history.get(tool_name, []) if t > cutoff]
                    )
                    total = recent_failures + recent_successes

                    if total > 0:
                        error_rate = recent_failures / total
                        if error_rate > 0.1:
                            unhealthy += 1
                        elif error_rate > 0.05:
                            degraded += 1
                        else:
                            healthy += 1
                    else:
                        healthy += 1

        # Count tools without any monitoring as healthy
        # In a real implementation, we'd check all registered tools
        healthy += max(0, 133 - healthy - degraded - unhealthy)

        # Get recent anomalies
        recent_anomalies = [a for a in self._anomalies if a.detected_at > now - timedelta(hours=24)]

        # Top issues
        top_issues = []
        if tripped_breakers:
            top_issues.append(
                f"{len(tripped_breakers)} circuit breakers tripped: "
                f"{', '.join(tripped_breakers[:5])}"
            )
        if recent_anomalies:
            critical_anomalies = [a for a in recent_anomalies if a.severity == "critical"]
            if critical_anomalies:
                top_issues.append(f"{len(critical_anomalies)} critical anomalies detected")

        return HealthReport(
            generated_at=now,
            healthy_tools=healthy,
            degraded_tools=degraded,
            unhealthy_tools=unhealthy,
            circuit_breakers_tripped=tripped_breakers,
            recent_anomalies=recent_anomalies,
            top_issues=top_issues,
        )

    async def reset_circuit_breaker(self, tool_name: str) -> None:
        """Manually reset a circuit breaker.

        Args:
            tool_name: Name of the tool
        """
        async with self._lock:
            if tool_name in self._circuit_breakers:
                cb = self._circuit_breakers[tool_name]
                cb.state = CircuitBreakerState.CLOSED
                cb.failure_count = 0
                cb.opened_at = None
                cb.next_retry = None
                cb.last_failure = None

            # Clear history
            if tool_name in self._failure_history:
                self._failure_history[tool_name] = []
            if tool_name in self._success_history:
                self._success_history[tool_name] = []

    async def get_circuit_breaker_summary(self) -> dict:
        """Get summary of all circuit breakers.

        Returns:
            Dictionary with circuit breaker counts
        """
        async with self._lock:
            summary = {
                "closed": 0,
                "open": 0,
                "half_open": 0,
                "total": len(self._circuit_breakers),
            }

            for cb in self._circuit_breakers.values():
                if cb.state == CircuitBreakerState.CLOSED:
                    summary["closed"] += 1
                elif cb.state == CircuitBreakerState.OPEN:
                    summary["open"] += 1
                elif cb.state == CircuitBreakerState.HALF_OPEN:
                    summary["half_open"] += 1

            return summary
