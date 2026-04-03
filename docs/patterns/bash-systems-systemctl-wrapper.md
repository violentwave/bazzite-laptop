---
language: bash
domain: systems
type: pattern
title: systemctl wrapper for service management
tags: bash, systemctl, systemd, service-management, wrapper
---

# systemctl Wrapper for Service Management

Create reusable bash functions for common systemd operations.

## Basic Wrapper Functions

```bash
#!/usr/bin/env bash

is_service_active() {
    local service=$1
    systemctl is-active --quiet "$service" 2>/dev/null
}

is_service_enabled() {
    local service=$1
    systemctl is-enabled --quiet "$service" 2>/dev/null
}

service_status() {
    local service=$1
    systemctl status "$service" --no-pager
}

service_start() {
    local service=$1
    systemctl start "$service"
}

service_stop() {
    local service=$1
    systemctl stop "$service"
}

service_restart() {
    local service=$1
    systemctl restart "$service"
}
```

## Safe Service Management

```bash
#!/usr/bin/env bash
set -euo pipefail

ensure_service() {
    local service=$1
    local action=${2:-start}  # start, restart, or nothing
    
    if ! systemctl list-unit-files | grep -q "^$service"; then
        echo "Service $service does not exist"
        return 1
    fi
    
    case $action in
        start)
            systemctl start "$service"
            echo "Started $service"
            ;;
        restart)
            systemctl restart "$service"
            echo "Restarted $service"
            ;;
        *)
            echo "Service $service exists"
            ;;
    esac
}

wait_for_service() {
    local service=$1
    local timeout=${2:-30}
    
    for i in $(seq 1 $timeout); do
        if systemctl is-active --quiet "$service"; then
            return 0
        fi
        sleep 1
    done
    echo "Timeout waiting for $service"
    return 1
}
```

## Service Log Viewing

```bash
#!/usr/bin/env bash

service_logs() {
    local service=$1
    local lines=${2:-50}
    journalctl -u "$service" -n "$lines" --no-pager
}

service_logs_follow() {
    local service=$1
    journalctl -u "$service" -f --no-pager
}

service_logs_since() {
    local service=$1
    local since=${2:-1 hour ago}
    journalctl -u "$service" --since "$since" --no-pager
}
```

## Bulk Operations

```bash
#!/usr/bin/env bash

restart_all_app_services() {
    for svc in bazzite-llm-proxy bazzite-mcp-bridge; do
        echo "Restarting $svc..."
        systemctl restart "$svc" || echo "Failed: $svc"
    done
}

stop_all_app_services() {
    for svc in bazzite-mcp-bridge bazzite-llm-proxy; do
        echo "Stopping $svc..."
        systemctl stop "$svc" || echo "Failed: $svc"
    done
}

get_service_status() {
    local service=$1
    echo "=== $service ==="
    systemctl is-active "$service" || true
    systemctl is-enabled "$service" || true
}
```

## Error Handling

```bash
#!/usr/bin/env bash

run_or_fail() {
    local msg=$1
    shift
    if ! "$@"; then
        echo "ERROR: $msg" >&2
        return 1
    fi
}

restart_service_safe() {
    local service=$1
    run_or_fail "Failed to restart $service" systemctl restart "$service"
    wait_for_service "$service" 10
}
```

This pattern provides safe, consistent service management.