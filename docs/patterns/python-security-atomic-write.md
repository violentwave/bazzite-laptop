---
language: python
domain: security
type: pattern
title: Atomic file write with tempfile
tags: atomic-write, file-safety, crash-safe, filesystem
---

# Atomic File Writes with Temporary Files

When writing critical configuration files or state data, a sudden crash or power loss can leave you with a corrupted or partially written file. This pattern ensures your writes are atomic—either they complete fully, or the original file remains untouched.

## The Problem

Direct file writes are not atomic. If your process is killed mid-write, you end up with a partial file:

```python
# DANGEROUS: Not atomic
with open("/etc/app/config.json", "w") as f:
    json.dump(config, f)
```

A crash during this write could leave you with a truncated JSON file that fails to parse on next load.

## The Solution: Write to Temp File + Atomic Rename

Write to a temporary file in the same filesystem, then atomically rename it to replace the target:

```python
import os
import tempfile
import json
from pathlib import Path

def atomic_write(path: Path, data: str) -> None:
    """Write data atomically using tempfile + rename."""
    path = Path(path)
    directory = path.parent
    
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=directory,
        delete=False,
    ) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    
    try:
        os.replace(tmp_path, path)  # Atomic on POSIX
    except Exception:
        os.unlink(tmp_path)
        raise

def atomic_json_write(path: Path, obj: dict) -> None:
    """Write JSON data atomically."""
    data = json.dumps(obj, indent=2)
    atomic_write(path, data)
```

## Why This Works

1. **Temporary file in same directory**: Ensures `os.replace()` works (same filesystem required for atomic rename)
2. **`delete=False` + manual cleanup**: We control when the temp file is deleted
3. **`os.replace()`**: Atomic on POSIX systems — either succeeds completely or fails, no partial state

## Real-World Usage in Bazzite AI

This pattern is used in the MCP bridge for writing allowlists and rate limit configs:

```python
# From ai/rate_limiter.py
def _persist_state(path: Path, data: dict) -> None:
    """Persist rate limit state atomically."""
    content = json.dumps(data, indent=2)
    path = Path(path)
    
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    os.replace(tmp_path, path)
```

## Edge Cases

- **Different filesystems**: `os.replace()` fails if temp and target are on different mounts
- **Large files**: Use streaming writes for files that won't fit in memory
- **Permissions**: Ensure the directory is writable and allows file creation

## Testing

```python
import pytest
from pathlib import Path
import json

def test_atomic_write_replaces_file(tmp_path):
    target = tmp_path / "config.json"
    original = {"key": "value"}
    
    atomic_json_write(target, original)
    
    with open(target) as f:
        assert json.load(f) == original
```

This pattern gives you crash-safe writes without complex file locking.