---
language: python
domain: security
type: pattern
title: Rate limiting with token bucket
tags: rate-limiting, token-bucket, throttling, security
---

# Rate Limiting with Token Bucket

Protect your APIs from abuse with token bucket rate limiting. This pattern provides smooth rate limiting with burst capability.

## The Token Bucket Algorithm

```
Tokens fill at rate R per second
Bucket capacity = B tokens
Request consumes 1 token
If bucket empty -> request denied
```

## Implementation

```python
import time
import threading
from dataclasses import dataclass
from typing import Callable

@dataclass
class RateLimitConfig:
    rate: float      # tokens per second
    capacity: int    # bucket capacity
    burst: int       # max burst size

class TokenBucket:
    def __init__(self, config: RateLimitConfig):
        self.rate = config.rate
        self.capacity = config.capacity
        self.burst = config.burst
        self.tokens = float(config.burst)
        self.last_update = time.monotonic()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if allowed."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    def __init__(self):
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = threading.Lock()
    
    def allow(self, key: str, config: RateLimitConfig) -> bool:
        """Check if request is allowed."""
        with self.lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(config)
            return self.buckets[key].consume()
```

## Usage

```python
# Configure: 10 requests/sec with burst of 20
config = RateLimitConfig(rate=10.0, capacity=20, burst=20)
limiter = RateLimiter()

@app.route("/api/data")
def get_data():
    client_id = request.headers.get("X-Client-ID", "default")
    if not limiter.allow(client_id, config):
        return {"error": "Rate limit exceeded"}, 429
    return {"data": "..."}
```

## Distributed Rate Limiting

For multi-instance deployments, use Redis:

```python
import redis

class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url)
    
    def allow(self, key: str, limit: int, window: int) -> bool:
        """Atomic rate limit check using Redis."""
        now = time.time()
        window_start = now - window
        
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        
        results = pipe.execute()
        return results[2] <= limit
```

## Integration with MCP Bridge

The Bazzite AI MCP bridge uses this pattern:

```python
# From ai/rate_limiter.py
def can_call(self, scope: str) -> bool:
    """Check if call is allowed under rate limits."""
    config = self._get_config(scope)
    return self._buckets[scope].consume()
```

This pattern provides flexible, accurate rate limiting for any service.