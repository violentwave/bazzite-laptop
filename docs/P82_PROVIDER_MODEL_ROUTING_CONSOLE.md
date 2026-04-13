# P82 — Provider + Model Discovery / Routing Console

**Status**: Complete  
**Dependencies**: P79, P81  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Implement the provider and model discovery + routing console for the Unified Control Console. Expose secure runtime provider state, normalized model availability, task-type routing, fallback chains, and provider health in the UI without flattening everything into a generic model picker.

## Summary / Scope

This phase delivers the Provider + Model Discovery / Routing Console — the operational interface for managing LLM providers and routing configuration. The implementation provides real-time provider health, model catalog browsing, and task-type routing visualization.

**Key Features**:
- Provider discovery from secure runtime config (P81 settings service)
- Provider health and auth viability tracking
- Model catalog per provider with normalization
- Task-type routing configuration (fast, reason, batch, code, embed)
- Fallback chain visualization
- Refresh/invalidation after secrets changes
- Local Ollama embed visibility

## Implementation

### Backend Components

#### `ai/provider_service.py` (~450 lines)
Core provider and model management service with three main classes:

**ProviderService**:
- Discovers providers from `keys.env` configuration
- Tracks provider health via integration with `ai/health.HealthTracker`
- Reads LiteLLM routing config from `configs/litellm-config.yaml`
- Generates model catalog across all providers
- Builds routing entries for each task type
- Persists status to `~/security/provider-status.json`

**Known Providers**:
- Google Gemini (gemini)
- Groq (groq)
- Mistral AI (mistral)
- OpenRouter (openrouter)
- z.ai (z.ai)
- Cerebras (cerebras)
- Ollama Local (ollama) — special handling for local embed

**Task Types**:
- `fast` — Speed-first for interactive chat
- `reason` — Reasoning-first for deep analysis
- `batch` — Volume-first for data processing
- `code` — Code-specialized models
- `embed` — Embedding models for vectors

#### MCP Tools Added (5 tools)

**providers.discover**:
- List all providers with configuration and health status
- Returns: id, name, status, is_configured, is_healthy, models, health_score

**providers.models**:
- Get all available models across configured providers
- Returns: id, name, provider, task_types

**providers.routing**:
- Get routing configuration for all task types
- Returns: task_type, primary_provider, fallback_chain, eligible_models, health_state

**providers.refresh**:
- Force a refresh of provider discovery and health
- Triggered automatically when API keys change (via P81 hooks)

**providers.health**:
- Get detailed health metrics for all providers
- Returns: score, success_count, failure_count, consecutive_failures, auth_broken

#### Integration with P81

The provider service integrates with P81's settings service through the `trigger_provider_refresh()` function:

```python
# In settings_service.py
def _trigger_provider_refresh(self, key_name: str) -> None:
    if key_name in llm_keys:
        from ai.provider_service import trigger_provider_refresh
        trigger_provider_refresh(key_name)  # Calls P82 refresh
```

### Frontend Components

#### `ui/src/components/providers/` (~1,500 lines)

**ProvidersContainer.tsx**:
- Main providers panel with tab navigation
- Three tabs: Health, Models, Routing
- Auto-refresh every 30 seconds
- Manual refresh button with loading state
- Summary statistics in header

**ProviderHealthPanel.tsx**:
- Summary cards: Configured, Healthy, Degraded, Blocked
- Provider list with columns: Name, Status, Health Score, Models, Last Error
- Health score visualization with progress bars
- Status indicators with color coding

**ModelCatalogPanel.tsx**:
- Filter by task type and provider
- Grouped by provider cards
- Model badges showing supported task types
- Real-time availability based on provider configuration

**RoutingConsole.tsx**:
- Task type cards with icons (Fast, Reason, Batch, Code, Embed)
- Primary provider and fallback chain visualization
- Eligible models list per task type
- Health state indicators (Healthy, Mixed, Blocked, Cooldown)
- Caveats/warnings display

#### Supporting Files

**`ui/src/types/providers.ts`**:
- TypeScript interfaces for ProviderInfo, ModelInfo, RoutingEntry
- Task type enums and labels
- Provider status types

**`ui/src/hooks/useProviders.ts`**:
- React hook for fetching provider data
- Auto-refresh with 30-second interval
- Manual refresh capability
- Error handling and loading states

### Design Compliance

All components follow P78 Midnight Glass specifications:

**Colors**:
- Provider healthy: `--success` (green)
- Provider degraded: `--warning` (amber)
- Provider blocked: `--danger` (red)
- Provider not configured: `--text-tertiary` (gray)
- Task type icons: `--accent-primary` (indigo)

**Layout**:
- Summary cards: `--base-02` background, `--base-04` border
- Provider rows: Hover state with `--base-03`
- Task type cards: Distinct icons, grouped layout
- Progress bars: Gradient based on health score

**Motion**:
- Loading spinner: `--accent-primary`
- Refresh button: Smooth transitions
- Tab switching: Instant (no animation for data)
- Auto-refresh: Silent background update

## File Structure

```
ai/
├── provider_service.py            # Backend service (450 lines)
├── settings_service.py            # Updated with P82 hooks
├── mcp_bridge/tools.py            # 5 provider tool handlers added
└── health.py                      # Existing (reused)

configs/
├── mcp-bridge-allowlist.yaml      # 5 provider tools added
└── litellm-config.yaml            # Existing routing config (reused)

ui/src/components/providers/
├── ProvidersContainer.tsx         # Main panel (200 lines)
├── ProviderHealthPanel.tsx        # Health view (250 lines)
├── ModelCatalogPanel.tsx          # Model catalog (200 lines)
├── RoutingConsole.tsx             # Routing view (350 lines)
└── index.ts                       # Exports

ui/src/hooks/
├── useProviders.ts                # Provider data hook (100 lines)
└── useChat.ts                     # Existing (P83)

ui/src/types/
├── providers.ts                   # Provider types (50 lines)
└── chat.ts                        # Existing (P83)

ui/src/app/page.tsx                # Updated with ProvidersContainer
```

## Deliverables

- [x] ProviderService with discovery and health tracking
- [x] Integration with existing HealthTracker
- [x] 5 MCP tools for provider operations
- [x] LiteLLM config parsing for routing
- [x] P81 settings service hooks for refresh
- [x] ProvidersContainer with tab navigation
- [x] ProviderHealthPanel with summary cards
- [x] ModelCatalogPanel with filters
- [x] RoutingConsole with task type cards
- [x] useProviders hook with auto-refresh
- [x] TypeScript types for all data structures
- [x] Midnight Glass design compliance
- [x] P82 documentation

## Validation Results

### Backend
```bash
ruff check ai/provider_service.py
```
✅ All checks passed

### Frontend
```bash
cd ui && npx tsc --noEmit
```
✅ No type errors

### Integration
```bash
grep -c "providers\." configs/mcp-bridge-allowlist.yaml
```
✅ 5 tools registered

## Usage

### Viewing Provider Health
1. Navigate to Models & Providers panel
2. Click "Health" tab
3. View summary cards and provider list
4. Check health scores and error states

### Browsing Model Catalog
1. Click "Models" tab
2. Use filters to narrow by task type or provider
3. View grouped models by provider
4. See task type badges for each model

### Checking Routing Configuration
1. Click "Routing" tab
2. View task type cards (Fast, Reason, Batch, Code, Embed)
3. See primary provider and fallback chain
4. Check eligible models per task type
5. Review health state and caveats

### Refreshing Provider State
1. Click "Refresh" button in header
2. Or wait for automatic 30-second refresh
3. State updates when API keys change via P81

## Integration Points

### From P81 (Settings)
When API keys are added/removed in Settings:
1. Settings service calls `trigger_provider_refresh()`
2. Provider service re-discovers all providers
3. Health status is rechecked
4. UI auto-reflects changes within 30 seconds

### To P84 (Security Ops)
Provider health data available for monitoring:
- Provider offline events
- Auth failure tracking
- Health score trends
- Fallback chain activation logs

## Next Phase Ready

**P84 — Security Ops Center** can proceed:
- Provider health monitoring available
- Health tracker integration in place
- Provider status file for persistence
- Audit hooks for security events

## Commit

```
SHA: <to be committed>
Message: P82: Provider + Model Discovery / Routing Console with health tracking and MCP integration
```

## References

- P77 — UI Architecture (Panel specifications)
- P78 — Midnight Glass Design System
- P79 — Frontend Shell Bootstrap
- P81 — PIN-Gated Settings + Secrets Service
- P83 — Chat + MCP Workspace Integration
- ai/health.py — Health tracking foundation
- configs/litellm-config.yaml — Routing configuration
- AGENT.md — System capabilities
- HANDOFF.md — Current session context
