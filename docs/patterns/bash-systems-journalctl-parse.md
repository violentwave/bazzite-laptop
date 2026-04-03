---
language: bash
domain: systems
type: pattern
title: Parsing journalctl output
tags: bash, journalctl, log-parsing, systemd-logs, syslog
---

# Parsing journalctl Output

Extract and process systemd journal logs programmatically.

## Basic Usage

```bash
#!/usr/bin/env bash

# Get recent logs for a service
journalctl -u bazzite-mcp-bridge -n 100

# Get logs since specific time
journalctl -u bazzite-mcp-bridge --since "1 hour ago"
journalctl -u bazzite-mcp-bridge --since "2026-04-01 10:00:00"

# Filter by priority
journalctl -p err -u bazzite-mcp-bridge
```

## JSON Output for Parsing

```bash
#!/usr/bin/env bash

# Get logs in JSON format (easy to parse)
logs=$(journalctl -u bazzite-mcp-bridge -o json --no-pager | head -n 50)

# Parse with jq
journalctl -u bazzite-mcp-bridge -o json --no-pager | \
    jq -r '.timestamp + " " + .message' | \
    head -n 10

# Extract specific fields
journalctl -u bazzite-mcp-bridge -o json --no-pager | \
    jq -r 'select(.PRIORITY == "3") | .MESSAGE'
```

## Grep-Friendly Output

```bash
#!/usr/bin/env bash

# Concise format for piping to grep
journalctl -u bazzite-mcp-bridge -o short-iso

# Show only message (for piping)
journalctl -u bazzite-mcp-bridge -o cat

# Line prefix format
journalctl -u bazzite-mcp-bridge -o short
```

## Error Counting

```bash
#!/usr/bin/env bash

count_errors() {
    local service=$1
    local since=${2:-24h}
    
    journalctl -u "$service" -p err --since "$since" --no-pager | \
        wc -l
}

# Usage
error_count=$(count_errors "bazzite-mcp-bridge" "1 hour ago")
echo "Errors in last hour: $error_count"
```

## Recent Crash Detection

```bash
#!/usr/bin/env bash

check_recent_crashes() {
    local service=$1
    
    journalctl -u "$service" -p err --since "1 hour ago" --no-pager | \
        grep -i "exception\|error\|failed" | \
        tail -n 20
}

# Show last 5 errors
journalctl -u bazzite-mcp-bridge -p err -n 5 --no-pager
```

## Continuous Monitoring

```bash
#!/usr/bin/env bash

# Follow logs in real-time
journalctl -u bazzite-mcp-bridge -f

# Follow with filter
journalctl -u bazzite-mcp-bridge -f | grep -i error
```

## Boot-Specific Logs

```bash
#!/usr/bin/env bash

# Get logs from specific boot
journalctl -b -u bazzite-mcp-bridge

# List boots
journalctl --list-boots

# Get logs from previous boot
journalctl -b -1 -u bazzite-mcp-bridge
```

## Service Health Check

```bash
#!/usr/bin/env bash

service_health() {
    local service=$1
    
    echo "=== Health check for $service ==="
    
    # Check if active
    if systemctl is-active --quiet "$service"; then
        echo "Status: ACTIVE"
    else
        echo "Status: INACTIVE"
    fi
    
    # Recent errors
    echo "Recent errors:"
    journalctl -u "$service" -p err -n 5 --no-pager
    
    # Last start time
    echo "Last started:"
    journalctl -u "$service -b -n 1 --no-pager" | \
        grep "Started $service"
}
```

This pattern enables effective log analysis and monitoring.