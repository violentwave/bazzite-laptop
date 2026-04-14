# P84 — Security Ops Center

**Status**: Complete  
**Dependencies**: P79, P81, P82, P83  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Implement the Security Ops Center for the Unified Control Console — a comprehensive operator workspace that surfaces security and ops-relevant signals.

## Summary / Scope

This phase delivers the Security Ops Center with real-time security overview, alert management, scan findings, and provider health monitoring.

**Key Features**:
- Security overview with severity counts and system status
- Alert feed with severity filtering and acknowledgment
- Scan findings history
- Provider health issue tracking
- Real-time data refresh (30-second interval)
- Midnight Glass design compliance

## Implementation

### Backend Components

#### `ai/security_service.py` (~450 lines)

**SecurityService**:
- Aggregates data from security status files
- Reads health logs from system paths
- Calculates security overview with severity counts
- Tracks provider health issues
- Manages alert acknowledgment
- Implements 30-second caching

**Data Structures**:
- `SecurityAlert`: Alert data with severity, category, timestamps
- `ScanFinding`: Scan results with threat counts
- `ProviderHealthIssue`: Provider failures and auth issues
- `SecurityOverview`: Complete security snapshot

#### MCP Tools Added (5 tools)

- `security.ops_overview` - Complete security overview
- `security.ops_alerts` - Get alerts with severity filter
- `security.ops_findings` - Recent scan findings
- `security.ops_provider_health` - Provider health issues
- `security.ops_acknowledge` - Acknowledge alert by ID

### Frontend Components

#### `ui/src/components/security/` (~1,800 lines)

- **SecurityContainer.tsx** - Main panel with tab navigation
- **SecurityOverview.tsx** - Overview with severity counts
- **AlertFeed.tsx** - Alert management with filtering
- **FindingsPanel.tsx** - Scan findings display
- **HealthCluster.tsx** - Provider health monitoring
- **SecurityActionsPanel.tsx** - Actions sidebar

#### Supporting Files

- `ui/src/types/security.ts` - TypeScript interfaces
- `ui/src/hooks/useSecurity.ts` - React hook with auto-refresh

## File Structure

```
ai/
├── security_service.py            # Backend service
├── mcp_bridge/tools.py            # 5 security ops tools

configs/
└── mcp-bridge-allowlist.yaml      # 5 security ops tools added

ui/src/components/security/
├── SecurityContainer.tsx          # Main panel
├── SecurityOverview.tsx           # Overview view
├── AlertFeed.tsx                  # Alert management
├── FindingsPanel.tsx              # Scan findings
├── HealthCluster.tsx              # Health monitoring
├── SecurityActionsPanel.tsx       # Actions sidebar
└── index.ts                       # Exports

ui/src/hooks/
├── useSecurity.ts                 # Security data hook

ui/src/types/
├── security.ts                    # Security types

ui/src/app/page.tsx                # Updated with SecurityContainer
```

## Deliverables

- [x] SecurityService with data aggregation
- [x] 5 MCP tools for security operations
- [x] SecurityContainer with tab navigation
- [x] SecurityOverview with severity counts
- [x] AlertFeed with filtering and acknowledgment
- [x] FindingsPanel with scan results
- [x] HealthCluster with provider monitoring
- [x] SecurityActionsPanel sidebar
- [x] useSecurity hook with auto-refresh
- [x] TypeScript types
- [x] Midnight Glass design compliance
- [x] P84 documentation

## Validation Results

### Backend
```bash
ruff check ai/security_service.py
```
All checks passed

### Frontend
```bash
cd ui && npx tsc --noEmit
```
No type errors

## Usage

Navigate to Security panel via shield icon in the rail.
Use tabs to switch between Overview, Alerts, Findings, and Health views.
Alerts can be filtered by severity and acknowledged.
Data auto-refreshes every 30 seconds.

## Integration Points

- Reuses P82 provider health data
- Integrates with P81 settings/audit system
- Follows P83 chat/tool-result patterns

## Next Phase Ready

**P85 — Projects & Phases** can proceed.

## References

- P77 — UI Architecture
- P78 — Midnight Glass Design System
- P79 — Frontend Shell Bootstrap
- P81 — PIN-Gated Settings
- P82 — Provider Discovery
- P83 — Chat Workspace
