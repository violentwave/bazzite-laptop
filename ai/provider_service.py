"""Provider and Model Discovery + Routing Console Service.

P82 — Provider + Model Discovery / Routing Console
P115 — Provider Registry + Routing Persistence v2 (integration)

Provides:
- Provider discovery from secure runtime config
- Provider health and auth viability tracking
- Model catalog per provider with normalization
- Task-type routing configuration (fast, reason, batch, code, embed)
- Fallback chain visualization
- Refresh/invalidation after secrets changes
- Local Ollama embed visibility
- Durable provider registry (P115)

Integration with P81:
- Receives refresh triggers from settings_service._trigger_provider_refresh()
- Reads provider keys via config.KEY_SCOPES["llm"]
- Respects secure backend ownership of secrets

Integration with P115:
- Uses ProviderRegistry for custom provider storage
- Generates routing config from registry
- Merges built-in and custom providers
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml

from ai.config import APP_NAME, CONFIGS_DIR, get_key
from ai.health import HealthTracker, ProviderHealth
from ai.provider_registry import (
    ProviderRegistry,
    get_provider_registry,
)

logger = logging.getLogger(APP_NAME)

# ── Constants ────────────────────────────────────────────────────────────────

LITELLM_CONFIG_PATH = CONFIGS_DIR / "litellm-config.yaml"
PROVIDER_STATUS_FILE = Path.home() / "security" / "provider-status.json"

# Known provider configurations
KNOWN_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com",
        "models": [
            {
                "id": "gemini-2.5-flash-lite",
                "name": "Gemini 2.5 Flash Lite",
                "task_types": ["fast", "batch"],
            },
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "task_types": ["code"]},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "task_types": ["reason"]},
            {"id": "gemini-embedding-001", "name": "Gemini Embedding", "task_types": ["embed"]},
        ],
    },
    "groq": {
        "name": "Groq",
        "key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com",
        "models": [
            {
                "id": "llama-3.3-70b-versatile",
                "name": "Llama 3.3 70B",
                "task_types": ["fast", "reason", "batch", "code"],
            },
        ],
    },
    "mistral": {
        "name": "Mistral AI",
        "key_env": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai",
        "models": [
            {
                "id": "mistral-small-latest",
                "name": "Mistral Small",
                "task_types": ["fast", "batch"],
            },
            {"id": "mistral-large-latest", "name": "Mistral Large", "task_types": ["reason"]},
            {"id": "codestral-latest", "name": "Codestral", "task_types": ["code"]},
            {"id": "mistral-embed", "name": "Mistral Embed", "task_types": ["embed"]},
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai",
        "models": [
            {
                "id": "meta-llama/llama-3.3-70b-instruct",
                "name": "Llama 3.3 70B",
                "task_types": ["fast", "batch"],
            },
            {
                "id": "anthropic/claude-sonnet-4",
                "name": "Claude Sonnet 4",
                "task_types": ["reason", "code"],
            },
        ],
    },
    "z.ai": {
        "name": "z.ai",
        "key_env": "ZAI_API_KEY",
        "base_url": "https://api.z.ai",
        "models": [
            {"id": "glm-4.7-flash", "name": "GLM 4.7 Flash", "task_types": ["fast"]},
            {"id": "glm-4.7", "name": "GLM 4.7", "task_types": ["reason", "code"]},
        ],
    },
    "cerebras": {
        "name": "Cerebras",
        "key_env": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai",
        "models": [
            {
                "id": "llama-4-scout-17b-16e-instruct",
                "name": "Llama 4 Scout",
                "task_types": ["fast", "batch"],
            },
        ],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "key_env": None,  # No API key needed for local
        "base_url": "http://localhost:11434",
        "models": [
            {"id": "nomic-embed-text", "name": "Nomic Embed Text", "task_types": ["embed"]},
        ],
        "is_local": True,
    },
}

TASK_TYPE_LABELS = {
    "fast": "Fast (Interactive)",
    "reason": "Reason (Analysis)",
    "batch": "Batch (Volume)",
    "code": "Code (Generation)",
    "embed": "Embed (Vectors)",
}


class ProviderStatus(Enum):
    """Provider availability status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ModelInfo:
    """Information about a model."""

    id: str
    name: str
    provider: str
    task_types: list[str]
    is_available: bool = True


@dataclass
class ProviderInfo:
    """Information about a provider."""

    id: str
    name: str
    status: str
    is_configured: bool
    is_healthy: bool
    is_local: bool
    models: list[ModelInfo]
    health_score: float
    last_error: str | None
    last_probe_time: float | None


@dataclass
class RoutingEntry:
    """Routing configuration for a task type."""

    task_type: str
    task_label: str
    primary_provider: str | None
    fallback_chain: list[str]
    eligible_models: list[ModelInfo]
    health_state: str
    caveats: str | None


# ── Provider Service ─────────────────────────────────────────────────────────


class ProviderService:
    """Manages provider discovery, health, and routing configuration."""

    def __init__(self) -> None:
        self.health_tracker = HealthTracker()
        self._last_refresh = 0.0
        self._refresh_interval = 30  # seconds

    def _load_litellm_config(self) -> dict:
        """Load the LiteLLM routing configuration."""
        try:
            with open(LITELLM_CONFIG_PATH) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Failed to load litellm config: %s", e)
            return {}

    def _check_provider_configured(self, provider_id: str) -> bool:
        """Check if a provider has its API key configured."""
        provider = KNOWN_PROVIDERS.get(provider_id)
        if not provider:
            return False

        key_env = provider.get("key_env")
        if key_env is None:
            # Local provider (Ollama) - check if service is reachable
            return self._check_ollama_available()

        # Check if key is set in environment
        return get_key(key_env) is not None

    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running locally."""
        import urllib.request

        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as response:  # noqa: S310
                return response.status == 200
        except Exception:
            return False

    def _get_provider_health(self, provider_id: str) -> ProviderHealth:
        """Get health state for a provider."""
        return self.health_tracker.get(provider_id)

    def _determine_status(self, provider_id: str, is_configured: bool) -> ProviderStatus:
        """Determine the status of a provider."""
        if not is_configured:
            return ProviderStatus.NOT_CONFIGURED

        health = self._get_provider_health(provider_id)

        if health.auth_broken:
            return ProviderStatus.BLOCKED

        if health.is_disabled:
            return ProviderStatus.UNAVAILABLE

        if health.consecutive_failures > 0:
            return ProviderStatus.DEGRADED

        return ProviderStatus.HEALTHY

    def discover_providers(self) -> list[ProviderInfo]:
        """Discover all providers and their status."""
        providers = []

        for provider_id, config in KNOWN_PROVIDERS.items():
            is_configured = self._check_provider_configured(provider_id)
            health = self._get_provider_health(provider_id)
            status = self._determine_status(provider_id, is_configured)

            models = [
                ModelInfo(
                    id=m["id"],
                    name=m["name"],
                    provider=provider_id,
                    task_types=m["task_types"],
                    is_available=is_configured and status != ProviderStatus.BLOCKED,
                )
                for m in config.get("models", [])
            ]

            info = ProviderInfo(
                id=provider_id,
                name=config["name"],
                status=status.value,
                is_configured=is_configured,
                is_healthy=status == ProviderStatus.HEALTHY,
                is_local=config.get("is_local", False),
                models=models,
                health_score=health.effective_score,
                last_error=health.last_error,
                last_probe_time=health.last_probe_time,
            )
            providers.append(info)

        # Sort: configured first, then by health score
        providers.sort(key=lambda p: (not p.is_configured, -p.health_score))
        return providers

    def get_model_catalog(self) -> list[ModelInfo]:
        """Get all models across all providers."""
        models = []
        for provider in self.discover_providers():
            for model in provider.models:
                if model.is_available:
                    models.append(model)
        return models

    def get_routing_config(self) -> list[RoutingEntry]:
        """Get routing configuration for all task types."""
        config = self._load_litellm_config()
        model_list = config.get("model_list", [])

        # Group by task type
        task_providers: dict[str, list[tuple[str, str, bool]]] = {}
        # (provider_id, model_id, is_configured)

        for entry in model_list:
            task_type = entry.get("model_name")
            if not task_type:
                continue

            params = entry.get("litellm_params", {})
            model_spec = params.get("model", "")

            # Parse provider from model spec (e.g., "gemini/gemini-2.5-flash")
            if "/" in model_spec:
                provider_backend, model_id = model_spec.split("/", 1)
            else:
                continue

            # Map backend to provider_id
            provider_map = {
                "gemini": "gemini",
                "groq": "groq",
                "mistral": "mistral",
                "openrouter": "openrouter",
                "openai": "z.ai",  # z.ai uses openai-compatible API
                "cerebras": "cerebras",
            }
            provider_id = provider_map.get(provider_backend)

            if not provider_id:
                continue

            # Check if provider is configured
            is_configured = self._check_provider_configured(provider_id)

            if task_type not in task_providers:
                task_providers[task_type] = []

            task_providers[task_type].append((provider_id, model_id, is_configured))

        # Build routing entries
        entries = []
        for task_type in ["fast", "reason", "batch", "code", "embed"]:
            providers = task_providers.get(task_type, [])

            # Filter to configured providers
            configured = [(p, m) for p, m, c in providers if c]

            primary = configured[0][0] if configured else None
            fallbacks = [p for p, _ in configured[1:]] if len(configured) > 1 else []

            # Get health state
            health_states = []
            caveats = None

            for provider_id, _ in configured:
                health = self._get_provider_health(provider_id)
                if health.auth_broken:
                    health_states.append(f"{provider_id}:auth-broken")
                elif health.is_disabled:
                    health_states.append(f"{provider_id}:cooldown")
                elif health.consecutive_failures > 0:
                    health_states.append(f"{provider_id}:degraded")
                else:
                    health_states.append(f"{provider_id}:healthy")

            if not configured:
                health_state = "no-providers-configured"
                caveats = "No providers configured for this task type"
            elif all(h.endswith("auth-broken") for h in health_states):
                health_state = "all-blocked"
                caveats = "All providers have authentication errors"
            elif all(h.endswith("cooldown") for h in health_states):
                health_state = "all-cooldown"
                caveats = "All providers in cooldown"
            else:
                health_state = "mixed"

            # Get eligible models
            eligible_models = []
            for provider_id, model_id in configured:
                provider_config = KNOWN_PROVIDERS.get(provider_id, {})
                for m in provider_config.get("models", []):
                    if m["id"] == model_id:
                        eligible_models.append(
                            ModelInfo(
                                id=model_id,
                                name=m["name"],
                                provider=provider_id,
                                task_types=m["task_types"],
                                is_available=True,
                            )
                        )

            entry = RoutingEntry(
                task_type=task_type,
                task_label=TASK_TYPE_LABELS.get(task_type, task_type),
                primary_provider=primary,
                fallback_chain=fallbacks,
                eligible_models=eligible_models,
                health_state=health_state,
                caveats=caveats,
            )
            entries.append(entry)

        return entries

    def refresh(self) -> dict:
        """Force a refresh of provider discovery and health.

        Called by settings_service when API keys change.
        """
        self._last_refresh = time.time()

        # Re-check all providers
        providers = self.discover_providers()

        # Persist status
        status = {
            "refreshed_at": datetime.utcnow().isoformat(),
            "providers": {p.id: asdict(p) for p in providers},
            "routing": [asdict(r) for r in self.get_routing_config()],
        }

        PROVIDER_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROVIDER_STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2, default=str)

        logger.info("Provider refresh completed: %d providers", len(providers))

        return {
            "success": True,
            "providers_count": len(providers),
            "configured_count": sum(1 for p in providers if p.is_configured),
            "healthy_count": sum(1 for p in providers if p.is_healthy),
        }

    def get_health_tracker(self) -> HealthTracker:
        """Get the health tracker instance."""
        return self.health_tracker

    def get_registry(self) -> ProviderRegistry:
        """Get the provider registry instance."""
        return get_provider_registry()

    def generate_routing_from_registry(self) -> list[dict]:
        """Generate routing config from provider registry.

        P115: Deterministic routing config generation.
        """
        registry = get_provider_registry()
        return registry.generate_routing_config(KNOWN_PROVIDERS)

    def get_merged_catalog(self) -> list[ModelInfo]:
        """Get model catalog merging built-in and registry providers.

        P115: Unified catalog for UI display.
        """
        registry = get_provider_registry()
        merged = registry.merge_with_builtin(KNOWN_PROVIDERS)

        models = []
        for provider in merged:
            if not provider.enabled:
                continue
            for model in provider.models:
                if model.is_available:
                    models.append(
                        ModelInfo(
                            id=model.id,
                            name=model.name,
                            provider=provider.provider_id,
                            task_types=model.task_types,
                            is_available=True,
                        )
                    )
        return sorted(models, key=lambda m: m.id)


# ── Public API ──────────────────────────────────────────────────────────────

_provider_service: ProviderService | None = None


def get_provider_service() -> ProviderService:
    """Get or create the provider service singleton."""
    global _provider_service
    if _provider_service is None:
        _provider_service = ProviderService()
    return _provider_service


def trigger_provider_refresh(key_name: str) -> None:
    """Trigger a provider refresh when LLM keys change.

    Called by settings_service._trigger_provider_refresh() from P81.
    """
    llm_providers = {
        "GEMINI_API_KEY": "gemini",
        "GROQ_API_KEY": "groq",
        "MISTRAL_API_KEY": "mistral",
        "OPENROUTER_API_KEY": "openrouter",
        "CEREBRAS_API_KEY": "cerebras",
        "ZAI_API_KEY": "z.ai",
    }

    if key_name in llm_providers:
        logger.info("Provider refresh triggered by %s change", key_name)
        service = get_provider_service()
        result = service.refresh()
        logger.info("Provider refresh result: %s", result)
