# P78 — Midnight Glass Design System

**Status**: Complete  
**Dependencies**: P77  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Create the Midnight Glass design system, panel layout grammar, interaction states, component inventory, token plan, and Figma mapping strategy that will drive the custom UI build.

## Summary / Scope

This phase defines tokens, layout grammar, component patterns, danger-state styling, and screen inventory so implementation can proceed from a unified design system. The visual direction is **locked**: Midnight Glass theme with near-black graphite base, indigo/violet/blue accents, and optional cyan for focus/live states.

**Design Direction**: Locked per user specification
- Theme: Midnight Glass
- Base: Near-black graphite
- Accents: Indigo / cold violet / electric blue
- Live States: Brighter cyan (reserved)
- Feel: Security-first operator console
- Anti-patterns: No gamer neon, no pink-forward retro, no cluttered SaaS dashboard

## Design Principles

### 1. Midnight Glass Aesthetic

- **Dark-first**: Near-black (#0a0a0f to #12121a) as primary background
- **Glass layers**: Subtle transparency for elevated surfaces only
- **Cold spectrum**: Indigo, violet, electric blue for interactive elements
- **Cyan reserved**: Brighter cyan exclusively for focus/live/active states
- **High contrast**: Text on dark must meet WCAG AA minimum

### 2. Security Console Feel

- Professional, not playful
- Clear hierarchy of information
- Alert states are visible but not alarming
- Density appropriate for operators, not consumers

### 3. Progressive Disclosure

- Minimal default view
- Advanced features one click away
- No overwhelming dashboard on first load
- Power user features accessible via keyboard shortcuts

### 4. Chat as Primary Surface

- Chat is not secondary or overlay
- Full-height chat workspace
- Tool results render beautifully inline
- Conversation is the organizing principle

### 5. Terminal as Native

- Terminal feels like part of the app, not an external tool
- Shared visual language with GUI
- Seamless context switching

## Color Tokens

### Base Colors (Graphite)

| Token | Hex | Usage |
|-------|-----|-------|
| `--base-00` | `#050508` | Deepest background |
| `--base-01` | `#0a0a0f` | Primary background |
| `--base-02` | `#12121a` | Elevated surfaces |
| `--base-03` | `#1a1a25` | Cards, panels |
| `--base-04` | `#252535` | Borders, dividers |
| `--base-05` | `#353545` | Hover states |
| `--base-06` | `#454555` | Active states |

### Accent Colors (Indigo/Violet)

| Token | Hex | Usage |
|-------|-----|-------|
| `--accent-primary` | `#6366f1` | Primary actions, links |
| `--accent-secondary` | `#8b5cf6` | Secondary emphasis |
| `--accent-tertiary` | `#a78bfa` | Highlights, badges |
| `--accent-glow` | `#4f46e5` | Glow effects |

### Cyan (Live States Only)

| Token | Hex | Usage |
|-------|-----|-------|
| `--live-cyan` | `#06b6d4` | Active/live indicators |
| `--live-glow` | `#0891b2` | Pulse animations |
| `--live-dim` | `#164e63` | Background for live areas |

### State Colors

| State | Color | Usage |
|-------|-------|-------|
| Success | `#22c55e` | Healthy, online, success |
| Warning | `#f59e0b` | Attention needed, amber |
| Danger | `#ef4444` | Error, blocked, critical |
| Info | `#3b82f6` | Neutral information |
| Offline | `#6b7280` | Inactive, disabled |

### Text Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--text-primary` | `#f8fafc` | Headings, primary text |
| `--text-secondary` | `#94a3b8` | Body text, labels |
| `--text-tertiary` | `#64748b` | Muted, placeholders |
| `--text-disabled` | `#475569` | Disabled state |

### Glass Surfaces

| Token | Value | Usage |
|-------|-------|-------|
| `--glass-bg` | `rgba(18, 18, 26, 0.85)` | Glass backgrounds |
| `--glass-border` | `rgba(255, 255, 255, 0.08)` | Glass borders |
| `--glass-highlight` | `rgba(99, 102, 241, 0.15)` | Glass accent |

## Typography Scale

### Font Stack

```css
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
--font-sans: 'Inter', 'SF Pro Display', system-ui, sans-serif;
```

### Type Scale

| Token | Size | Line | Weight | Usage |
|-------|------|------|--------|-------|
| `--text-xs` | 12px | 16px | 400 | Captions, timestamps |
| `--text-sm` | 14px | 20px | 400 | Secondary text |
| `--text-base` | 16px | 24px | 400 | Body text |
| `--text-lg` | 18px | 28px | 500 | Lead paragraphs |
| `--text-xl` | 20px | 28px | 600 | Small headings |
| `--text-2xl` | 24px | 32px | 600 | Section headings |
| `--text-3xl` | 30px | 36px | 700 | Major headings |
| `--text-4xl` | 36px | 40px | 700 | Display text |

### Monospace Scale (for code/terminal)

| Token | Size | Usage |
|-------|------|-------|
| `--mono-xs` | 11px | Compact code |
| `--mono-sm` | 13px | Terminal default |
| `--mono-base` | 14px | Code blocks |
| `--mono-lg` | 16px | Emphasized code |

## Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--space-0` | 0 | — |
| `--space-1` | 4px | Tight gaps |
| `--space-2` | 8px | Default gaps |
| `--space-3` | 12px | Component padding |
| `--space-4` | 16px | Card padding |
| `--space-5` | 20px | Section gaps |
| `--space-6` | 24px | Panel gaps |
| `--space-8` | 32px | Major sections |
| `--space-10` | 40px | Page margins |
| `--space-12` | 48px | Large sections |

## Border & Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-none` | 0 | Terminal, code |
| `--radius-sm` | 4px | Buttons, inputs |
| `--radius-md` | 6px | Cards |
| `--radius-lg` | 8px | Panels |
| `--radius-xl` | 12px | Modals |
| `--radius-full` | 9999px | Pills, avatars |

### Border Widths

| Token | Value | Usage |
|-------|-------|-------|
| `--border-thin` | 1px | Dividers, subtle |
| `--border-default` | 1px | Standard borders |
| `--border-thick` | 2px | Focus states |

## Shadow & Glow

### Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | Subtle elevation |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.4)` | Cards |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.5)` | Modals |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.6)` | Overlays |

### Glow Effects

| Token | Value | Usage |
|-------|-------|-------|
| `--glow-accent` | `0 0 20px rgba(99, 102, 241, 0.3)` | Primary glow |
| `--glow-live` | `0 0 20px rgba(6, 182, 212, 0.4)` | Live state glow |
| `--glow-danger` | `0 0 20px rgba(239, 68, 68, 0.3)` | Danger glow |

## Blur Effects

| Token | Value | Usage |
|-------|-------|-------|
| `--blur-sm` | `4px` | Subtle glass |
| `--blur-md` | `8px` | Standard glass |
| `--blur-lg` | `16px` | Heavy glass |

## Motion Tokens

### Durations

| Token | Value | Usage |
|-------|-------|-------|
| `--duration-fast` | 100ms | Micro-interactions |
| `--duration-normal` | 200ms | Standard transitions |
| `--duration-slow` | 300ms | Emphasis |
| `--duration-slower` | 500ms | Page transitions |

### Easing

| Token | Value | Usage |
|-------|-------|-------|
| `--ease-default` | `cubic-bezier(0.4, 0, 0.2, 1)` | Standard |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Exit |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Enter |
| `--ease-bounce` | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | Playful |

### Live Pulse Animation

```css
@keyframes pulse-live {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.4); }
  50% { opacity: 0.8; box-shadow: 0 0 0 8px rgba(6, 182, 212, 0); }
}
```

## Shell Rules

### Top Bar

- Height: 48px
- Background: `--base-01` with subtle bottom border
- Left: App menu toggle + Logo/Title
- Center: Context indicator (current panel)
- Right: Search, Notifications, User/Settings
- No window chrome (assume frameless or custom)

### Icon Rail

- Width (collapsed): 56px
- Width (expanded): 200px
- Background: `--base-01`
- Border: 1px right border `--base-04`
- Icons: 24px, centered in 56px height row
- Active state: Left border accent (3px) + background highlight
- Hover: Background `--base-03`

### Content Area

- Background: `--base-00` or `--base-01`
- Padding: `--space-6` (24px)
- Scroll: Native scroll with custom styling
- Max-width: None (full fluid layout)

### Glass Surfaces (Elevated Layers)

Use sparingly for:
- Modals
- Dropdowns
- Tooltips
- Command palette
- Notifications

**Rules**:
- Only on top of dark base (never full-glass UI)
- Always with backdrop blur
- Border required for definition
- Shadow for elevation

## Component Rules

### Top Bar

```
┌─────────────────────────────────────────────────────────────┐
│ [≡]  Bazzite Control Console        [🔍] [🔔] [👤] │
└─────────────────────────────────────────────────────────────┘
```

- Logo: Simple lightning bolt or terminal icon
- Title: "Bazzite" (bold) + "Control Console" (regular)
- Actions: Search (Cmd+K), Notifications bell, User menu
- Height: 48px fixed

### Icon Rail

**Collapsed (default)**:
```
│ ⚡  │  ← Active (left border accent)
│ 🔒  │
│ 🤖  │
│ 💻  │
│ 📊  │
│ ⚙️   │
```

**Expanded**:
```
│ ⚡  Chat          │
│ 🔒  Security      │
│ 🤖  Models        │
│ 💻  Terminal      │
│ 📊  Projects      │
│ ⚙️   Settings      │
│                  │
│ [≪] Collapse     │
```

### Chat Cards

**User Message**:
- Right-aligned
- Background: `--base-03`
- Border-radius: `--radius-lg` (top-right reduced)
- Max-width: 80%

**Assistant Message**:
- Left-aligned
- Background: Transparent (subtle left border accent)
- Max-width: 90%

**Tool Result Card**:
- Full width within assistant message
- Background: `--base-02`
- Border: 1px `--base-04`
- Header: Tool name + timestamp
- Body: Formatted result (code block, table, etc.)

### Command Palette Rows

```
┌─────────────────────────────────────────────┐
│ 🔍  Search...                               │
├─────────────────────────────────────────────┤
│ ⚡   Navigate to Chat              [↵]      │
│ 🔒   Navigate to Security          [↵]      │
│ ─────────────────────────────────────────── │
│ 🔧  Tools                                   │
│    security.status                 [↵]      │
│    system.gpu_status               [↵]      │
│ ─────────────────────────────────────────── │
│ ⚙️   Settings                               │
│    Toggle dark mode                [↵]      │
└─────────────────────────────────────────────┘
```

- Modal: Centered, max-width 640px
- Background: `--glass-bg` with `--blur-lg`
- Input: Top, sticky
- Sections: Divider with label
- Selected row: Background `--base-03` + left accent

### Notification Rows

```
┌─────────────────────────────────────────────┐
│ 🔔 Security Alert                           │
│ High priority threat detected               │
│ 2 min ago                          [View]   │
└─────────────────────────────────────────────┘
```

- Icon: State color (red for danger, etc.)
- Title: Bold
- Description: Secondary text
- Timestamp: Tertiary text
- Action: Text button

### Artifact Cards

```
┌─────────────────────────────────────────────┐
│ 📄 security-scan-2024-01-15.log             │
│ 12.4 KB • 2 min ago                 [↓] [👁]│
└─────────────────────────────────────────────┘
```

- Compact: Single row
- Icon: File type
- Name: Truncated with ellipsis
- Metadata: Size + time
- Actions: Download, Preview

### Modal Variants

**Standard Modal**:
- Background: `--base-02`
- Border-radius: `--radius-xl`
- Shadow: `--shadow-xl`
- Max-width: 560px
- Padding: `--space-6`

**Danger Modal**:
- Top border: 4px `--danger`
- Icon: Warning triangle (red)
- Confirm button: Red background
- Cancel button: Default style

**Glass Modal** (for overlays):
- Background: `--glass-bg`
- Backdrop-filter: `--blur-lg`
- Border: 1px `--glass-border`

### Settings Sections

```
┌─────────────────────────────────────────────┐
│ Security                                    │
│ ─────────────────────────────────────────── │
│ PIN Protection                              │
│ Require PIN to access settings      [Toggle]│
│                                             │
│ Two-Factor Authentication                   │
│ Status: Not configured              [Setup] │
│                                             │
│ Gmail Alerts                                │
│ Forward alerts to Gmail             [Toggle]│
│ user@example.com                    [Edit]  │
└─────────────────────────────────────────────┘
```

- Section title: `--text-lg`, bold
- Divider below title
- Setting row: Label left, control right
- Description: `--text-sm`, `--text-secondary`

### Shell Tabs

```
┌─────────────────────────────────────────────┐
│ Chat    │ Security │ Models │      [+]      │
└─────────────────────────────────────────────┘
```

- Active tab: Bottom border accent + bold text
- Inactive: `--text-secondary`
- Hover: Background `--base-02`
- Close button: × on hover

### Audit Strip

```
┌─────────────────────────────────────────────┐
│ Last action: Settings changed    2 min ago  │
│                                    [History]│
└─────────────────────────────────────────────┘
```

- Fixed to bottom of privileged panels
- Height: 32px
- Background: `--base-01`
- Border-top: 1px `--base-04`
- Text: `--text-xs`, `--text-secondary`

### Status Chips

| Type | Visual | Usage |
|------|--------|-------|
| Online | 🟢 Green dot + "Online" | Service healthy, connected |
| Warning | 🟠 Amber dot + "Warning" | Attention needed, amber |
| Error | 🔴 Red dot + "Error" | Error, blocked, critical |
| Info | 🔵 Blue dot + "Info" | Neutral information |
| Offline | ⚪ Gray dot + "Offline" | Inactive, disabled |
| Live | 🔵 Cyan pulse + "Live" | Active streaming, real-time |
| Busy | 🟠 Amber pulse + "Processing" | Working, wait state |

```
┌─────────────┐
│ ● Online    │
└─────────────┘
```

- Background: `--base-02`
- Border-radius: `--radius-full`
- Padding: `--space-1` `--space-3`
- Dot: 8px circle (10px for Live with pulse)
- Text: `--text-xs`

### State Surfaces

**Purpose**: Consistent empty, loading, error, and success states across all panels.

#### Loading State

```
┌─────────────────────────────────────────────┐
│                                             │
│          ⏳ Loading...                      │
│                                             │
│    Fetching security scan results...        │
│                                             │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: Animated spinner (optional branded icon)
- Icon color: `--accent-primary` or `--text-secondary`
- Title: `--text-lg`, `--text-primary`, centered
- Description: `--text-sm`, `--text-secondary`, centered
- Animation: Subtle pulse or rotate, `--duration-slow`
- Background: Inherit from parent container
- Full-panel variant: Centered vertically and horizontally

#### Empty State

```
┌─────────────────────────────────────────────┐
│                                             │
│               📭                            │
│                                             │
│         No alerts found                     │
│                                             │
│   Your security alerts will appear here     │
│   when threats are detected.                │
│                                             │
│          [Run Manual Scan]                  │
│                                             │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 48px, `--text-tertiary`
- Title: `--text-xl`, `--text-primary`, centered
- Description: `--text-base`, `--text-secondary`, centered, max-width 320px
- Action button: Optional, centered below text
- Background: Inherit from parent

#### Error State

```
┌─────────────────────────────────────────────┐
│                                             │
│               ⚠️                            │
│                                             │
│         Failed to load data                 │
│                                             │
│   Unable to connect to the MCP bridge.      │
│   Please check your connection and retry.   │
│                                             │
│          [Retry]  [View Logs]               │
│                                             │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 48px, `--danger`
- Title: `--text-xl`, `--text-primary`, centered
- Description: `--text-base`, `--text-secondary`, centered
- Error details: `--text-sm`, `--text-tertiary`, monospace, collapsible
- Actions: Primary action (Retry) + Secondary action (dismiss/logs)
- Border: Optional 1px `--danger` left border for inline errors

#### Success State

```
┌─────────────────────────────────────────────┐
│                                             │
│               ✅                            │
│                                             │
│         Scan completed                      │
│                                             │
│   No threats detected in your system.       │
│                                             │
│                                             │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 48px, `--success`
- Title: `--text-xl`, `--text-primary`, centered
- Description: `--text-base`, `--text-secondary`, centered
- Auto-dismiss: Optional, 3-5 seconds for toasts
- Background: Subtle `--success` tint at 5% opacity (optional)

#### Warning State

```
┌─────────────────────────────────────────────┐
│ ⚠️ Warning                                  │
├─────────────────────────────────────────────┤
│ High CPU temperature detected (87°C)        │
│                                             │
│ Consider cleaning fans or improving airflow.│
│                                             │
│ [Dismiss]  [View Details]                   │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 20px, `--warning`, inline with title
- Title: `--text-lg`, `--text-primary`
- Description: `--text-base`, `--text-secondary`
- Background: Subtle `--warning` tint at 10% opacity
- Border: 1px `--warning` or left border accent
- Actions: Dismiss + primary action

#### Disconnected State

```
┌─────────────────────────────────────────────┐
│                                             │
│               🔌                            │
│                                             │
│         Connection lost                     │
│                                             │
│   The connection to the LLM proxy was       │
│   interrupted. Reconnecting in 3s...        │
│                                             │
│          [Reconnect Now]                    │
│                                             │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 48px, `--text-tertiary` or `--warning`
- Title: `--text-xl`, `--text-primary`, centered
- Description: `--text-base`, `--text-secondary`, centered
- Auto-retry: Show countdown or progress
- Manual action: Reconnect button
- Banner variant: Compact bar at top of panel

#### Blocked State

```
┌─────────────────────────────────────────────┐
│ 🔒 Action Blocked                           │
├─────────────────────────────────────────────┤
│ This action requires 2FA verification.      │
│                                             │
│ Please authenticate to proceed with         │
│ deleting the API key.                       │
│                                             │
│ [Enter 2FA Code]        [Cancel]            │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 20px, `--danger`
- Title: `--text-lg`, `--text-primary`
- Description: `--text-base`, `--text-secondary`
- Background: Subtle `--danger` tint at 5% opacity
- Border: 1px `--danger` left border
- Actions: Required authentication input + cancel

#### Offline State

```
┌─────────────────────────────────────────────┐
│                                             │
│               📡                            │
│                                             │
│         Service offline                     │
│                                             │
│   The Ollama embedding service is           │
│   currently unavailable.                    │
│                                             │
│   Last seen: 2 hours ago                    │
│                                             │
│          [Start Service]                    │
│                                             │
└─────────────────────────────────────────────┘
```

**Specs**:
- Icon: 48px, `--text-tertiary`
- Title: `--text-xl`, `--text-tertiary`, centered
- Description: `--text-base`, `--text-secondary`, centered
- Metadata: Last seen timestamp, status history
- Actions: Start/restart service (if applicable)

### Artifact Drawer Panel

**Purpose**: Slide-out panel for file/artifact management

**Layout**:
```
┌──────────────────────────────────────────────┐
│ 📎 Artifacts                        [✕ Close]│
├──────────────────────────────────────────────┤
│ 🔍 Search artifacts...                       │
├──────────────────────────────────────────────┤
│ 📄 security-scan.log                [↓] [👁]│
│    12.4 KB • PDF • 2 min ago                 │
│                                              │
│ 📊 health-report.pdf                [↓] [👁]│
│    245 KB • PDF • 1 hour ago                 │
│                                              │
│ 📷 screenshot-001.png               [↓] [👁]│
│    1.2 MB • PNG • Yesterday                  │
├──────────────────────────────────────────────┤
│ [📁 Open Folder]         [Clear] [Export All]│
└──────────────────────────────────────────────┘
```

**Specs**:
- Width: 360px (desktop), full-screen (mobile)
- Background: `--base-02` or `--glass-bg` with blur
- Border-left: 1px `--base-04`
- Animation: Slide from right, `--duration-normal`, `--ease-out`
- Header: Sticky, 56px height
- List item: 64px height, hover `--base-03`
- Actions: Download (↓), Preview (👁), both icon buttons

### Audit Strip

**Purpose**: Fixed bottom bar showing recent activity

**Layout**:
```
┌──────────────────────────────────────────────────────────────┐
│ 📝 Settings changed              2 min ago          [History]│
└──────────────────────────────────────────────────────────────┘
```

**Specs**:
- Height: 32px fixed
- Background: `--base-01`
- Border-top: 1px `--base-04`
- Padding: `--space-2` `--space-4`
- Icon: 14px, `--text-secondary`
- Text: `--text-xs`, `--text-secondary`
- Timestamp: Right-aligned
- Action link: Right side, accent color on hover

### Command Palette Modal

**Purpose**: Universal command search and execution

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ 🔍  Search commands, tools, navigation...                   │
├─────────────────────────────────────────────────────────────┤
│ ⚡   Go to Chat                                      [↵]    │
│ 🔒   Go to Security Ops                              [↵]    │
│ ─────────────────────────────────────────────────────────── │
│ 🔧  TOOLS                                                   │
│    security.status                                   [↵]    │
│    system.gpu_status                                 [↵]    │
└─────────────────────────────────────────────────────────────┘
```

**Specs**:
- Max-width: 640px, centered
- Background: `--glass-bg` with `--blur-lg`
- Border-radius: `--radius-xl`
- Shadow: `--shadow-xl`
- Input: 56px height, sticky top
- Section header: `--text-xs`, uppercase, `--text-tertiary`
- Row: 48px height, hover `--base-03` with left accent
- Shortcut: Right-aligned, `--text-tertiary`, monospace

## Responsive Layout Rules

### Breakpoints

| Name | Width | Layout |
|------|-------|--------|
| Desktop XL | ≥1920px | Full 3-column |
| Desktop | 1280-1919px | 2-column |
| Tablet | 1024-1279px | Compact 2-column |
| Mobile | <1024px | Single column |

### Desktop XL (≥1920px)

- Icon rail: Expanded (200px)
- Content: Fluid
- Context sidebar: 320px fixed

### Desktop (1280-1919px)

- Icon rail: Collapsed (56px) default, expandable
- Content: Fluid
- Context sidebar: Collapsible overlay

### Tablet (1024-1279px)

- Icon rail: Collapsed only
- Content: Fluid
- No persistent sidebar

### Mobile (<1024px)

- Icon rail: Bottom navigation (icon only)
- Content: Full width
- Modals: Full screen

## Usage Rules

### Glass Usage

**DO**:
- Use for modals and overlays
- Use for dropdowns
- Use for elevated contextual layers
- Combine with backdrop blur

**DON'T**:
- Use for primary backgrounds
- Use for full-page glass
- Use without sufficient contrast

### Cyan Accent Usage

**DO**:
- Use for live/active states
- Use for real-time indicators
- Use for focus rings (sparingly)

**DON'T**:
- Use as primary brand color
- Use for static elements
- Overuse (diminishes impact)

### Danger State Usage

**DO**:
- Use red for errors and blocked states
- Use stronger treatment for critical actions
- Use 2FA for destructive operations

**DON'T**:
- Use red for non-dangerous emphasis
- Overwhelm with red alerts

## Explicit "Do Not" Rules

### Design Anti-Patterns (Forbidden)

| Anti-Pattern | Why | Alternative |
|--------------|-----|-------------|
| **Pink-forward retro** | Off-brand | Stay in indigo/violet/blue spectrum |
| **Gamer neon** | Unprofessional | Subtle accent colors only |
| **Noisy gradients** | Visual clutter | Solid colors or subtle gradients only |
| **Full-glass UI** | Accessibility issues | Glass only for overlays |
| **Crowded dashboard** | Cognitive overload | Progressive disclosure |
| **Generic SaaS cards** | Boring, undifferentiated | Technical operator aesthetic |
| **Rounded everything** | Too soft | Sharp edges for structure |
| **Shadow-heavy** | Muddy on dark | Glow effects instead |

## Current Design Artifact Register

### Notion Pages

| Page | ID | Purpose |
|------|-----|---------|
| P77 — UI Architecture + Contracts Baseline | 341f793e-df7b-8131-a0da-fbfd846c2cfd | Architecture spec |
| P78 — Midnight Glass Design System + Figma Mapping | 341f793e-df7b-8195-9d71-e7decc230af6 | This document |

### FigJam Boards

| Board | URL | Content |
|-------|-----|---------|
| Bazzite Unified Control Console — Midnight Glass IA | FigJam | Information architecture |
| Midnight Glass UX Structure — Minimal Shell, Deep Capability | FigJam | UX flow diagrams |
| Midnight Glass System Surfaces Pack | FigJam | System surface designs |
| Midnight Glass Component Pass — Core UI Kit | FigJam | Component specifications |

### Canva Concepts

| Concept | URL | Content |
|---------|-----|---------|
| Midnight Glass Software UI Theme – Technical Operator Console | Canva | Visual concept board |
| Midnight Glass Premium UI Concept Board 1 | Canva | Refined concepts |
| Poster - Midnight Glass UI Concept Board | Canva | Master review candidate |

### Implementation Notes

**Renderer-Generated Visual Boards**:
- Previous attempts at AI-generated visual boards have been unstable
- Repo documentation must be detailed enough to support implementation even when visual generation lags
- Design specs in this document are implementation-facing and should be treated as source of truth
- Visual boards in Figma/Canva are reference material, not canonical specs

## Specific Design Decisions to Preserve

### Shell Structure

- ✅ Clean top-level shell (minimal by default)
- ✅ Feature-rich deeper layers (progressive disclosure)
- ✅ Compact top bar (48px height)
- ✅ Collapsed icon rail by default (56px width)
- ✅ Structured secondary navigation (expandable rail)

### Chat Design

- ✅ User/assistant distinction by structure/tone (not loud color blocks)
- ✅ Tool cards distinct from ordinary chat cards
- ✅ Inline tool results (not popovers)

### State Treatment

- ✅ Stronger treatment for blocked/danger states
- ✅ Status chips consistent across shell/settings/cards
- ✅ Glass reserved for elevated contextual layers only
- ✅ Brighter cyan reserved for focus/live states only

## Design Sign-Off Authority

**⚠️ CRITICAL**: Final design sign-off is **user-only**.

OpenCode may:
- Document existing design decisions
- Refine working drafts for clarity
- Suggest implementation improvements
- Create specification documents

OpenCode may NOT:
- Change the locked Midnight Glass direction
- Approve final mockups
- Sign off on visual direction
- Override user design preferences

Any design changes must be:
1. Proposed in working draft form
2. Reviewed by user
3. Approved by user before becoming canonical

## Definition of Done

- [ ] Color tokens documented
- [ ] Typography scale defined
- [ ] Spacing system established
- [ ] Component rules specified
- [ ] Responsive behavior documented
- [ ] "Do not" rules listed
- [ ] Design artifact register created
- [ ] HANDOFF.md updated

## Next Phases

| Phase | Focus | Dependencies |
|-------|-------|--------------|
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

## References

- P77 — UI Architecture + Contracts Baseline (prerequisite)
- AGENT.md — System capabilities
- HANDOFF.md — Current session context
- Notion design pages (see artifact register above)
- FigJam boards (see artifact register above)
- Canva concept boards (see artifact register above)
