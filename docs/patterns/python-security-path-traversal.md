---
language: python
domain: security
type: pattern
title: Path traversal prevention
tags: path-traversal, directory-traversal, lfi, security, path-validation
---

# Path Traversal Prevention

Prevent directory traversal attacks that allow attackers to access files outside intended directories.

## The Vulnerability

```python
# VULNERABLE: User can escape the intended directory
# Request: /read?file=../../../etc/passwd
def vulnerable_read(filename):
    return open(f"/var/www/uploads/{filename}").read()

# Or worse:
# Request: /read?file=..%2F..%2F..%2Fetc%2Fpasswd (URL encoded)
```

## The Solution: Path Resolution

```python
from pathlib import Path

def safe_read_file(base_dir: Path, filename: str) -> str:
    """Read file safely within base directory."""
    base_dir = base_dir.resolve()
    
    # Join and resolve the target path
    target = (base_dir / filename).resolve()
    
    # Security check: target must be within base_dir
    if not target.is_relative_to(base_dir):
        raise ValueError("Path traversal attempt detected")
    
    # Now safe to read
    return target.read_text()
```

## Complete Implementation

```python
from pathlib import Path
import os

class SafeFileReader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
    
    def read(self, relative_path: str) -> str:
        """Read file relative to base directory."""
        # Normalize and resolve
        target = (self.base_dir / relative_path).resolve()
        
        # Security check
        self._verify_within_base(target)
        
        return target.read_text()
    
    def _verify_within_base(self, target: Path) -> None:
        """Verify path is within base directory."""
        try:
            target.relative_to(self.base_dir)
        except ValueError:
            raise PermissionError(
                f"Path {target} is outside base {self}"
            )
    
    def list_files(self, subdir: str = "") -> list[str]:
        """List files in subdirectory."""
        target = (self.base_dir / subdir).resolve()
        self._verify_within_base(target)
        
        if not target.is_dir():
            raise ValueError(f"Not a directory: {target}")
        
        return [f.name for f in target.iterdir()]
```

## Handling URL Encoded Paths

```python
from urllib.parse import unquote
from pathlib import Path

def parse_and_validate(base_dir: Path, user_input: str) -> Path:
    """Decode URL encoding and validate path."""
    # Decode URL encoding (e.g., %2F -> /)
    decoded = unquote(user_input)
    
    # Resolve the path
    target = (base_dir / decoded).resolve()
    
    # Check containment
    if not target.is_relative_to(base_dir):
        raise ValueError("Invalid path")
    
    return target
```

## Additional Security Measures

```python
import os

def safe_path_join(base: str, user_input: str) -> str:
    """Safe path joining with multiple checks."""
    # 1. Resolve to absolute
    base_path = os.path.abspath(base)
    
    # 2. Join paths
    joined = os.path.join(base_path, user_input)
    
    # 3. Resolve to canonical path
    canonical = os.path.realpath(joined)
    
    # 4. Verify within base
    if not canonical.startswith(base_path + os.sep):
        # Handle edge case where base is / and canonical is /
        if canonical != base_path:
            raise ValueError("Path traversal detected")
    
    return canonical
```

## Web Framework Integration

```python
from flask import Flask, request, abort
from pathlib import Path

app = Flask(__name__)
UPLOAD_DIR = Path("/var/www/uploads")

@app.route("/download/<filename>")
def download(filename):
    try:
        safe_reader = SafeFileReader(UPLOAD_DIR)
        content = safe_reader.read(filename)
        return content
    except (ValueError, PermissionError) as e:
        abort(403, description=str(e))
    except FileNotFoundError:
        abort(404)
```

## Blocklist Approach (Not Recommended Alone)

```python
import re

BLOCKED_PATTERNS = [
    r"\.\.",           # Double dot
    r"^/",             # Absolute path
    r"^\.\.",          # Relative parent
]

def contains_traversal(path: str) -> bool:
    """Check for traversal patterns (blocklist - not sufficient alone!)."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, path):
            return True
    return False

# Use WITH allowlist, not instead of allowlist!
```

## Testing

```python
import pytest

def test_path_traversal_blocked():
    reader = SafeFileReader(Path("/safe/dir"))
    
    with pytest.raises((ValueError, PermissionError)):
        reader.read("../../../etc/passwd")
    
    with pytest.raises((ValueError, PermissionError)):
        reader.read("/etc/passwd")

def test_valid_path_allowed():
    reader = SafeFileReader(Path("/safe/dir"))
    
    content = reader.read("subdir/file.txt")
    assert isinstance(content, str)
```

This pattern prevents local file inclusion vulnerabilities.