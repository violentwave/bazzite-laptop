---
language: bash
domain: security
type: pattern
title: Safe temporary file handling
tags: bash, tempfile, mktemp, security, safe-temp-files
---

# Safe Temporary File Handling

Create secure temporary files and directories that don't expose you to race conditions or symlink attacks.

## Using mktemp

```bash
#!/usr/bin/env bash
set -euo pipefail

# Create a temporary file (fails if can't create)
tmpfile=$(mktemp)
echo "Temp file: $tmpfile"
# Use the file
echo "data" > "$tmpfile"
# Cleanup handled by trap

# Create a temporary directory
tmpdir=$(mktemp -d)
echo "Temp dir: $tmpdir"

# Template-based naming (secure)
tmpfile=$(mktemp /tmp/myapp-XXXXXX)
```

## Trap-Based Cleanup

```bash
#!/usr/bin/env bash
set -euo pipefail

TMPFILES=()

cleanup() {
    for f in "${TMPFILES[@]}"; do
        rm -f "$f" 2>/dev/null || true
    done
}
trap cleanup EXIT

# Add files as we create them
tmp1=$(mktemp)
TMPFILES+=("$tmp1")
tmp2=$(mktemp)
TMPFILES+=("$tmp2")
```

## Avoiding Insecure Patterns

```bash
# BAD: Race condition vulnerability
echo "data" > /tmp/file.$$  # PID can be reused

# BAD: Symlink attack possible
echo "data" > /tmp/app-log

# GOOD: mktemp creates with secure permissions
tmpfile=$(mktemp)
# Permissions: 0600 (owner read/write only)
```

## Temporary Directory in Script

```bash
#!/usr/bin/env bash
set -euo pipefail

create_temp_dir() {
    local tmpdir=$(mktemp -d)
    chmod 700 "$tmpdir"  # Ensure private
    echo "$tmpdir"
}

TMPDIR=$(create_temp_dir)
trap 'rm -rf "$TMPDIR"' EXIT

# Use the directory
echo "work" > "$TMPDIR/output.txt"
```

## Template Options

```bash
# File with extension
tmpfile=$(mktemp /tmp/app-XXXXXX.json)

# Directory with suffix
tmpdir=$(mktemp -d /tmp/cache-XXXXXX)

# No X's = just guaranteed unique
tmpfile=$(mktemp -u)  # WARNING: doesn't create file
```

## Working with User Data

```bash
#!/usr/bin/env bash
set -euo pipefail

# Safely process user-uploaded file
process_user_file() {
    local upload_path=$1
    local work_dir=$(mktemp -d)
    
    trap "rm -rf '$work_dir'" RETURN
    
    # Copy to temp location (avoids modifying upload)
    cp "$upload_path" "$work_dir/input"
    
    # Process
    process_file "$work_dir/input" > "$work_dir/output"
    
    cat "$work_dir/output"
}
```

This pattern prevents temp file security vulnerabilities.