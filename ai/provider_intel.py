"""Provider intelligence for dynamic routing based on metrics.

Analyzes P24 metrics data to score providers by latency, error rate, cost,
and health status. Enables intelligent provider selection beyond static chains.
"""

import logging
from typing import Any

from ai.health import HealthTracker

logger = logging.getLogger("bazzite-ai.provider_intel")

PROVIDER_COSTS = {
    "gemini": {"input": 0.0, "output": 0.0},
    "groq": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
    "openrouter": {"input": 0.001, "output": 0.002},
    "zai": {"input": 0.0, "output": 0.0},
    "cerebras": {"input": 0.0, "output": 0.0},
}

PROVIDER_TASKS = {
    "fast": ["gemini", "groq", "mistral", "openrouter", "zai", "cerebras"],
    "reason": ["gemini", "groq", "mistral", "openrouter", "zai"],
    "batch": ["gemini", "groq", "mistral", "openrouter", "cerebras"],
    "code": ["gemini", "groq", "mistral", "openrouter", "zai"],
    "embed": ["gemini", "mistral"],
}


class ProviderIntel:
    def __init__(self) -> None:
        self._health_tracker = HealthTracker()

    def _get_recent_metrics(self, provider: str, task_type: str, minutes: int = 10) -> dict:
        try:
            from ai.metrics import get_recorder

            recorder = get_recorder()
            raw = recorder.get_raw(hours=minutes / 60, metric_type="provider", limit=1000)

            provider_metrics = [
                r
                for r in raw
                if r.get("name") == "provider_latency"
                and r.get("tags", {}).get("provider") == provider
                and r.get("tags", {}).get("task_type") == task_type
            ]

            if not provider_metrics:
                return {"count": 0, "latency_p95": 0.0, "error_rate": 0.0}

            latencies = [float(r["value"]) for r in provider_metrics]
            sorted_latencies = sorted(latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            latency_p95 = sorted_latencies[p95_idx] if sorted_latencies else 0.0

            error_metrics = [
                r
                for r in raw
                if r.get("name") == "provider_error"
                and r.get("tags", {}).get("provider") == provider
            ]

            total_calls = len(provider_metrics) + len(error_metrics)
            error_rate = len(error_metrics) / total_calls if total_calls > 0 else 0.0

            return {
                "count": len(provider_metrics),
                "latency_p95": latency_p95,
                "error_rate": error_rate,
            }
        except Exception as e:
            logger.debug("Failed to get metrics: %s", e)
            return {"count": 0, "latency_p95": 0.0, "error_rate": 0.0}

    def _get_health_multiplier(self, provider: str) -> float:
        try:
            healthy = self._health_tracker.get_sorted([provider])
            if not healthy:
                return 0.0
            for h in healthy:
                if h.name == provider:
                    if h.failures < 3:
                        return 1.0
                    elif h.failures < 10:
                        return 0.3
                    else:
                        return 0.0
            return 0.0
        except Exception:
            return 1.0

    def score_provider(self, provider: str, task_type: str | None = None) -> dict[str, Any]:
        if task_type and provider not in PROVIDER_TASKS.get(task_type, []):
            return {
                "provider": provider,
                "score": 0.0,
                "latency_p95": 0.0,
                "error_rate": 0.0,
                "cost_per_1k": 0.0,
                "health": "unavailable",
            }

        metrics = self._get_recent_metrics(provider, task_type or "fast")
        latency_p95 = metrics.get("latency_p95", 0.0)
        error_rate = metrics.get("error_rate", 0.0)

        health_multiplier = self._get_health_multiplier(provider)
        if health_multiplier == 0.0:
            health_status = "banned"
        elif health_multiplier == 0.3:
            health_status = "cooldown"
        else:
            health_status = "healthy"

        cost_per_1k = PROVIDER_COSTS.get(provider, {}).get("input", 0.0)

        score = 0.0
        if latency_p95 > 0:
            score = (1.0 / (1.0 + latency_p95)) * (1.0 - error_rate) * health_multiplier
        elif metrics.get("count", 0) == 0:
            score = 1.0 * health_multiplier

        return {
            "provider": provider,
            "score": float(score),
            "latency_p95": float(latency_p95),
            "error_rate": float(error_rate),
            "cost_per_1k": float(cost_per_1k),
            "health": health_status,
        }

    def rank_providers(self, task_type: str) -> list[dict[str, Any]]:
        providers = PROVIDER_TASKS.get(task_type, [])
        scored = [self.score_provider(p, task_type) for p in providers]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def get_status(self) -> dict[str, Any]:
        all_providers = set()
        for providers in PROVIDER_TASKS.values():
            all_providers.update(providers)

        status = {}
        for provider in all_providers:
            status[provider] = self.score_provider(provider)

        return {"providers": status}

    def choose_best(self, task_type: str, exclude: list[str] | None = None) -> str | None:
        exclude = exclude or []
        ranked = self.rank_providers(task_type)
        for entry in ranked:
            if entry["provider"] not in exclude and entry["health"] != "banned":
                if entry["score"] > 0:
                    return entry["provider"]
        return None


_intel: ProviderIntel | None = None
_intel_lock = None


def get_intel() -> ProviderIntel:
    global _intel
    if _intel is None:
        import threading

        global _intel_lock
        if _intel_lock is None:
            _intel_lock = threading.Lock()
        with _intel_lock:
            if _intel is None:
                _intel = ProviderIntel()
    return _intel
