# P117 — Security + Shell Operations Hardening

## Overview

P117 verifies and documents the security and shell operator surfaces are reliable, auditable, recoverable, and clear about degraded states.

## Components Verified

### Security Panel (`ui/src/components/security/SecurityContainer.tsx`)

Error handling implemented:
- `ErrorState` component with severity levels (error/warning/info)
- `partialData` flag for degraded data scenarios
- `missingSources` display for unavailable data sources
- `operatorAction` field for required operator steps
- Severity-based color coding

State handling:
- Loading state with spinner
- Full error state with retry button
- Partial data state with unavailable source listing
- Health cluster for provider issues

### Shell Panel (`ui/src/components/shell-gateway/ShellContainer.tsx`)

Session status handling:
- Active: normal command input enabled
- Disconnected: displays "Session disconnected — terminate and create a new session"
- Error: displays "Session error — terminate and create a new session"
- Other states: displays "Session {status} — no commands accepted"

Audit visibility:
- `ShellAuditStrip` component for audit trail
- Session context display
- Status messages per session state

## Degraded State Handling

| Scenario | UI Display | Messaging |
|----------|-----------|-----------|
| No data, error | Full error state | "Security Data Unavailable" + retry |
| Partial data | Warning state | "Partial Security Data" + missing sources list |
| Session disconnected | Status message | "Session disconnected — terminate and create a new session" |
| Session error | Status message | "Session error — terminate and create a new session" |

## Blocked/Unavailable Actions

- Security scan trigger: shows error message if backend fails
- Health check trigger: shows error message if backend fails
- Command execution: disabled for non-active sessions with clear status message

## Validation

- TypeScript compile: clean
- UI build: passes
- Shell service tests: 23 passed
- Ruff: clean

## Evidence Files

- `security_runtime_state.json` - runtime state sample
- `shell_runtime_state.json` - shell state sample