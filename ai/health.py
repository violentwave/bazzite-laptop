"""Provider health tracking for the LLM router.

Tracks success/failure rates, latency, and auto-demotes providers after
consecutive failures. Exponential backoff: 2m -> 4m -> 10m max.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("ai.health")

_FAILURE_THRESHOLD = 5
_BASE_COOLDOWN_S = 120
_MAX_COOLDOWN_S = 600
_STALENESS_THRESHOLD_S = 600  # 10 minutes


class AllProvidersExhausted(RuntimeError):
    """Raised when no LLM provider is available for a task type."""

    def __init__(self, task_type: str, reason: str = "all providers exhausted") -> None:
        super().__init__(f"LLM call failed for task_type '{task_type}': {reason}")
        self.task_type = task_type


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
    consecutive_auth_failures: int = 0
    last_probe_time: float | None = None
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

    @property
    def effective_score(self) -> float:
        """Score with staleness cap: >10min without probe -> max 0.8."""
        s = self.score
        if (
            self.last_probe_time is not None
            and (time.time() - self.last_probe_time) > _STALENESS_THRESHOLD_S
        ):
            return min(s, 0.8)
        return s


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
        h.consecutive_auth_failures = 0
        h.auth_broken = False
        h.last_probe_time = time.time()

    def record_failure(self, name: str, error: str, status_code: int | None = None) -> None:
        """Record a failed API call. Auto-demotes after threshold."""
        h = self.get(name)
        h.failure_count += 1
        h.consecutive_failures += 1
        h.last_error = error
        h.last_error_time = time.time()
        h.last_probe_time = time.time()

        is_auth_error = status_code in (401, 403) or "401" in error or "403" in error
        if is_auth_error:
            h.consecutive_auth_failures += 1
            if h.consecutive_auth_failures >= 3:
                h.auth_broken = True
        else:
            h.consecutive_auth_failures = 0

        if h.consecutive_failures >= _FAILURE_THRESHOLD:
            cooldown = min(
                _BASE_COOLDOWN_S * (2**h._demotion_count),
                _MAX_COOLDOWN_S,
            )
            h.disabled_until = time.time() + cooldown
            h._demotion_count += 1
            logger.warning(
                "Provider '%s' disabled for %ds after %d consecutive failures",
                name,
                cooldown,
                h.consecutive_failures,
            )

    def get_sorted(self, names: list[str]) -> list[ProviderHealth]:
        """Return health entries sorted by effective_score descending, excluding disabled/auth_broken."""  # noqa: E501
        result = []
        for name in names:
            h = self.get(name)
            if not h.is_disabled and not h.auth_broken:
                result.append(h)
        result.sort(key=lambda h: h.effective_score, reverse=True)
        return result

    def reset_all(self) -> None:
        """Reset all tracked providers to a clean healthy state."""
        for h in self._providers.values():
            h.success_count = 100
            h.failure_count = 0
            h.consecutive_failures = 0
            h.consecutive_auth_failures = 0
            h.total_latency_ms = 0.0
            h.last_error = None
            h.last_error_time = None
            h.disabled_until = None
            h.auth_broken = False
            h.last_probe_time = None
            h._demotion_count = 0

    def reset_all_scores(self) -> None:
        """Reset all providers to score 1.0 and clear cooldowns. Called on service startup."""
        self.reset_all()
        logger.info("Health scores reset on startup")


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="LLM provider health management")
    parser.add_argument("--reset", action="store_true", help="Reset all provider scores to 1.0")
    args = parser.parse_args()

    if not args.reset:
        parser.print_help()
        raise SystemExit(1)

    status_path = Path.home() / "security" / "llm-status.json"
    if status_path.exists():
        data = json.loads(status_path.read_text())
    else:
        data = {}

    providers = data.get("providers", {})
    for name in providers:
        providers[name]["score"] = 1.0
        providers[name]["auth_broken"] = False

    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(data, indent=2))
    print(f"Reset {len(providers)} provider(s) to score=1.0:")
    for name in providers:
        print(f"  {name}: 1.0")
