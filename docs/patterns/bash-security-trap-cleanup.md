---
language: bash
domain: security
type: pattern
title: Trap cleanup on exit
tags: bash, trap, cleanup, exit-handler, signal-handler
---

# Trap Cleanup on Exit

Use traps to ensure cleanup runs even when scripts fail or are interrupted.

## Basic Cleanup Trap

```bash
#!/usr/bin/env bash
set -euo pipefail

TEMP_FILES=()

cleanup() {
    echo "Cleaning up..."
    for file in "${TEMP_FILES[@]}"; do
        rm -f "$file" 2>/dev/null || true
    done
}

trap cleanup EXIT
```

## Signal Handling

```bash
#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    echo "Caught signal, shutting down gracefully..."
    # Stop background processes
    kill $BACKGROUND_PID 2>/dev/null || true
    # Remove temp files
    rm -f /tmp/script-$$
    exit 130
}

trap cleanup SIGINT SIGTERM
```

## Multiple Traps

```bash
#!/usr/bin/env bash
set -euo pipefail

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Script finished"
}

cleanup() {
    local exit_code=$?
    echo "Exit code: $exit_code"
    # Cleanup temp files
    rm -f /tmp/data-*.tmp
    log_message
    exit $exit_code
}

trap cleanup EXIT
```

## Context-Specific Cleanup

```bash
#!/usr/bin/env bash
set -euo pipefail

setup_temp_files() {
    local tmp1=$(mktemp)
    local tmp2=$(mktemp)
    TEMP_FILES+=("$tmp1" "$tmp2")
}

# Use a flag to track if setup succeeded
SETUP_DONE=false

setup() {
    setup_temp_files
    SETUP_DONE=true
}

cleanup() {
    if [[ "$SETUP_DONE" == "true" ]]; then
        rm -f "${TEMP_FILES[@]}" 2>/dev/null || true
    fi
}

trap cleanup EXIT

setup
# ... rest of script
```

## Resource Lock Cleanup

```bash
#!/usr/bin/env bash
LOCK_FILE="/tmp/app.lock"

acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        echo "Already running"
        exit 1
    fi
    echo $$ > "$LOCK_FILE"
}

cleanup() {
    rm -f "$LOCK_FILE"
}

trap cleanup EXIT

acquire_lock
# ... main work
```

## Nested Cleanup

```bash
#!/usr/bin/env bash

main() {
    local tmpdir=$(mktemp -d)
    
    # Cleanup function specific to this function
    local cleanup_temp
    cleanup_temp() {
        rm -rf "$tmpdir"
    }
    trap cleanup_temp EXIT
    
    # Work with temp directory
    echo "Working in $tmpdir"
}
```

This pattern ensures resources are always cleaned up properly.