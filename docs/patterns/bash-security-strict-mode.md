---
language: bash
domain: security
type: pattern
title: Strict mode for bash scripts
tags: bash, strict-mode, set -e, set -u, error-handling
---

# Strict Mode for Bash Scripts

Enable strict mode to catch errors early and write more robust shell scripts.

## Basic Strict Mode

```bash
#!/usr/bin/env bash
set -euo pipefail

# -e: Exit on error
# -u: Exit on undefined variable
# -o pipefail: Pipeline fails if any command fails
```

## Why Each Flag Matters

- `set -e`: Script exits immediately when a command returns non-zero
- `set -u`: Script exits when using an undefined variable
- `set -o pipefail`: Pipeline returns failure if any command fails (not just the last)

## Practical Example

```bash
#!/usr/bin/env bash
set -euo pipefail

# Fail on undefined variables
echo "Running with user: ${USER:?USER must be set}"
echo "Home directory: ${HOME}"

# Fail on command failure
rm -rf /tmp/old-cache
curl -sS "https://api.example.com/data" > data.json

# Pipeline fails properly
cat data.json | jq ".items" | head -n 5
```

## Disabling Strict Mode Temporarily

```bash
set +e  # Disable exit on error
some_command_that_might_fail || true
set -e  # Re-enable

# Or for a single command:
command_that_might_fail || true
```

## Local Scoping

```bash
# Disable strict mode in a subshell
(
    set +e
    might_fail_command
)
# Back to strict mode automatically

# Or with background processes
set -e
(
    might_fail
) || true  # Handle failure
```

## Error Trapping

```bash
set -euo pipefail

cleanup() {
    echo "Cleaning up..."
    # Remove temp files
    rm -f /tmp/script-*
}

trap cleanup EXIT

# Now if anything fails, cleanup still runs
```

## Debugging with Strict Mode

```bash
set -euo pipefail
set -x  # Enable debug output

# Each command prints before executing
some_command
another_command
```

This pattern prevents many common shell scripting errors.