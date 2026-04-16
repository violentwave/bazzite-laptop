# P115 — Provider Registry + Routing Persistence v2

## Overview

P115 creates a durable provider registry for custom providers, complementing the built-in providers from `provider_service.py KNOWN_PROVIDERS`.

## Components Created

### ai/provider_registry.py

ProviderRegistry class with:
- **CRUD Operations**: `create_provider`, `update_provider`, `disable_provider`, `enable_provider`
- **Queries**: `list_providers`, `get_provider`
- **Merging**: `merge_with_builtin` - combines built-in and custom providers
- **Generation**: `generate_routing_config` - deterministic LiteLLM config

### ai/provider_service.py Integration

Added methods:
- `get_registry()` - returns registry instance
- `generate_routing_from_registry()` - generates routing from registry
- `get_merged_catalog()` - unified model catalog

### MCP Tools Added

| Tool | Description |
|------|-------------|
| `provider.list` | List all providers (including custom) |
| `provider.create` | Create a new custom provider |
| `provider.update` | Update an existing provider |
| `provider.disable` | Disable a provider |
| `provider.enable` | Enable a disabled provider |
| `provider.generate_routing` | Generate LiteLLM routing config |

## Provider Record Schema

```python
{
    "provider_id": str,           # unique identifier
    "display_name": str,          # human-readable name
    "provider_type": str,        # openai_compatible, gemini, groq, etc.
    "base_url": str | None,      # API base URL
    "enabled": bool,            # active state
    "credential_ref": str | None, # env var name (never secret)
    "models": list[ModelCatalogEntry],
    "routing_metadata": dict,
    "notes": str | None,
    "created_at": str,
    "updated_at": str,
}
```

## Validation

- `provider_id`: lowercase, starts with letter, a-z0-9_-
- `provider_type`: must be in allowlist
- `base_url`: required for openai_compatible/anthropic_compatible
- Secrets detected and rejected inline

## Tests

`tests/test_provider_registry.py` - 22 tests covering:
- ID validation
- Secret detection
- CRUD operations
- Merging with built-in providers
- Deterministic routing generation

## Evidence

- `docs/evidence/p115/provider_registry_sample.json`
- `docs/evidence/p115/routing_generation_sample.json`

## P114 Parity

Updated MCP allowlist (`configs/mcp-bridge-allowlist.yaml`) with 6 new provider registry tools.