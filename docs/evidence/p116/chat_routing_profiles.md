# P116 — Chat Workspace Routing Profiles

## Overview

P116 adds profile selector to Chat Workspace, showing active route visibility before sending messages.

## Components Created

### ui/src/components/chat/ChatProfileSelector.tsx

Dropdown component with:
- Task type selection: Fast, Reason, Batch, Code, Embed
- Safe localStorage persistence (key: `bazzite-chat-profile`)
- Validation on read (filters invalid stored values)
- Visual icons: Profile, Chevron, Check

### ui/src/hooks/useChatRouting.ts

Hook for routing data:
- Fetches routing from `providers.routing` MCP tool
- Returns `ActiveRoute` with primary provider, fallback chain, health state
- Caches routing data in component state
- Exposes `refresh()` for manual reload

### ui/src/components/chat/ChatRouteInfo.tsx

Route display component:
- Shows active primary provider
- Shows fallback chain
- Color-coded health state (green/yellow/red/gray)
- Caveat tooltip on hover

## Integration

Updated `ChatContainer.tsx` toolbar with:
- `ChatProfileSelector` dropdown
- `ChatRouteInfo` status display
- Profile passed to message send context

## Profile Options

| Profile | Label | Description |
|---------|-------|-------------|
| fast | Fast (Interactive) | Speed-first for chat |
| reason | Reason (Analysis) | Reasoning-first for analysis |
| batch | Batch (Volume) | Volume-first for data |
| code | Code (Generation) | Code-specialized |
| embed | Embed (Vectors) | Vector generation |

## Health State Display

- **green**: healthy
- **yellow**: degraded / cooldown
- **red**: auth-broken / blocked
- **gray**: no-provider configured

## Validation

- TypeScript compile: clean
- Build: passes
- localStorage: validated on read (filters invalid entries)
- Error fallbacks: graceful UI states

## Evidence

- Runtime state sample: `chat_profile_runtime_state.json`