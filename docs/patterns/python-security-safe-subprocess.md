---
language: python
domain: security
type: pattern
title: Safe subprocess execution
tags: subprocess, shell-injection, command-injection, security
---

# Safe Subprocess Execution

Never pass unsanitized user input to subprocess commands. This pattern shows how to execute external commands safely.

## The Danger: Shell Injection

```python
# DANGEROUS: User input directly in command
filename = request.args.get("filename")
os.system(f"cat /var/data/{filename}")  # Injection via ../../../etc/passwd
```

## Safe Alternative: shell=False + List Args

```python
import subprocess

def safe_cat(filename: str) -> str:
    """Safely read a file using subprocess."""
    # Pass args as list, not string - prevents shell injection
    result = subprocess.run(
        ["cat", filename],
        capture_output=True,
        text=True,
        shell=False,  # Critical: don't use shell
        timeout=5,
    )
    return result.stdout
```

## Validating File Paths

```python
from pathlib import Path

def safe_read_file(base_dir: Path, filename: str) -> str:
    """Read file only if it's within base directory."""
    base_dir = base_dir.resolve()
    
    # Resolve the requested path
    target = (base_dir / filename).resolve()
    
    # Security check: must be within base_dir
    if not target.is_relative_to(base_dir):
        raise ValueError("Path traversal attempt detected")
    
    return target.read_text()
```

## Allowed Command List

```python
ALLOWED_COMMANDS = {"systemctl", "journalctl", "ps", "ls", "cat"}

def safe_systemctl(action: str, service: str) -> str:
    """Execute systemctl only for allowed actions."""
    if action not in {"start", "stop", "status", "restart", "enable", "disable"}:
        raise ValueError(f"Disallowed action: {action}")
    
    result = subprocess.run(
        ["systemctl", action, service],
        capture_output=True,
        text=True,
        shell=False,
        timeout=30,
    )
    return result.stdout
```

## Using shutil for Common Operations

```python
import shutil

# Instead of subprocess for file operations
def copy_file(src: Path, dst: Path) -> None:
    shutil.copy2(src, dst)  # Safer than os.system("cp ...")

def list_directory(path: Path) -> list[str]:
    return [f.name for f in path.iterdir()]  # Safer than ls
```

## Timeout and Resource Limits

```python
def run_command_safe(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run command with timeout and limits."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
        # Limit subprocess resources
        # On Linux: use resource module to limit memory, CPU
    )
```

## Logging for Audit Trail

```python
import logging

logger = logging.getLogger(__name__)

def audited_command(args: list[str]) -> str:
    """Run command with audit logging."""
    logger.info("Executing command: %s", " ".join(args))
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        shell=False,
    )
    logger.info("Command exit code: %d", result.returncode)
    return result.stdout
```

This pattern prevents command injection while maintaining functionality.