# P92 — Providers + Security Surfaces Live Integration

## Summary

Make provider, model, routing, and security surfaces render live backend truth with structured degraded/manual states instead of blank fetch failures or generic error banners.

## Problem Statement

The P82 (Providers) and P84 (Security) panels currently show:
- Generic "Providers integration failed" or "Security data load failed" errors
- Blank states when backend data is missing or incomplete
- No distinction between different failure modes (auth errors, quota limits, missing files)
- No operator-visible guidance for manual remediation steps

## Solution

Apply the P91 hardening pattern to P82 and P84 surfaces:
1. Specific error codes for each failure mode
2. User-facing operator-visible messages
3. Truthful manual remediation guidance
4. Graceful handling of absent files / absent keys / unavailable providers

## Implementation Plan

### Backend Changes

#### 1. Provider Service Error Handling

Update `ai/provider_service.py` to return structured responses:

```python
# Success
{
    "success": True,
    "providers": [...],
    "counts": {"configured": 3, "healthy": 2, "degraded": 1}
}

# Error
{
    "success": False,
    "error_code": "config_unavailable",
    "error": "LiteLLM config not found",
    "operator_action": "Verify configs/litellm-config.yaml exists"
}
```

Error codes to add:
- `config_unavailable` — LiteLLM config missing/unreadable
- `provider_health_unavailable` — Health tracker data missing
- `refresh_failed` — Provider refresh operation failed

#### 2. Security Service Error Handling

Update `ai/security_service.py` to return structured responses:

Error codes to add:
- `status_file_unavailable` — Security .status file missing
- `alerts_file_unavailable` — alerts.json missing
- `llm_status_unavailable` — llm-status.json missing
- `logs_unavailable` — Log directory not accessible

#### 3. MCP Tool Handlers

Update `ai/mcp_bridge/tools.py` provider/security handlers:
- Add input validation
- Add specific exception handling
- Return structured error responses with `success`, `error_code`, `error`, `operator_action`

Provider tools:
- `providers.discover` — Handle config/health errors
- `providers.models` — Handle model catalog errors  
- `providers.routing` — Handle routing config errors
- `providers.health` — Handle health data errors
- `providers.refresh` — Handle refresh operation errors

Security tools:
- `security.ops_overview` — Handle aggregation errors
- `security.ops_alerts` — Handle alerts file errors
- `security.ops_findings` — Handle findings errors
- `security.ops_provider_health` — Handle provider health errors

### Frontend Changes

#### 1. Type Definitions

Update `ui/src/types/providers.ts`:
```typescript
interface ProvidersResponse {
  success: boolean;
  providers?: ProviderInfo[];
  counts?: ProviderCounts;
  error_code?: string;
  error?: string;
  operator_action?: string;
}
```

Update `ui/src/types/security.ts`:
```typescript
interface SecurityResponse {
  success: boolean;
  data?: SecurityOverview;
  error_code?: string;
  error?: string;
  operator_action?: string;
}
```

#### 2. Hook Updates

Update `useProviders.ts`:
- Check for `success: false` in responses
- Format operator-visible error messages
- Distinguish between backend unavailable vs config missing vs data empty

Update `useSecurity.ts`:
- Same pattern as useProviders
- Handle partial failures (some data available, some not)

#### 3. Component Updates

Update `ProvidersContainer.tsx`:
- Replace generic error banner with specific degraded states
- Show "Config file missing" state with operator action
- Show "Provider auth failed" state with manual remediation
- Show "Quota exceeded" state for Cohere/Gemini issues

Update `SecurityContainer.tsx`:
- Replace generic error with specific states
- Show "Status file not found" if .status missing
- Show "Alerts unavailable" if alerts.json missing
- Show partial data when some sources fail

### Error State Design

#### Provider Error States

**Config Unavailable**
```
Title: Provider Configuration Unavailable
Message: LiteLLM config file not found at configs/litellm-config.yaml
Action: Verify the configuration file exists and is readable
State: degraded
```

**Auth Broken (Gemini)**
```
Title: Gemini Authentication Failed
Message: API key invalid or revoked
Action: Update GEMINI_API_KEY in settings
State: manual (requires operator action)
```

**Quota Exceeded (Cohere)**
```
Title: Cohere Quota Exceeded
Message: API rate limit or quota reached
Action: Check Cohere dashboard or wait for quota reset
State: manual (requires operator action)
```

**Provider Unavailable**
```
Title: Provider Unavailable
Message: Service temporarily unavailable after 5 consecutive failures
Action: Provider is in cooldown. Wait 2 minutes before retry.
State: degraded (auto-recovery expected)
```

#### Security Error States

**Status File Missing**
```
Title: Security Status Unavailable
Message: Security status file not found at ~/security/.status
Action: Run a security scan to generate initial status
State: manual (requires operator action)
```

**Alerts File Missing**
```
Title: Security Alerts Unavailable
Message: Alerts file not found. Alert evaluation may not be running.
Action: Check security-alert.timer is enabled and running
State: manual (requires operator action)
```

**Partial Data**
```
Title: Partial Security Data
Message: Some security data sources are unavailable
Details: Alerts loaded, findings unavailable
State: degraded (some functionality available)
```

## Files to Modify

### Backend
- `ai/provider_service.py` — Structured responses, error handling
- `ai/security_service.py` — Structured responses, error handling
- `ai/mcp_bridge/tools.py` — Provider/security tool handler updates

### Frontend
- `ui/src/types/providers.ts` — Response type updates
- `ui/src/types/security.ts` — Response type updates
- `ui/src/hooks/useProviders.ts` — Error handling
- `ui/src/hooks/useSecurity.ts` — Error handling
- `ui/src/components/providers/ProvidersContainer.tsx` — Degraded states
- `ui/src/components/security/SecurityContainer.tsx` — Degraded states

### Documentation
- `docs/P92_PLAN.md` — This document
- `docs/P92_COMPLETION_REPORT.md` — Post-implementation summary
- `HANDOFF.md` — Phase completion
- `docs/PHASE_INDEX.md` — Phase entry
- `docs/PHASE_ARTIFACT_REGISTER.md` — Artifact inventory

## Validation

### Backend
```bash
ruff check ai/provider_service.py ai/security_service.py ai/mcp_bridge/tools.py
```

### Frontend
```bash
cd ui/
npx tsc --noEmit
npm run build
```

### Tests
```bash
python -m pytest tests/test_mcp_drift.py -v
```

### Manual
1. Open Providers panel
2. Verify each tab handles missing data gracefully
3. Verify auth/quota errors show specific messages
4. Open Security panel
5. Verify each tab handles missing files gracefully
6. Verify counts/chips align with backend

## Definition of Done

- Provider and security surfaces render live backend truth or explicit degraded/manual states
- No generic fetch-failure message remains where structured backend/operator state exists
- Provider-specific issues (Gemini auth, Cohere quota) are visible and correctly explained
- UI chips, counts, and status labels match backend data
- Typecheck passes
- Ruff passes for touched backend files
- MCP drift tests pass
- Documentation updated

## Dependencies

- P90 — Console Runtime Recovery ✅
- P91 — Settings Hardening ✅
- P82 — Provider Service (existing) ✅
- P84 — Security Service (existing) ✅
