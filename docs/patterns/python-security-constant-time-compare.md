---
language: python
domain: security
type: pattern
title: Constant-time comparison for secrets
tags: constant-time, timing-attack, secrets-comparison, hmac, security
---

# Constant-Time Comparison for Secrets

Prevent timing attacks by using constant-time comparison for sensitive values like API keys and passwords.

## The Problem: Timing Attacks

```python
# VULNERABLE: Timing leak reveals which characters match
def vulnerable_compare(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
    return True

# Attacker can measure response time to guess each character:
# "A" takes slightly longer than "a" if first char matches
```

## The Solution: Constant-Time Comparison

```python
import hmac

def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings in constant time."""
    return hmac.compare_digest(a, b)

def constant_time_compare_str(a: str, b: str) -> bool:
    """Compare two strings in constant time."""
    return hmac.compare_digest(a.encode(), b.encode())
```

## Using with Secrets

```python
import hashlib
import hmac

def verify_api_key(request_key: str, stored_key_hash: str) -> bool:
    """Verify API key without timing leak."""
    # Hash the provided key
    provided_hash = hashlib.sha256(request_key.encode()).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(provided_hash, stored_key_hash)

def verify_hmac(message: bytes, signature: bytes, secret: bytes) -> bool:
    """Verify HMAC signature in constant time."""
    expected = hmac.new(secret, message, hashlib.sha256).digest()
    return hmac.compare_digest(signature, expected)
```

## Password Verification

```python
import hashlib
import hmac

def verify_password(provided: str, stored_hash: str) -> bool:
    """Verify password using constant-time comparison."""
    provided_hash = hashlib.pbkdf2_hmac(
        "sha256",
        provided.encode(),
        salt=b"fixed_salt",  # In practice, use unique salt per user
        iterations=100000,
    ).hex()
    
    return hmac.compare_digest(provided_hash, stored_hash)

# Using bcrypt (recommended for passwords)
import bcrypt

def verify_bcrypt_password(provided: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(
        provided.encode(),
        stored_hash.encode(),
    )
```

## Custom Constant-Time Implementation

```python
def constant_time_bytes_compare(a: bytes, b: bytes) -> bool:
    """Compare bytes in constant time. Manual implementation."""
    if len(a) != len(b):
        # Still do comparison to avoid length leak
        a = a + b  # Pad to same length
        b = b + a[:len(a)-len(b)]
    
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    
    return result == 0
```

## API Key Validation

```python
import hmac

ALLOWED_API_KEYS = {
    "key1": "hash1...",
    "key2": "hash2...",
}

def validate_api_key(key: str) -> bool:
    """Validate API key without leaking which keys exist."""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    # Compare against ALL allowed keys (prevents enumeration)
    for allowed_hash in ALLOWED_API_KEYS.values():
        if hmac.compare_digest(key_hash, allowed_hash):
            return True
    
    return False
```

## Token Validation

```python
import hmac
import hashlib
import time

def create_token(data: str, secret: str) -> str:
    """Create a signed token."""
    payload = f"{data}.{time.time()}"
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"

def verify_token(token: str, secret: str, max_age: int = 3600) -> bool:
    """Verify token with constant-time comparison."""
    try:
        data, timestamp, signature = token.rsplit(".", 2)
        
        # Verify signature in constant time
        expected = hmac.new(
            secret.encode(),
            f"{data}.{timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return False
        
        # Check expiry
        if time.time() - float(timestamp) > max_age:
            return False
        
        return True
    except ValueError:
        return False
```

This pattern prevents timing-based secret leakage.