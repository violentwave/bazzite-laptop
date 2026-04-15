# P94 Plan — Shell Gateway End-to-End Runtime Recovery

**Phase:** P94
**Objective:** Make the shell gateway usable end-to-end from the live console, with precise error states and audit/context visibility.
**Dependency:** P90 (Console Runtime Recovery)
**Risk Tier:** High
**Backend:** opencode

## Problems Found

1. **CRITICAL: `shell=True` in `execute_command`** — Hard stop violation (CLAUDE.md rule: no `shell=True`)
2. **Broken session model** — `Popen` creates a persistent process but `execute_command` runs a separate `subprocess.run`, so commands don't execute in the session process
3. **No structured MCP error responses** — Backend returned generic error dicts without `error_detail` or `operator_action` guidance
4. **No disconnected state handling in UI** — TerminalCanvas only showed "active" vs "error", no "disconnected" state
5. **No privilege escalation blocking** — `sudo`, `su`, dangerous patterns allowed through
6. **No session limit** — Unlimited sessions could exhaust resources
7. **Non-atomic file writes** — Session persistence and audit log used plain writes
8. **No command validation** — Empty commands, oversized commands all passed through
9. **UI error handling too fragile** — Any MCP error caused generic "fetch failure" instead of precise states
10. **Command input shown for disconnected/error sessions** — Users could try to type into dead sessions

## Deliverables

### Backend: `ai/shell_service.py`
- Remove `shell=True` — use `shlex.split()` + `subprocess.run(shell=False)`
- Add `_is_command_allowed()` — block `sudo`, `su`, dangerous patterns, oversized commands
- Add `_atomic_write()` for session and audit persistence (tempfile + os.replace)
- Add `MAX_SESSIONS = 10`, `MAX_COMMAND_LENGTH = 4096`, `COMMAND_TIMEOUT = 30`
- Add custom exceptions: `ShellSessionCreationError`, `ShellSessionNotFoundError`, `ShellCommandError`
- All error responses include `error`, `error_detail`, and `operator_action` fields
- Session liveness check in `get_session()` and `list_sessions()` — detect dead processes
- `get_session_context()` now includes `status` and `command_count`
- Audit log records `command_blocked` and `session_create_failed` events
- Output truncation to 4KB for stdout/stderr

### Backend: `ai/mcp_bridge/tools.py`
- P94 comment on shell tool section
- `get_session()` and `get_session_context()` no longer return `None` — always return dict with error info

### Frontend: `ui/src/hooks/useShellSessions.ts`
- Add `isErrorResponse()` and `extractError()` helpers for structured MCP error handling
- `createSession()` handles `status: "error"` sessions from backend
- `executeCommand()` maps error codes to precise UI messages with operator actions
- `terminateSession()` handles error responses properly
- Output buffer cleared on session switch via `setActiveSession`
- Connection errors shown as separate TerminalOutput entries

### Frontend: `ui/src/components/shell-gateway/TerminalCanvas.tsx`
- Add disconnected session state view with operator guidance
- Improve error session view with actionable guidance
- Escape quotemarks in empty-state text

### Frontend: `ui/src/components/shell-gateway/ShellContainer.tsx`
- Command input disabled during loading (was only disabled on empty input)
- New status bar for disconnected/error/idle sessions below the terminal canvas
- Shows operators what to do: "terminate and create new session"

### Frontend: `ui/src/components/shell-gateway/ShellSidePane.tsx`
- Audit log fetch error handled gracefully (returns empty array)
- `command_blocked` action shown in red alongside `session_terminated`

### Tests: `tests/test_shell_service.py`
- 23 tests covering:
  - Atomic write correctness
  - Command allowlisting (empty, sudo, dangerous patterns, oversize)
  - Session creation, persistence, liveness
  - Command execution (success, blocked, timeout, not found, session-not-found)
  - Session termination
  - Session context retrieval
  - Audit log creation, filtering

## Security Model Preserved

- No privilege expansion: `sudo` and `su` commands are blocked
- Audit logging on every command execution, blocked command, and session event
- All actions remain local-only (127.0.0.1)
- `shell=False` on all `subprocess` calls
- Static argument lists only — no `shell=True`
- Command output truncated to 4KB
- Session limit of 10 concurrent sessions

## Files Modified

- `ai/shell_service.py` — Complete runtime recovery rewrite
- `ai/mcp_bridge/tools.py` — Shell handler cleanup
- `ui/src/hooks/useShellSessions.ts` — Error state handling, structured responses
- `ui/src/components/shell-gateway/TerminalCanvas.tsx` — Disconnected/error states
- `ui/src/components/shell-gateway/ShellContainer.tsx` — Status bar for inactive sessions
- `ui/src/components/shell-gateway/ShellSidePane.tsx` — Blocked command display, error handling
- `tests/test_shell_service.py` — New test file (23 tests)