# P77 — UI Architecture + Contracts Baseline

**Status**: Ready  
**Dependencies**: P76  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Define the canonical architecture, trust boundaries, route map, settings/security model, panel structure, repo doc targets, and execution contract for the Bazzite Unified Control Console before implementation begins.

## Summary / Scope

This phase locks the local-only, single-user architecture, Midnight Glass visual direction, trust boundaries, shell layout, settings model, and service boundaries so future UI phases have a stable, unambiguous target.

**Key Constraint**: This is a local-only, single-user operator console. No multi-user features, no cloud sync, no external authentication.

## Architecture Principles

### 1. Local-Only, Single-User

- All data stays on the local machine
- No user accounts or authentication flows
- Settings stored locally (encrypted at rest for sensitive values)
- No network calls except to configured AI providers

### 2. Security-First Operator Console

The UI should feel like a professional security operations tool:
- Clean, focused interface
- Progressive disclosure of advanced features
- Clear visual hierarchy for alerts and warnings
- Audit trails for all actions

### 3. Chat-First Workflow

- Chat is a primary page, not an overlay
- Tool results render inline in chat
- Conversation history is searchable
- Context-aware suggestions

### 4. Terminal as Native Companion

- Terminal/TUI feels native to the product
- Seamless transition between GUI and CLI
- Shared context between chat and terminal
- Command history synced

### 5. Minimal Shell / Progressive Disclosure

- Clean top-level shell by default
- Collapsed icon rail (expandable)
- Feature-rich deeper layers accessible via drill-down
- No cluttered "admin dashboard" aesthetic

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    USER SPACE (UI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Chat      │  │   Security  │  │   Settings          │ │
│  │   Workspace │  │   Ops       │  │   (PIN-gated)       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│              MCP BRIDGE (127.0.0.1:8766)                   │
│         Tool validation + scoped secret loading              │
├─────────────────────────────────────────────────────────────┤
│              LLM PROXY (127.0.0.1:8767)                    │
│         Health-weighted routing + rate limiting              │
├─────────────────────────────────────────────────────────────┤
│              SYSTEM SERVICES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Phase      │  │  Security   │  │  Intel              │ │
│  │  Control    │  │  Agents     │  │  Scraper            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Security Zones

1. **Public Zone**: Chat, Help, Documentation
2. **Operator Zone**: Security Ops, Models, Terminal, Project/Phases
3. **Privileged Zone**: Settings (PIN-gated), Dangerous Actions (2FA)

## Primary Panel Map

### 1. Chat and Tool Workspace (Primary)

**Purpose**: Main interaction surface for AI assistance

**Features**:
- Persistent chat history
- Tool result rendering (inline cards)
- File upload / drag-drop
- Conversation search
- Context pinning
- Branching conversations

**Layout**:
- Full-width chat stream
- Input area at bottom (fixed)
- Context sidebar (collapsible)
- Tool palette (command palette integration)

### 2. Security Ops Center

**Purpose**: Security monitoring and incident response

**Features**:
- Threat intel dashboard
- Active alerts panel
- Scan status overview
- Quarantine management
- Alert history
- IOC lookup tools

**Layout**:
- Summary cards (top)
- Alert feed (center)
- Quick actions (right sidebar)
- Timeline view (expandable)

### 3. Models and Providers

**Purpose**: LLM provider management and monitoring

**Features**:
- Provider health status
- Token usage tracking
- Model selection
- Routing configuration
- Cost monitoring
- Fallback chain visualization

**Layout**:
- Provider grid (cards)
- Usage charts
- Routing rules editor
- Test/validate buttons

### 4. Settings (PIN-Gated)

**Purpose**: System configuration (sensitive)

**Features**:
- API key management (masked)
- Security settings (2FA toggle)
- Notification preferences
- Gmail alert configuration
- Backup/restore
- Dangerous actions whitelist

**Security**:
- PIN required for access
- 2FA for sensitive changes
- Masked secrets (never displayed in full)
- Audit log of all changes

### 5. Terminal

**Purpose**: Native TUI companion

**Features**:
- Full terminal emulation
- Command history
- Context-aware suggestions
- Split panes
- Session management

**Integration**:
- Share context with chat
- Copy/paste between GUI and terminal
- Command palette integration

### 6. Project and Phases

**Purpose**: Phase control and project management

**Features**:
- Phase roadmap view
- Active phase monitor
- Notion sync status
- Task queue overview
- Handoff history

**Layout**:
- Phase timeline
- Current phase card
- Dependency graph (readonly)
- Action buttons (contextual)

## Global Surfaces

### Command Palette

**Purpose**: Universal quick access to all features

**Trigger**: `Ctrl+K` (Linux/Windows) or `Cmd+K` (macOS)

**Capabilities**:
- Navigate to any panel ("Go to Security")
- Execute MCP tools ("Run security audit")
- Search chat history ("Find conversation about P76")
- Run system commands ("Restart MCP Bridge")
- Find settings ("Open API key settings")
- Switch themes (if multiple supported)

**Layout**:
```
┌─────────────────────────────────────────────┐
│ 🔍  Search commands, tools, settings...    │
├─────────────────────────────────────────────┤
│ ⚡   Go to Chat                       ↵     │
│ 🔒   Go to Security Ops               ↵     │
│ ─────────────────────────────────────────── │
│ 🔧  Tools                                   │
│    security.status                    ↵     │
│    system.gpu_status                  ↵     │
│    agents.security_audit              ↵     │
│ ─────────────────────────────────────────── │
│ ⚙️   Settings                               │
│    Open API key management            ↵     │
│    Toggle notifications               ↵     │
└─────────────────────────────────────────────┘
```

**Behavior**:
- Modal overlay with glass background
- Fuzzy search on command names and descriptions
- Recent commands section (last 5)
- Keyboard navigation (arrow keys + enter)
- Escape to close
- Right side shows keyboard shortcuts

### Artifact Drawer

**Purpose**: Access files, logs, and generated artifacts across all panels

**Trigger**: 
- Global: `Ctrl+Shift+A` or toolbar button
- Contextual: Panel-specific artifact buttons

**Content Types**:
- Generated files (reports, exports)
- Log excerpts (security, health, system)
- Screenshots / evidence
- Downloaded attachments
- Temporary working files

**Layout**:
```
Main Content Area          │ ┌───────────────────────────┐
                           │ │ 📎 Artifacts              │
                           │ ├───────────────────────────┤
                           │ │ 🔍 Search artifacts...    │
                           │ ├───────────────────────────┤
                           │ │ 📄 security-scan.log      │
                           │ │    12.4 KB • 2 min ago   │
                           │ │    [👁] [↓]               │
                           │ │                           │
                           │ │ 📊 health-report.pdf      │
                           │ │    245 KB • 1 hour ago   │
                           │ │    [👁] [↓]               │
                           │ │                           │
                           │ │ 📷 screenshot-001.png     │
                           │ │    1.2 MB • Yesterday    │
                           │ │    [👁] [↓]               │
                           │ ├───────────────────────────┤
                           │ │ [Clear All]      [Export] │
                           │ └───────────────────────────┘
```

**Behavior**:
- Slide-out panel from right (320px width)
- Persistent across panel switches
- Search/filter by name, type, date
- Preview pane for supported formats
- Download individual or batch (zip)
- Auto-cleanup after 30 days (configurable)

### Notifications / Activity Center

**Location**: Top bar, right side (bell icon)

**Notification Types**:
| Priority | Types | Behavior |
|----------|-------|----------|
| **Critical** | Security breach, system failure | Persistent badge + sound + desktop notification |
| **High** | Phase blocked, scan complete | Badge + desktop notification |
| **Medium** | Timer warning, provider switch | Badge only |
| **Low** | Info, tips | Auto-dismiss after 5 seconds |

**Layout**:
```
┌─────────────────────────────┐
│ 🔔 Notifications      [⚙️]  │
├─────────────────────────────┤
│ 🚨 Security Alert    1m ago │
│ High priority threat        │
│ detected in quarantine      │
│                    [View]   │
├─────────────────────────────┤
│ ✅ Phase Complete    5m ago │
│ P76 finished successfully   │
│                    [View]   │
├─────────────────────────────┤
│ ⚠️ Timer Warning    15m ago │
│ health.timer hasn't run     │
│                    [Check]  │
├─────────────────────────────┤
│ [Mark All Read]  [History]  │
└─────────────────────────────┘
```

**Behavior**:
- Badge count on bell icon (max 99+)
- Dropdown panel on click
- Click notification to navigate to relevant panel
- Settings gear for notification preferences
- History view (last 100 notifications)
- Do Not Disturb mode (suppress non-critical)

### Status Chips

**Purpose**: Consistent status indication across all UI surfaces

**Types**:
| Chip | Visual | Usage |
|------|--------|-------|
| **Online** | 🟢 Green dot + "Online" | Service healthy, connected |
| **Live** | 🔵 Cyan pulse + "Live" | Active streaming, real-time |
| **Warning** | 🟠 Amber dot + "Warning" | Attention needed |
| **Error** | 🔴 Red dot + "Error" | Problem state |
| **Offline** | ⚪ Gray dot + "Offline" | Disconnected, inactive |
| **Busy** | 🟠 Amber pulse + "Processing" | Working, wait state |
| **Locked** | 🔒 Icon + "Locked" | Security locked |

**Placement**:
- Top bar: System status (MCP Bridge, LLM Proxy)
- Panel headers: Panel-specific status
- Cards: Item status (provider health, phase status)
- Settings: Feature status indicators

**Example**:
```
┌─────────────────────────────────────────────┐
│ Models & Providers                [🟢 Online]│
├─────────────────────────────────────────────┤
│                                             │
│ Gemini                    🟢 Online         │
│ Groq                      🟢 Online         │
│ OpenRouter                🟠 Warning        │
│   └─ High latency (2.3s)                   │
│ Mistral                   ⚪ Offline        │
│                                             │
└─────────────────────────────────────────────┘
```

### Audit Strip

**Purpose**: Visibility into recent actions for accountability

**Location**: Fixed bottom of privileged panels (Settings, Security Ops)

**Shows**:
- Last action timestamp
- Action type (view, edit, delete, execute)
- Actor (user, system, agent)
- Target resource
- View full audit log link

**Layout**:
```
┌─────────────────────────────────────────────┐
│                                             │
│         Main Panel Content                  │
│                                             │
├─────────────────────────────────────────────┤
│ 📝 Settings changed    2 min ago    [History]│
└─────────────────────────────────────────────┘
         ↑
      Audit Strip (32px height)
```

**Behavior**:
- Updates in real-time
- Click "History" for full audit log
- Export audit log (CSV/JSON)
- Filter by action type, date range
- Retention: 90 days default

## Navigation Model

### Minimal Shell / Progressive Disclosure

**Default State**:
```
┌────────────────────────────────────────────┐
│  [≡]  Bazzite Control Console    [🔍][👤] │  ← Compact Top Bar
├────┬───────────────────────────────────────┤
│    │                                       │
│ ⚡  │      Main Content Area               │
│ 🔒  │      (Chat / Security / etc)         │
│ ⚙️   │                                       │
│ 📋  │                                       │
│ 💻  │                                       │
│ 📊  │                                       │
│    │                                       │
└────┴───────────────────────────────────────┘
     ↑
Collapsed Icon Rail (5 icons)
```

**Expanded State**:
```
┌────────────────────────────────────────────┐
│  [≡]  Bazzite Control Console    [🔍][👤] │
├──────────┬─────────────────────────────────┤
│ Chat     │                                 │
│ Security │      Main Content Area          │
│ Models   │                                 │
│ Terminal │                                 │
│ Projects │                                 │
│ Settings │                                 │
├──────────┤                                 │
│ [≪]      │                                 │
└──────────┴─────────────────────────────────┘
     ↑
Expanded Rail with Labels
```

### Icon Rail Structure

| Icon | Label | Panel | Security Zone |
|------|-------|-------|---------------|
| 💬 | Chat | Chat Workspace | Public |
| 🛡️ | Security | Security Ops | Operator |
| 🤖 | Models | Models & Providers | Operator |
| 💻 | Terminal | Terminal | Operator |
| 📊 | Projects | Project & Phases | Operator |
| ⚙️ | Settings | Settings | Privileged (PIN) |

## Command Palette

**Trigger**: `Ctrl+K` or `Cmd+K`

**Capabilities**:
- Navigate to any panel
- Execute MCP tools
- Search chat history
- Run system commands
- Find settings

**Layout**:
- Modal overlay
- Fuzzy search
- Recent commands section
- Keyboard navigation

## Notifications / Activity Center

**Location**: Top bar, right side

**Types**:
- Security alerts (high priority)
- Phase completion notifications
- Timer health warnings
- Provider status changes

**Behavior**:
- Badge count on bell icon
- Dropdown panel for history
- Click to navigate to relevant panel
- Auto-dismiss for low priority

## Artifact Drawer

**Purpose**: Access files, logs, and generated artifacts

**Trigger**: Panel-specific or global shortcut

**Content**:
- Generated files
- Log excerpts
- Exported reports
- Screenshots/evidence

**Layout**:
- Slide-out panel (right side)
- List view with metadata
- Preview pane
- Download/share actions

## Danger Modal

**Trigger**: Destructive actions requiring confirmation

**Features**:
- Clear warning iconography
- Explicit confirmation text
- 2FA challenge for highest-risk actions
- 5-second delay for irreversible actions

**States**:
- Warning (yellow) — Reversible, requires click
- Danger (red) — Destructive, requires type-to-confirm
- Critical (red + 2FA) — System-level, requires 2FA code

## State Surfaces

### Status Chips

Consistent across all panels:
- **Online/Healthy**: Green dot + text
- **Warning**: Amber dot + text
- **Error**: Red dot + text
- **Offline**: Gray dot + text
- **Active/Live**: Cyan pulse animation

### Audit Strip

**Location**: Bottom of privileged panels

**Shows**:
- Last action timestamp
- Action type
- Actor (user or system)
- View full audit log link

## Responsive Layout Matrix

| Breakpoint | Layout | Notes |
|------------|--------|-------|
| ≥1920px | Full 3-column | Rail + Content + Context sidebar |
| 1280-1919px | 2-column | Rail + Content (sidebar collapses) |
| 1024-1279px | Compact 2-column | Collapsed rail default |
| <1024px | Single column | Rail becomes bottom nav |

## Settings / Security Model

### Authentication Tiers

| Tier | Requirement | Use Case |
|------|-------------|----------|
| **Standard** | None | Chat, View panels |
| **Operator** | Session active | Security Ops, Terminal |
| **Privileged** | 4-digit PIN | Settings access |
| **Dangerous** | PIN + 2FA | API key changes, destructive actions |

### PIN Configuration

- 4-6 digit PIN
- Stored hashed (bcrypt)
- 3 attempts → 5 minute lockout
- Forgot PIN → Requires system admin recovery

### 2FA Configuration

- TOTP-based (authenticator app)
- Gmail backup codes
- QR code setup flow
- Remember device option (30 days)

### Secret Masking

- API keys: Show first 4 + last 4 only
- Passwords: Never visible
- Tokens: One-time reveal with PIN
- Copy button (masked value not in clipboard)

### Gmail Alerts

- Optional integration
- Alert on security events
- Alert on phase completions
- Alert on system health issues
- Configurable frequency (immediate, digest)

## Repo Doc Targets

### Phase-Owned (docs/P77_*.md)

- `docs/P77_UI_ARCHITECTURE.md` — This document
- `docs/P77_TRUST_BOUNDARIES.md` — Detailed security zones
- `docs/P77_PANEL_SPEC.md` — Panel-by-panel specifications

### Cross-Phase (docs/)

- `docs/UI_NAVIGATION.md` — Navigation patterns
- `docs/UI_SECURITY.md` — Security model details
- `docs/PHASE_INDEX.md` — Updated with P77

## Phase Ordering and Dependencies

### UI Initiative Roadmap (P77-P88)

| Phase | Focus | Depends On |
|-------|-------|------------|
| P77 | UI Architecture (this phase) | P76 |
| P78 | Midnight Glass Design System | P77 |
| P79 | Shell + Navigation | P78 |
| P80 | Chat Workspace | P79 |
| P81 | Security Ops Center | P79 |
| P82 | Models & Providers | P79 |
| P83 | Terminal Integration | P79 |
| P84 | Settings + PIN/2FA | P79 |
| P85 | Projects & Phases | P79 |
| P86 | Command Palette | P79-P80 |
| P87 | Responsive Polish | P80-P85 |
| P88 | Design Finalization | P87 |

## Design Sign-Off Authority

**⚠️ CRITICAL**: Final design sign-off for mockups, visual direction, and canonical design direction is **user-only**. 

OpenCode may:
- Refine working drafts
- Suggest improvements
- Document existing decisions

OpenCode may NOT:
- Mark designs as final
- Approve visual direction changes
- Override user design preferences

## Definition of Done

- [x] Architecture documented (this doc)
- [ ] Trust boundaries mapped
- [ ] Panel inventory complete
- [ ] Navigation model specified
- [ ] Security model defined
- [ ] Phase roadmap established
- [ ] Repo docs created/updated
- [ ] HANDOFF.md updated

## References

- P76 — Ingestion Reliability (prerequisite)
- P78 — Midnight Glass Design System (next phase)
- AGENT.md — System architecture
- HANDOFF.md — Session context

## Implementation Notes

1. **Tech Stack TBD**: P78 will specify React/Vue/Tauri/etc.
2. **Backend Unchanged**: Python control plane remains authoritative
3. **MCP Integration**: UI calls MCP tools via bridge (127.0.0.1:8766)
4. **Local Storage**: Settings in SQLite or encrypted JSON
5. **No External Auth**: Local-only as specified
