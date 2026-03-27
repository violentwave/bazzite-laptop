#!/usr/bin/env bash
# newelle-sudo.sh — run allowlisted system commands with appropriate privilege
# Usage: newelle-sudo.sh <command> [args...]
# Example: newelle-sudo.sh systemctl start system-health.service
set -euo pipefail

# Allowlist format: "<full command string>" -> "system" or "user"
# system = requires sudo; user = systemctl --user, no sudo
declare -A ALLOWED_COMMANDS=(
    ["systemctl start system-health.service"]="system"
    ["systemctl start clamav-quick.service"]="system"
    ["systemctl start clamav-deep.service"]="system"
    ["systemctl restart bazzite-llm-proxy.service"]="user"
    ["systemctl restart bazzite-mcp-bridge.service"]="user"
)

if [[ $# -eq 0 ]]; then
    echo "Usage: $(basename "$0") <command> [args...]" >&2
    exit 1
fi

FULL_CMD="$*"

if [[ -z "${ALLOWED_COMMANDS[$FULL_CMD]+x}" ]]; then
    echo "Error: command not in allowlist: ${FULL_CMD}" >&2
    echo "Allowed commands:" >&2
    for cmd in "${!ALLOWED_COMMANDS[@]}"; do
        echo "  ${cmd}" >&2
    done
    exit 1
fi

SERVICE_TYPE="${ALLOWED_COMMANDS[$FULL_CMD]}"

if [[ "${SERVICE_TYPE}" == "user" ]]; then
    # User services — no sudo, inject --user flag after "systemctl"
    exec systemctl --user "${@:2}"
else
    exec sudo systemctl "${@:2}"
fi
