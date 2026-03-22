"""Provider health tracking for the LLM router.

Tracks success/failure rates, latency, and auto-demotes providers after
consecutive failures. Exponential backoff: 5m -> 10m -> 30m max.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("ai.health")

_FAILURE_THRESHOLD = 3
_BASE_COOLDOWN_S = 300
_MAX_COOLDOWN_S = 1800


@dataclass
class ProviderHealth:
    """Health state for a single LLM provider."""

    name: str
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_latency_ms: float = 0.0
    last_error: str | None = None
    last_error_time: float | None = None
    disabled_until: float | None = None
    auth_broken: bool = False
    _demotion_count: int = field(default=0, repr=False)

    @property
    def score(self) -> float:
        """0.0-1.0 health score. Cold start = 0.5 (neutral)."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        success_rate = self.success_count / total
        avg_latency = self.total_latency_ms / total
        latency_score = max(0.0, 1.0 - (avg_latency / 10000))
        return 0.7 * success_rate + 0.3 * latency_score

    @property
    def is_disabled(self) -> bool:
        """True if the provider is currently in a cooldown period."""
        if self.disabled_until is None:
            return False
        return time.time() < self.disabled_until


class HealthTracker:
    """Manages health state for all LLM providers."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderHealth] = {}

    def get(self, name: str) -> ProviderHealth:
        """Get or create a ProviderHealth entry."""
        if name not in self._providers:
            self._providers[name] = ProviderHealth(name=name)
        return self._providers[name]

    def record_success(self, name: str, latency_ms: float) -> None:
        """Record a successful API call."""
        h = self.get(name)
        h.success_count += 1
        h.total_latency_ms += latency_ms
        h.consecutive_failures = 0
        h.auth_broken = False

    def record_failure(self, name: str, error: str) -> None:
        """Record a failed API call. Auto-demotes after threshold."""
        h = self.get(name)
        h.failure_count += 1
        h.consecutive_failures += 1
        h.last_error = error
        h.last_error_time = time.time()

        if "401" in error or "403" in error:
            h.auth_broken = True

        if h.consecutive_failures >= _FAILURE_THRESHOLD:
            cooldown = min(
                _BASE_COOLDOWN_S * (2 ** h._demotion_count),
                _MAX_COOLDOWN_S,
            )
            h.disabled_until = time.time() + cooldown
            h._demotion_count += 1
            logger.warning(
                "Provider '%s' disabled for %ds after %d consecutive failures",
                name, cooldown, h.consecutive_failures,
            )

    def get_sorted(self, names: list[str]) -> list[ProviderHealth]:
        """Return health entries sorted by score descending, excluding disabled."""
        result = []
        for name in names:
            h = self.get(name)
            if not h.is_disabled:
                result.append(h)
        result.sort(key=lambda h: h.score, reverse=True)
        return result
