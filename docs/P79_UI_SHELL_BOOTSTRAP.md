# P79 — Frontend Shell Bootstrap

**Status**: In Progress  
**Dependencies**: P78  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Bootstrap the custom local web UI shell for the Unified Control Console. Create the first working shell with local-only runtime assumptions, compact top bar, collapsed icon rail, clean main content pane, and Midnight Glass theme integration.

## Summary / Scope

This phase creates the real frontend shell and shared runtime primitives that later phases will attach to. The shell is intentionally minimal at first glance but architecturally ready for deep capability in future phases.

**Key Architectural Decisions**:
- **Location**: `ui/` directory at repo root — repo-native path for the frontend app
- **Stack**: Next.js 16 + React 19 + TypeScript + Tailwind v4 — matches existing capability pack recommendations
- **Backend Communication**: Direct fetch to MCP Bridge (127.0.0.1:8766) and LLM Proxy (127.0.0.1:8767) — no new backend abstraction
- **Local-Only Enforcement**: Development server binds to localhost only; runtime assumes 127.0.0.1 services

## Tech Stack Rationale

### Why Next.js App Router + TypeScript

1. **Existing Foundation**: Next.js 16 already initialized in `ui/` directory
2. **Type Safety**: TypeScript ensures component contracts match P77/P78 specifications
3. **App Router**: Native support for layouts, parallel routes, and server components for future expansion
4. **Tailwind v4**: Already configured with Midnight Glass tokens in globals.css
5. **Ecosystem**: Matches P61-P67 frontend capability pack patterns for consistency

### Why Not Replace Existing Backend

The Python control plane (`ai/` directory) remains authoritative:
- MCP Bridge (`ai/mcp_bridge/`) provides 96 tools via HTTP
- LLM Proxy (`ai/llm_proxy.py`) provides OpenAI-compatible API
- Phase Control (`ai/phase_control/`) manages execution
- No duplication — frontend is a thin client to existing services

### Local-Only Binding Strategy

**Development**:
```bash
cd ui && npm run dev  # Binds to localhost:3000 by default
```

**Runtime**:
- Frontend expects MCP Bridge at `http://127.0.0.1:8766`
- Frontend expects LLM Proxy at `http://127.0.0.1:8767`
- CORS configured for localhost origins only
- No external API calls from browser (all proxied through Python backend)

## Deliverables

### Code Structure

```
ui/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with fonts, metadata
│   │   ├── page.tsx            # Main content area (panel router)
│   │   └── globals.css         # Midnight Glass tokens
│   ├── components/
│   │   └── shell/
│   │       ├── ShellContext.tsx      # Global shell state
│   │       ├── Layout.tsx            # Shell layout frame
│   │       ├── TopBar.tsx            # Compact top bar (48px)
│   │       ├── IconRail.tsx          # Collapsible icon rail
│   │       ├── CommandPalette.tsx    # Global command/search
│   │       └── NotificationsPanel.tsx # Activity frame
│   ├── lib/
│   │   └── mcp-client.ts       # MCP Bridge client (future)
│   └── panels/                 # Future panel components
├── package.json
├── next.config.ts
├── tsconfig.json
└── next-env.d.ts
```

### Implemented Components

#### 1. ShellContext
- Rail expanded/collapsed state
- Active panel tracking
- Command palette visibility
- Notifications visibility
- Audit log tracking (for privileged panels)

#### 2. TopBar (48px height)
- Logo + title (Bazzite Control Console)
- Context indicator (current panel)
- Search trigger (opens Command Palette)
- Notifications bell with badge
- User/settings button

#### 3. IconRail (56px collapsed, 200px expanded)
- Chat (public zone)
- Security Ops (operator zone)
- Models (operator zone)
- Terminal (operator zone)
- Projects (operator zone)
- Settings (privileged zone, PIN-gated in future)
- Collapse/expand toggle

#### 4. Command Palette
- Modal overlay with glass effect
- Keyboard shortcut: Ctrl/Cmd+K
- Fuzzy search across navigation and tools
- Sectioned results (Navigation, Tools, Agents, Settings)
- Keyboard navigation (↑↓, Enter, Escape)

#### 5. Notifications Panel
- Slide-out panel (360px width)
- Priority-based styling (critical/high/medium/low)
- Placeholder notifications for P79
- Real-time integration deferred to P80+

#### 6. Layout Frame
- Full-screen shell (no scroll on body)
- Top bar + main content area
- Icon rail (left)
- Notifications panel (right, overlay)
- Audit strip (bottom, privileged panels only)
- Command palette (center overlay)

### Midnight Glass Theme Integration

All components use CSS custom properties from `globals.css`:

**Base Colors**:
- `--base-00` to `--base-06`: Graphite foundation
- `--text-primary`, `--text-secondary`, `--text-tertiary`: Text hierarchy

**Accents**:
- `--accent-primary`: Indigo (#6366f1)
- `--accent-secondary`: Violet (#8b5cf6)
- `--live-cyan`: Cyan for live states only (#06b6d4)

**Glass Surfaces**:
- `--glass-bg`: rgba(18, 18, 26, 0.85)
- `--glass-border`: rgba(255, 255, 255, 0.08)
- `--blur-lg`: 16px

**State Colors**:
- `--success`: #22c55e
- `--warning`: #f59e0b
- `--danger`: #ef4444

## Features Ready for Future Panels

The shell architecture supports future phases:

| Panel | Phase | Shell Support |
|-------|-------|---------------|
| Chat Workspace | P80 | Icon rail navigation, content area ready |
| Security Ops Center | P81 | Icon rail navigation, zone styling |
| Models & Providers | P82 | Icon rail navigation, status chips |
| Terminal | P83 | Icon rail navigation, shared layout |
| Settings + PIN/2FA | P84 | Icon rail navigation, audit strip, privileged zone |
| Projects & Phases | P85 | Icon rail navigation, content area ready |
| Command Palette v2 | P86 | Foundation complete, needs MCP tool integration |

## Deferred to Future Phases

**P80 — Chat Workspace**:
- Chat message components
- Tool result rendering
- Conversation history
- File upload/drag-drop

**P81 — Security Ops Center**:
- Threat intel dashboard
- Alert feed integration
- Scan status widgets
- Real-time security data

**P82 — Models & Providers**:
- Provider health cards
- Token usage charts
- Routing visualization
- Provider configuration UI

**P83 — Terminal**:
- Terminal emulator component
- xterm.js integration
- Session management

**P84 — Settings + PIN/2FA**:
- PIN authentication flow
- 2FA setup/management
- API key management UI
- Gmail alert configuration

**P85 — Projects & Phases**:
- Phase timeline view
- Notion sync status
- Task queue visualization

**P86+**:
- Full MCP tool integration in Command Palette
- Real-time notifications from event bus
- Split-pane layouts
- Responsive breakpoints implementation

## Local Development

### Prerequisites
- Node.js 20+ (for Next.js 16)
- Services running: MCP Bridge (:8766), LLM Proxy (:8767)

### Start Development Server
```bash
cd ui
npm install  # if needed
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production
```bash
cd ui
npm run build
npm run start
```

## Validation

### TypeScript
```bash
cd ui
npx tsc --noEmit
```

### Lint
```bash
cd ui
npm run lint
```

### Ruff (docs)
```bash
ruff check docs/P79*.md || true
```

### Keyword Verification
```bash
rg -n "Midnight Glass|icon rail|command palette|top bar|local-only|single-user" docs HANDOFF.md ui/src
```

## Design Compliance

### Preserved from P78
- ✅ Near-black graphite foundation (#0a0a0f)
- ✅ Indigo / cold violet / electric blue accents
- ✅ Cyan reserved for focus/live states
- ✅ Glass only on elevated contextual layers (modals, overlays)
- ✅ No gamer neon
- ✅ No pink-forward retro drift
- ✅ No cluttered SaaS-dashboard look

### Shell Structure
- ✅ Compact top-level shell (48px top bar)
- ✅ Collapsed icon rail by default (56px)
- ✅ Feature-rich deeper layers (expandable rail, command palette)
- ✅ Chat-first future ready
- ✅ Terminal/TUI native companion ready

## Security Zones (Visual)

| Zone | Panels | Visual Cue |
|------|--------|------------|
| Public | Chat | Standard accent |
| Operator | Security, Models, Terminal, Projects | Warning accent on hover |
| Privileged | Settings | Danger accent, audit strip |

## Definition of Done

- [x] Frontend bootstrapped in `ui/` directory
- [x] Next.js 16 + React 19 + TypeScript configured
- [x] Tailwind v4 with Midnight Glass tokens
- [x] TopBar component (48px, compact)
- [x] IconRail component (56px/200px, collapsible)
- [x] CommandPalette component (Ctrl+K, glass modal)
- [x] NotificationsPanel component (slide-out)
- [x] Layout frame with all shell surfaces
- [x] ShellContext for state management
- [x] Midnight Glass CSS tokens in globals.css
- [x] Local-only runtime assumptions documented
- [x] P79 documentation created
- [x] HANDOFF.md updated

## Next Phase Ready

**P80 — Chat Workspace** can proceed immediately:
- Shell layout complete
- Content area ready for panel content
- Icon rail navigation functional
- Command palette foundation ready

## References

- P77 — UI Architecture + Contracts Baseline
- P78 — Midnight Glass Design System
- AGENT.md — System capabilities
- HANDOFF.md — Current session context
- `ui/AGENTS.md` — Next.js-specific rules

## Implementation Notes

1. **No API keys in frontend**: All sensitive operations go through Python backend
2. **No shell=True**: Frontend uses standard HTTP fetch only
3. **127.0.0.1 only**: Services refuse 0.0.0.0 binding
4. **Progressive enhancement**: Shell works without JavaScript (SSR), enhanced with client JS
5. **Accessibility**: Focus visible, keyboard navigation, ARIA labels where needed
