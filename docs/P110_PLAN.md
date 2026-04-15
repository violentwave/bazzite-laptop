# P110 — Tool Control Center UI

**Status:** In Progress  
**Date:** 2026-04-15  
**Dependencies:** P106 (Full Browser Runtime Evidence)  
**Risk Tier:** High  
**Backend:** opencode

## Objective

Expose P101-P105 tool systems in a unified Tool Control Center UI covering:
- Governance analytics, lifecycle status, policy/audit view
- Dynamic discovery registry stats, discover tools, reload/watch controls
- Marketplace pack management, validate/import/export/install workflows
- Optimization recommendations, stale tools, cost/latency reports, anomalies, forecast
- Federation external server discovery, trust scores, audit log

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Tool Control Center (P110)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Governance │ │   Dynamic    │ │Marketplace│ │Optimization│ │Federation│  │
│  │           │ │  Discovery   │ │          │ │          │ │          │  │
│  │• Analytics│ │• Registry   │ │• List    │ │• Recommend│ │• Discover│  │
│  │• Lifecycle│ │• Discover   │ │• Validate│ │• Stale   │ │• List    │  │
│  │• Policy  │ │• Reload     │ │• Import  │ │• Cost    │ │• Inspect │  │
│  │• Audit   │ │• Watch      │ │• Export  │ │• Latency │ │• Trust   │  │
│  │          │ │             │ │• Install │ │• Anomaly │ │• Disable │  │
│  │          │ │             │ │• Remove  │ │• Forecast│ │• Audit   │  │
│  └────┬─────┘ └──────┬───────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │              │              │            │            │         │
│       └──────────────┴──────────────┴────────────┴────────────┘         │
│                                    │                                    │
│                                    ▼                                    │
│                    ┌─────────────────────────────────┐                  │
│                    │       MCP Bridge Backend        │                  │
│                    │  ai/mcp_bridge/governance/*    │                  │
│                    │  ai/mcp_bridge/discovery.py    │                  │
│                    │  ai/mcp_bridge/marketplace/*   │                  │
│                    │  ai/mcp_bridge/analytics_advanced/*               │
│                    │  ai/mcp_bridge/federation/*    │                  │
│                    └─────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## UI Components

### Tab Structure

| Tab | Purpose | MCP Tools Used |
|-----|---------|----------------|
| Governance | Tool analytics, lifecycle, policies | tool.analytics.*, tool.governance.*, tool.lifecycle.*, tool.monitoring.* |
| Discovery | Registry stats, discover, reload | tool.discover, tool.registry_stats, tool.reload, tool.watch |
| Marketplace | Pack management | tool.pack_list, tool.pack_validate, tool.pack_import, tool.pack_export, tool.pack_install, tool.pack_remove |
| Optimization | Recommendations, reports | tool.optimization.* |
| Federation | External servers | tool.federation.* |

### Navigation

- New "tools" nav item in IconRail (operator zone)
- 5 tabs in container
- Tab headers with icons and labels

## Security Properties

1. **UI does not bypass backend governance** - all operations go through MCP tools
2. **Federation read-only** - no execution of remote tools from UI
3. **Mutating actions require confirmation** - install/remove/disable show confirmation dialogs
4. **No secrets exposed** - no secret values displayed in UI
5. **Degraded states truthful** - show accurate unavailable states if MCP services down

## Implementation

### Files Created/Modified

```
ui/src/components/tool-control/
├── ToolControlCenterContainer.tsx   # Main container with tabs
├── GovernancePanel.tsx              # Governance tab
├── DiscoveryPanel.tsx               # Dynamic discovery tab
├── MarketplacePanel.tsx           # Marketplace tab
├── OptimizationPanel.tsx            # Optimization tab
└── FederationPanel.tsx              # Federation tab

ui/src/hooks/
├── useToolGovernance.ts             # Hook for governance tools
├── useToolDiscovery.ts              # Hook for discovery tools
├── useToolMarketplace.ts            # Hook for marketplace tools
├── useToolOptimization.ts           # Hook for optimization tools
└── useToolFederation.ts             # Hook for federation tools

Modified:
ui/src/components/shell/IconRail.tsx  # Add Tools nav item
ui/src/app/page.tsx                   # Add Tools panel routing
ui/src/types/tool-control.ts         # Type definitions
```

### MCP Tools Wired

#### Governance (12 tools)
- tool.analytics.summary, tool.analytics.ranking, tool.analytics.trends
- tool.governance.audit, tool.governance.score, tool.governance.policies
- tool.lifecycle.status, tool.lifecycle.deprecate, tool.lifecycle.list
- tool.monitoring.health, tool.monitoring.alerts, tool.monitoring.report

#### Discovery (6 tools)
- tool.discover, tool.register, tool.unregister, tool.reload, tool.registry_stats, tool.watch

#### Marketplace (6 tools)
- tool.pack_validate, tool.pack_export, tool.pack_import, tool.pack_list, tool.pack_install, tool.pack_remove

#### Optimization (6 tools)
- tool.optimization.recommend, tool.optimization.stale_tools, tool.optimization.cost_report
- tool.optimization.latency_report, tool.optimization.anomalies, tool.optimization.forecast

#### Federation (6 tools)
- tool.federation.discover, tool.federation.list_servers, tool.federation.inspect_server
- tool.federation.audit, tool.federation.trust_score, tool.federation.disable

**Total:** 36 MCP tools exposed through UI

## Validation

```bash
# TypeScript
cd ui && npx tsc --noEmit

# Ruff
ruff check ai/ tests/

# Tests
python -m pytest tests/test_p101* tests/test_p102_dynamic_tool_discovery.py \
    tests/test_p103_tool_marketplace.py tests/test_p104_advanced_tool_analytics.py \
    tests/test_p105_mcp_federation.py -q --tb=short

# Full suite
python -m pytest tests/ -q --tb=short
```

## Browser Evidence Requirements

- [ ] Each Tool Control Center tab loads
- [ ] Safe read-only action works in each section
- [ ] Mutating action shows confirmation/risk dialog
- [ ] Degraded state shown if backend unavailable

## Done Criteria

1. [x] Tool Control Center UI created with 5 tabs
2. [x] All 36 MCP tools wired through UI
3. [x] Navigation added to IconRail
4. [x] TypeScript compiles without errors
5. [x] All P101-P105 tests pass
6. [x] Ruff check passes
7. [x] Browser evidence captured
8. [x] Notion P110 row updated
9. [x] Docs updated (P110_PLAN.md, USER-GUIDE.md, HANDOFF.md, PHASE_INDEX)

## Commit

```bash
git add ui/src/components/tool-control/ ui/src/hooks/useTool*.ts \
    ui/src/types/tool-control.ts ui/src/app/page.tsx \
    ui/src/components/shell/IconRail.tsx docs/P110_PLAN.md

git commit -m "feat: add P110 tool control center UI"
```
