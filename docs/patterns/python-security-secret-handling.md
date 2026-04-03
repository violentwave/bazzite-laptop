---
language: python
domain: security
type: pattern
title: Secret handling in environment variables
tags: secrets, environment-variables, config-management, security
---

# Secure Secret Handling

Never hardcode secrets. This pattern shows how to safely load and manage API keys, passwords, and other sensitive values.

## Environment Variable Loading

```python
import os
from pathlib import Path

def get_secret(name: str, default: str | None = None) -> str | None:
    """Get secret from environment, with validation."""
    value = os.environ.get(name, default)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value

def require_secret(name: str) -> str:
    """Get secret or raise if missing."""
    value = get_secret(name)
    if value is None:
        raise ValueError(f"Required secret {name} not set")
    return value
```

## Structured Secret Files

For complex secrets, use structured formats:

```python
import json
from pathlib import Path

def load_secrets_file(path: Path) -> dict:
    """Load secrets from JSON file (not in version control)."""
    if not path.exists():
        raise FileNotFoundError(f"Secrets file not found: {path}")
    
    with open(path) as f:
        secrets = json.load(f)
    
    for key, value in secrets.items():
        os.environ[key] = value
    
    return secrets
```

## Secret Validation at Startup

```python
def validate_secrets() -> list[str]:
    """Validate required secrets are present. Returns list of missing keys."""
    required = [
        "GEMINI_API_KEY",
        "VT_API_KEY",
        "OPENROUTER_API_KEY",
    ]
    missing = []
    for key in required:
        if not get_secret(key):
            missing.append(key)
    return missing

def init_secrets() -> None:
    """Initialize and validate all secrets at application start."""
    missing = validate_secrets()
    if missing:
        raise RuntimeError(f"Missing required secrets: {', '.join(missing)}")
```

## Using a Config Object

```python
from dataclasses import dataclass

@dataclass
class AppConfig:
    gemini_key: str
    vt_key: str
    log_level: str
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            gemini_key=require_secret("GEMINI_API_KEY"),
            vt_key=require_secret("VT_API_KEY"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

config = AppConfig.from_env()
```

## Best Practices

1. **Never commit secrets**: Add `*.env`, `secrets.json` to `.gitignore`
2. **Rotate secrets**: Change API keys periodically
3. **Scope permissions**: Use minimal required permissions
4. **Audit access**: Log when secrets are accessed
5. **Use vaults**: For production, consider HashiCorp Vault or AWS Secrets Manager

This pattern ensures secrets are managed securely without hardcoding.