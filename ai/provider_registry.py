"""Provider Registry — Durable storage for custom providers.

P115 — Provider Registry + Routing Persistence v2

Provides:
- JSON-based registry for custom provider metadata
- CRUD operations for provider records
- Credential reference handling (never stores secrets)
- Validation of provider configs
- Deterministic routing config generation
- Redaction of sensitive fields

Built-in providers come from provider_service.py KNOWN_PROVIDERS.
Registry adds custom providers and override/disable state.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.config import APP_NAME

logger = logging.getLogger(APP_NAME)

SECURITY_DIR = Path.home() / "security"
REGISTRY_FILE = SECURITY_DIR / "provider-registry.json"
REGISTRY_BACKUP = SECURITY_DIR / "provider-registry.json.bak"

VALID_PROVIDER_TYPES = {
    "openai_compatible",
    "anthropic_compatible",
    "gemini",
    "groq",
    "mistral",
    "openrouter",
    "z_ai",
    "cerebras",
    "ollama",
}

VALID_TASK_TYPES = {"fast", "reason", "batch", "code", "embed"}


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, "utf-8")
    if path.exists():
        shutil.copystat(path, tmp)
    tmp.replace(path)


def _safe_provider_id(provider_id: str) -> str:
    if not re.match(r"^[a-z][a-z0-9_-]*$", provider_id):
        raise ValueError(
            f"Invalid provider_id: {provider_id!r}. "
            "Must be lowercase, start with letter, contain only a-z0-9_-"
        )
    return provider_id


def _validate_no_secrets(value: str) -> None:
    secret_patterns = [
        r"sk-[-a-zA-Z0-9]{20,}",
        r"sk_live[-a-zA-Z0-9]{20,}",
        r"xox[baprs]-[0-9]{10,}",
        r"AIza[_-][a-zA-Z0-9_-]{30,}",
    ]
    for pattern in secret_patterns:
        if re.search(pattern, value):
            raise ValueError("Potential secret detected in value")


@dataclass
class ModelCatalogEntry:
    id: str
    name: str
    task_types: list[str]
    is_available: bool = True


@dataclass
class ProviderRecord:
    provider_id: str
    display_name: str
    provider_type: str
    base_url: str | None = None
    enabled: bool = True
    credential_ref: str | None = None
    models: list[ModelCatalogEntry] = field(default_factory=list)
    routing_metadata: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    health_status: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_type": self.provider_type,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "credential_ref": self.credential_ref,
            "models": [asdict(m) for m in self.models],
            "routing_metadata": self.routing_metadata,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "health_status": self.health_status,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProviderRecord:
        models = [ModelCatalogEntry(**m) for m in data.get("models", [])]
        return cls(
            provider_id=data["provider_id"],
            display_name=data["display_name"],
            provider_type=data["provider_type"],
            base_url=data.get("base_url"),
            enabled=data.get("enabled", True),
            credential_ref=data.get("credential_ref"),
            models=models,
            routing_metadata=data.get("routing_metadata", {}),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            health_status=data.get("health_status"),
            last_error=data.get("last_error"),
        )


class ProviderRegistry:
    """Durable provider registry with CRUD operations."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or REGISTRY_FILE
        self._cache: dict[str, ProviderRecord] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._cache.clear()
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    data = json.load(f)
                for p in data.get("providers", []):
                    record = ProviderRecord.from_dict(p)
                    self._cache[record.provider_id] = record
            except Exception as e:
                logger.warning("Failed to load provider registry: %s", e)
        self._loaded = True

    def _save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(UTC).isoformat(),
            "providers": [p.to_dict() for p in self._cache.values()],
        }
        _atomic_write(self.registry_path, json.dumps(data, indent=2, sort_keys=True))

    def _ensure_loaded(func):
        def wrapper(self, *args, **kwargs):
            self._load()
            return func(self, *args, **kwargs)

        return wrapper

    @_ensure_loaded
    def list_providers(
        self, include_disabled: bool = False, include_builtin: bool = False
    ) -> list[ProviderRecord]:
        """List all providers, optionally including disabled or built-in."""
        result = []
        for p in self._cache.values():
            if not include_disabled and not p.enabled:
                continue
            result.append(p)
        return sorted(result, key=lambda p: (not p.enabled, p.provider_id))

    @_ensure_loaded
    def get_provider(self, provider_id: str) -> ProviderRecord | None:
        """Get a specific provider."""
        return self._cache.get(provider_id)

    @_ensure_loaded
    def create_provider(
        self,
        provider_id: str,
        display_name: str,
        provider_type: str,
        base_url: str | None = None,
        credential_ref: str | None = None,
        models: list[dict[str, Any]] | None = None,
        routing_metadata: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> ProviderRecord:
        """Create a new provider."""
        _safe_provider_id(provider_id)

        if provider_id in self._cache:
            raise ValueError(f"Provider {provider_id!r} already exists")

        if provider_type not in VALID_PROVIDER_TYPES:
            raise ValueError(
                f"Invalid provider_type: {provider_type!r}. Must be one of: {VALID_PROVIDER_TYPES}"
            )

        if provider_type in {"openai_compatible", "anthropic_compatible"} and not base_url:
            raise ValueError(f"base_url required for {provider_type!r}")

        if credential_ref:
            _validate_no_secrets(credential_ref)

        model_entries = []
        if models:
            for m in models:
                if not m.get("id"):
                    raise ValueError("Model must have id")
                model_entries.append(
                    ModelCatalogEntry(
                        id=m["id"],
                        name=m.get("name", m["id"]),
                        task_types=m.get("task_types", []),
                        is_available=m.get("is_available", True),
                    )
                )

        now = datetime.now(UTC).isoformat()
        record = ProviderRecord(
            provider_id=provider_id,
            display_name=display_name,
            provider_type=provider_type,
            base_url=base_url,
            enabled=True,
            credential_ref=credential_ref,
            models=model_entries,
            routing_metadata=routing_metadata or {},
            notes=notes,
            created_at=now,
            updated_at=now,
        )

        self._cache[provider_id] = record
        self._save()
        logger.info("Provider created: %s", provider_id)
        return record

    @_ensure_loaded
    def update_provider(
        self,
        provider_id: str,
        display_name: str | None = None,
        provider_type: str | None = None,
        base_url: str | None = None,
        credential_ref: str | None = None,
        models: list[dict[str, Any]] | None = None,
        routing_metadata: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> ProviderRecord:
        """Update an existing provider."""
        if provider_id not in self._cache:
            raise ValueError(f"Provider {provider_id!r} not found")

        record = self._cache[provider_id]

        if provider_type is not None:
            if provider_type not in VALID_PROVIDER_TYPES:
                raise ValueError(f"Invalid provider_type: {provider_type!r}")
            record.provider_type = provider_type

        if display_name is not None:
            record.display_name = display_name
        if base_url is not None:
            record.base_url = base_url
        if credential_ref is not None:
            _validate_no_secrets(credential_ref)
            record.credential_ref = credential_ref

        if models is not None:
            record.models = [
                ModelCatalogEntry(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    task_types=m.get("task_types", []),
                    is_available=m.get("is_available", True),
                )
                for m in models
            ]

        if routing_metadata is not None:
            record.routing_metadata = routing_metadata

        if notes is not None:
            record.notes = notes

        record.updated_at = datetime.now(UTC).isoformat()
        self._save()
        logger.info("Provider updated: %s", provider_id)
        return record

    @_ensure_loaded
    def disable_provider(self, provider_id: str) -> ProviderRecord:
        """Disable a provider."""
        if provider_id not in self._cache:
            raise ValueError(f"Provider {provider_id!r} not found")

        record = self._cache[provider_id]
        record.enabled = False
        record.updated_at = datetime.now(UTC).isoformat()
        self._save()
        logger.info("Provider disabled: %s", provider_id)
        return record

    @_ensure_loaded
    def enable_provider(self, provider_id: str) -> ProviderRecord:
        """Enable a provider."""
        if provider_id not in self._cache:
            raise ValueError(f"Provider {provider_id!r} not found")

        record = self._cache[provider_id]
        record.enabled = True
        record.updated_at = datetime.now(UTC).isoformat()
        self._save()
        logger.info("Provider enabled: %s", provider_id)
        return record

    def merge_with_builtin(self, builtin_providers: dict[str, Any]) -> list[ProviderRecord]:
        """Merge registry with built-in providers."""
        self._load()
        merged: list[ProviderRecord] = []

        for pid, config in builtin_providers.items():
            if pid in self._cache:
                reg_record = self._cache[pid]
                if reg_record.enabled:
                    merged.append(reg_record)
            else:
                model_entries = [
                    ModelCatalogEntry(
                        id=m["id"],
                        name=m["name"],
                        task_types=m.get("task_types", []),
                        is_available=config.get("key_env") is not None,
                    )
                    for m in config.get("models", [])
                ]
                now = datetime.now(UTC).isoformat()
                merged.append(
                    ProviderRecord(
                        provider_id=pid,
                        display_name=config["name"],
                        provider_type=pid,
                        base_url=config.get("base_url"),
                        enabled=config.get("key_env") is not None or config.get("is_local"),
                        credential_ref=config.get("key_env"),
                        models=model_entries,
                        created_at=now,
                        updated_at=now,
                    )
                )

        for reg_record in self._cache.values():
            if reg_record.provider_id not in builtin_providers:
                merged.append(reg_record)

        return sorted(merged, key=lambda p: (not p.enabled, p.provider_id))

    def generate_routing_config(
        self, builtin_providers: dict[str, Any], include_disabled: bool = False
    ) -> list[dict[str, Any]]:
        """Generate LiteLLM-compatible routing config."""
        providers = self.merge_with_builtin(builtin_providers)

        entries = []
        for record in providers:
            if not include_disabled and not record.enabled:
                continue

            for model in record.models:
                for task_type in model.task_types:
                    provider_backend = self._provider_to_backend(
                        record.provider_type, record.provider_id
                    )
                    model_id = f"{provider_backend}/{model.id}"

                    entry = {
                        "model_name": task_type,
                        "litellm_params": {
                            "model": model_id,
                        },
                    }

                    if record.credential_ref:
                        entry["litellm_params"]["api_key"] = f"os.environ/{record.credential_ref}"

                    if record.base_url:
                        entry["litellm_params"]["api_base"] = record.base_url

                    entries.append(entry)

        entries.sort(
            key=lambda e: (
                e["model_name"],
                e["litellm_params"]["model"],
            )
        )
        return entries

    def _provider_to_backend(self, provider_type: str, provider_id: str) -> str:
        """Map provider type to LiteLLM backend."""
        mapping = {
            "gemini": "gemini",
            "groq": "groq",
            "mistral": "mistral",
            "openrouter": "openrouter",
            "z_ai": "openai",
            "cerebras": "cerebras",
            "ollama": "ollama",
            "openai_compatible": "openai",
            "anthropic_compatible": "anthropic",
        }
        if provider_type in mapping:
            return mapping[provider_type]
        return provider_id

    def validate_config(self, data: dict[str, Any]) -> list[str]:
        """Validate a provider config and return errors."""
        errors = []

        provider_id = data.get("provider_id", "")
        try:
            _safe_provider_id(provider_id)
        except ValueError as e:
            errors.append(str(e))

        provider_type = data.get("provider_type")
        if provider_type not in VALID_PROVIDER_TYPES:
            errors.append(
                f"Invalid provider_type: {provider_type!r}. Must be one of: {VALID_PROVIDER_TYPES}"
            )

        base_url = data.get("base_url")
        if provider_type in {"openai_compatible", "anthropic_compatible"} and not base_url:
            errors.append("base_url required for custom providers")

        credential_ref = data.get("credential_ref")
        if credential_ref:
            try:
                _validate_no_secrets(credential_ref)
            except ValueError as e:
                errors.append(str(e))

        models = data.get("models", [])
        if not models:
            errors.append("At least one model required")
        else:
            for m in models:
                if not m.get("id"):
                    errors.append("Model missing id")
                task_types = m.get("task_types", [])
                for tt in task_types:
                    if tt not in VALID_TASK_TYPES:
                        errors.append(f"Invalid task_type: {tt}")

        return errors


_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Get or create the provider registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
