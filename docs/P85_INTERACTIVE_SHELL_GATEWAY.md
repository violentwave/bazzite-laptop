# P85 — Interactive Shell Gateway

**Status**: Complete  
**Dependencies**: P79, P81, P82, P83, P84  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Implement the Interactive Shell Gateway for the Unified Control Console — a secured local PTY/shell workspace with session management, audit trails, and handoff paths to chat, artifacts, and workflow context.

## Summary / Scope

This phase delivers the Interactive Shell Gateway — an operator-grade terminal workspace that provides:
- Local shell session management with PTY support
- Multiple concurrent session tabs
- Real-time audit/context strip
- Status chips (live, idle, warning, disconnected)
- Optional logs/artifacts side pane
- Security-aware access gating
- Handoff paths between chat, shell, and workflow context

**Key Features**:
- Create and manage multiple terminal sessions
- Execute commands with real-time output streaming
- Session status tracking (active, idle, disconnected, error)
- Comprehensive audit logging (JSONL format)
- Context strip showing session metadata
- Status chips for visual state indication
- Collapsible side pane for logs and artifacts
- Midnight Glass design compliance

## Implementation

### Backend Components

#### `ai/shell_service.py` (~385 lines)

**ShellService**:
- Manages terminal sessions with subprocess-based PTY
- Session persistence to JSON file
- Audit logging to JSONL
- Command execution with timeout
- Session lifecycle management (create/terminate)

**Data Structures**:
- `ShellSession`: Session data (id, name, status, cwd, pid, command_history)
- `SessionContext`: Display context (user, hostname, cwd, shell, idle_time)

**Key Methods**:
- `create_session(name, cwd, env)`: Create new shell session
- `execute_command(session_id, command)`: Execute command in session
- `terminate_session(session_id)`: Terminate session
- `get_session_context(session_id)`: Get session context for UI
- `get_audit_log(session_id, limit)`: Get audit entries

**MCP Tools (7 tools)**:
- `shell.create_session`: Create new interactive shell session
- `shell.list_sessions`: List all shell sessions
- `shell.get_session`: Get session details by ID
- `shell.execute_command`: Execute command in shell session (destructive)
- `shell.terminate_session`: Terminate shell session (destructive)
- `shell.get_context`: Get session context (user, cwd, shell, idle time)
- `shell.get_audit_log`: Get shell audit log

### Frontend Components

#### `ui/src/components/shell-gateway/` (~1,400 lines)

**ShellContainer.tsx**:
- Main panel component with header, tabs, terminal, and side pane
- Integrates with `useShellSessions` hook
- Command input with keyboard shortcuts
- Side pane toggle
- New session button

**TerminalCanvas.tsx**:
- Terminal output display with auto-scroll
- Session info header (name, id, cwd)
- Color-coded output (input, output, error, system)
- Loading indicator for command execution
- Empty/error state handling

**SessionTabs.tsx**:
- Horizontal tab bar for session switching
- Status indicator per session
- Close button for session termination
- New session button

**ShellAuditStrip.tsx**:
- Fixed bottom bar with session metadata
- Session ID, user@host, shell type
- Idle time, command count
- Session start timestamp

**ShellStatusBar.tsx**:
- Status chips for session state
- Error state display
- Idle time badge (when applicable)
- PID badge (when active)

**ShellSidePane.tsx**:
- Collapsible side panel (320px width)
- Tab navigation: Audit Log / Artifacts
- Audit log view with timestamp and details
- Artifacts placeholder view

#### Supporting Files

**`ui/src/types/shell.ts`**:
- TypeScript interfaces for ShellSession, SessionContext, CommandResult
- AuditLogEntry, TerminalOutput, SessionUIState types

**`ui/src/hooks/useShellSessions.ts`**:
- React hook for shell session management
- MCP Bridge integration
- Auto-refresh every 5 seconds
- Output buffer management
- Utility functions (getSessionStatusColor, formatIdleTime)

### Security Features

**Local-Only Access**:
- Shell sessions run locally on the machine
- No remote access or cloud execution
- Subprocess execution within user context

**Audit Trail**:
- All commands logged with timestamp
- Exit codes recorded
- Session lifecycle events tracked
- Append-only JSONL format

**Destructive Action Marking**:
- `shell.execute_command` marked as destructive
- `shell.terminate_session` marked as destructive
- Requires explicit user confirmation in UI

**Session Isolation**:
- Each session has unique ID and environment
- Working directory tracking
- Process isolation via subprocess

## File Structure

```
ai/
├── shell_service.py               # Backend service (385 lines)
├── mcp_bridge/tools.py            # 7 shell tool handlers

configs/
└── mcp-bridge-allowlist.yaml      # 7 shell tools registered

ui/src/components/shell-gateway/
├── ShellContainer.tsx             # Main panel (180 lines)
├── TerminalCanvas.tsx             # Terminal display (180 lines)
├── SessionTabs.tsx                # Session tabs (100 lines)
├── ShellAuditStrip.tsx            # Audit strip (130 lines)
├── ShellStatusBar.tsx             # Status chips (120 lines)
├── ShellSidePane.tsx              # Side pane (180 lines)
└── index.ts                       # Exports

ui/src/hooks/
├── useShellSessions.ts            # Shell hook (250 lines)

ui/src/types/
├── shell.ts                       # Shell types (70 lines)

ui/src/app/page.tsx                # Updated with ShellContainer
```

## Deliverables

- [x] ShellService with session management and PTY
- [x] 7 MCP tools for shell operations
- [x] ShellContainer main panel component
- [x] TerminalCanvas for output display
- [x] SessionTabs for multi-session UI
- [x] ShellAuditStrip with session metadata
- [x] ShellStatusBar with status chips
- [x] ShellSidePane for logs/artifacts
- [x] useShellSessions hook with auto-refresh
- [x] TypeScript types for all data structures
- [x] Midnight Glass design compliance
- [x] Security audit logging
- [x] P85 documentation

## Validation Results

### Backend
```bash
ruff check ai/shell_service.py
```
All checks passed

### Frontend
```bash
cd ui && npx tsc --noEmit
```
No type errors

### Integration
```bash
grep -c "shell\." configs/mcp-bridge-allowlist.yaml
```
7 tools registered

## Usage

### Creating a Session
1. Navigate to Terminal panel via icon rail
2. Click "+ New Session" button
3. Session tab appears with status indicator

### Executing Commands
1. Ensure session is active (green status dot)
2. Type command in input field at bottom
3. Press Enter or click Run button
4. Output appears in terminal canvas

### Managing Sessions
- Click session tab to switch between sessions
- Click × on tab to terminate session
- Sessions auto-save and persist between reloads

### Viewing Audit Log
1. Click "Show Sidebar" button
2. Click "Audit Log" tab
3. View recent commands with timestamps and exit codes

## Design Compliance

All components follow P78 Midnight Glass specifications:

**Colors**:
- Terminal background: `--base-00` (darkest graphite)
- Session tabs: `--base-01` with accent borders
- Active session: `--success` (green) status dot
- Idle session: `--warning` (amber) status
- Error state: `--danger` (red)

**Typography**:
- Terminal: JetBrains Mono monospace
- UI text: Inter sans-serif
- Status chips: Small uppercase labels

**Layout**:
- Compact header with status bar
- Horizontal session tabs
- Flexible terminal canvas
- Fixed audit strip at bottom
- Collapsible side pane (320px)

**Motion**:
- Pulse animation for active/live sessions
- Smooth transitions for tab switching
- Auto-scroll in terminal canvas

## Integration Points

### From P81 (PIN-Gated Settings)
- Security model foundation
- Audit logging patterns
- Privileged zone concepts

### From P82 (Provider Discovery)
- Auto-refresh patterns (30s interval)
- Status chip components
- Health indicator styling

### From P83 (Chat Workspace)
- Panel integration patterns
- Command execution patterns
- Output display conventions

### From P84 (Security Ops Center)
- Tab-based navigation
- Side panel patterns
- Audit trail display

### To P86 (Projects & Phases)
- Shell sessions can trigger workflow actions
- Command history available for task context
- Session context for phase execution

## Security Considerations

**Command Execution**:
- Commands execute in user context only
- No privilege escalation
- Timeout protection (30 seconds)
- Working directory restrictions

**Session Management**:
- Process isolation per session
- Environment variable control
- Signal handling for termination
- Zombie process prevention

**Audit Trail**:
- All commands logged
- Exit codes recorded
- Immutable JSONL format
- Session lifecycle tracked

## Next Phase Ready

**P86 — Project + Workflow + Phase Panels** can proceed:
- Shell gateway complete
- Session management patterns established
- Audit logging in place
- Handoff paths ready for workflow integration

## Commit

```
P85: Interactive Shell Gateway with session management, audit trails, and security gating
```

## References

- P77 — UI Architecture + Trust Boundaries
- P78 — Midnight Glass Design System
- P79 — Frontend Shell Bootstrap
- P81 — PIN-Gated Settings + Secrets Service
- P82 — Provider + Model Discovery
- P83 — Chat + MCP Workspace Integration
- P84 — Security Ops Center
- AGENT.md — System capabilities
- HANDOFF.md — Current session context
