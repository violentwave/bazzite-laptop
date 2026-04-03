---
language: yaml
domain: systems
type: pattern
title: Rate limit configuration
tags: rate-limiting, configuration, nginx, api-gateway
---

# Rate Limit Configuration

Configure rate limiting in various systems using YAML configuration.

## Simple Rate Limit Config

```yaml
# rate-limits.yaml
default:
  requests_per_second: 10
  burst: 20

api:
  requests_per_second: 100
  burst: 200

login:
  requests_per_second: 5
  burst: 10
```

## Nginx Rate Limiting

```nginx
http {
    # Define zones
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=login:5r/s;

    server {
        location / {
            limit_req zone=general burst=20;
        }

        location /api/ {
            limit_req zone=api burst=200;
        }

        location /login {
            limit_req zone=login burst=10;
        }
    }
}
```

## Python Rate Limiter Config

```yaml
# ai-rate-limits.yaml
limits:
  gemini_embed:
    requests_per_minute: 60
    requests_per_hour: 1500
  
  gemini_chat:
    requests_per_minute: 15
    requests_per_hour: 500
  
  openrouter:
    requests_per_minute: 30
    requests_per_hour: 1000

  cohere:
    requests_per_minute: 100
    requests_per_hour: 5000
```

## API Gateway Rate Limit

```yaml
# kong declarative config
services:
  - name: my-api
    url: http://backend:8080
    routes:
      - name: my-route
        paths:
          - /api
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000
          policy: local
          fault_tolerant: true

  - name: login-api
    url: http://backend:8080/login
    routes:
      - name: login-route
        paths:
          - /login
    plugins:
      - name: rate-limiting
        config:
          minute: 10
          hour: 100
          policy: local
```

## Distributed Rate Limit with Redis

```yaml
# redis-rate-limit.yaml
redis:
  host: localhost
  port: 6379
  db: 0

limits:
  default:
    key_prefix: "ratelimit:"
    max_requests: 100
    window_seconds: 60
  
  authenticated:
    key_prefix: "ratelimit:user:"
    max_requests: 1000
    window_seconds: 60
```

## Programmatic Usage

```python
import yaml
from pathlib import Path

def load_rate_limits(path: Path) -> dict:
    """Load rate limit configuration."""
    with open(path) as f:
        return yaml.safe_load(f)

config = load_rate_limits(Path("ai-rate-limits.yaml"))

def get_limit(provider: str) -> tuple[int, int]:
    """Get (requests_per_minute, requests_per_hour) for provider."""
    limits = config["limits"].get(provider, config["limits"]["default"])
    return limits["requests_per_minute"], limits["requests_per_hour"]
```

## IP-Based Limits

```yaml
# ip-rate-limits.yaml
ip_limits:
  "127.0.0.1":
    requests_per_second: 100
    burst: 200
  
  "10.0.0.0/8":
    requests_per_second: 10
    burst: 20

  # Whitelist
  whitelist:
    - "192.168.1.0/24"
```

This pattern enables flexible, configurable rate limiting.