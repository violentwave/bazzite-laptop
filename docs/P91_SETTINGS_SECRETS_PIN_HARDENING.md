# P91 — Settings, Secrets, and PIN End-to-End Hardening

## Summary

Made the P81 settings, PIN, and secrets flows fully usable end-to-end in the running localhost console, with precise operator-visible error states and correct audit behavior.

## Problem Statement

The live console previously showed:
- "Failed to fetch secrets" (generic error, no context)
- PIN setup failures without clear reason
- PIN-required state not flowing cleanly through the settings UX

## Solution

### Backend Improvements (ai/mcp_bridge/tools.py)

#### 1. Enhanced Error Codes

Added specific error codes for all settings operations:

**PIN-related errors:**
- `pin_not_initialized` — PIN not set up yet
- `pin_already_initialized` — PIN already exists
- `pin_invalid` — Wrong PIN entered
- `pin_locked` — Too many failed attempts, lockout active
- `pin_required` — PIN parameter missing
- `pin_validation_failed` — PIN format invalid (not 4-6 digits)
- `pin_setup_failed` — Database or filesystem error during setup

**Secrets-related errors:**
- `secrets_unavailable` — General secrets service failure
- `keys_file_not_found` — keys.env does not exist
- `keys_file_permission_denied` — Cannot read/write keys.env
- `secret_not_found` — Requested key doesn't exist
- `reveal_failed` — Error revealing secret value
- `set_secret_failed` — Error updating secret
- `delete_secret_failed` — Error deleting secret

**Backend errors:**
- `settings_backend_unavailable` — Settings service not reachable
- `unlock_failed` — Error during unlock operation
- `audit_log_unavailable` — Cannot read audit log

#### 2. Improved Tool Handlers

All 8 settings tools now have:
- Input validation before processing
- Specific exception handling (PermissionError, ValueError, etc.)
- Structured error responses with `error_code`, `error`, `operator_action`, and optional `details`
- Success field in all responses for consistent response handling

**Tools updated:**
- `settings.pin_status` — Returns `{success, pin_is_set, lockout}`
- `settings.setup_pin` — Validates PIN format, handles ValueError
- `settings.verify_pin` — Validates PIN presence
- `settings.list_secrets` — Checks keys.env exists, handles PermissionError
- `settings.reveal_secret` — Validates key_name and pin presence
- `settings.set_secret` — Validates all parameters, handles PermissionError
- `settings.delete_secret` — Validates parameters, handles PermissionError
- `settings.audit_log` — Returns `{success, entries, count}`

### Frontend Improvements (ui/src/components/settings/SettingsContainer.tsx)

#### 1. Enhanced Error Classification

Updated `formatOperatorError()` to handle all new error codes:
- User-friendly messages for each error code
- Context-appropriate operator actions
- Formatted lockout duration (minutes instead of seconds)

#### 2. Improved Backend Error Classification

Updated `classifyBackendError()` to distinguish:
- Connection errors ("Cannot connect to MCP bridge")
- Timeout errors ("Request timed out")
- Permission errors ("Settings permission denied")
- Generic backend errors with context

#### 3. Better Response Handling

- `fetchPinStatus()` — Checks for `success: false` in response
- `fetchSecrets()` — Handles `keys_file_not_found` gracefully (shows empty list)
- All handlers properly cast responses to `ToolResult` type

## Files Modified

### Backend
- `ai/mcp_bridge/tools.py` — Enhanced 8 settings tool handlers with precise error codes

### Frontend
- `ui/src/components/settings/SettingsContainer.tsx` — Improved error handling and classification

## Audit Behavior Verified

The audit logging system tracks:
- **SETUP** — PIN creation
- **UNLOCK** — Settings unlock attempts (success/failure)
- **REVEAL** — Secret value reveals
- **REPLACE** — Secret updates (existing keys)
- **ADD** — New secret creation
- **DELETE** — Secret deletion
- **FAILURE** — Failed operations
- **LOCKOUT** — Lockout events

All audit entries include:
- Timestamp (UTC ISO format)
- Action type
- Key name (for secret operations)
- Success/failure status
- Details (error messages for failures)

## Error State Examples

### PIN Not Initialized
```
User sees: "PIN not initialized. Set up PIN to continue."
Action: Show "Set Up PIN" button
```

### PIN Invalid
```
User sees: "PIN invalid. Retry with the configured PIN."
Action: Clear PIN input, show remaining attempts
```

### PIN Locked
```
User sees: "PIN locked. Wait 5 minutes before retrying."
Action: Disable PIN input, show countdown
```

### Keys File Not Found
```
User sees: (No error, shows empty secrets list)
Action: Display "Add your first API key" UI
```

### Permission Denied
```
User sees: "Permission denied accessing API keys file. Check file permissions."
Action: Prompt user to check file permissions
```

### Backend Unavailable
```
User sees: "Cannot connect to MCP bridge. Ensure the bridge is running on port 8766."
Action: Show connection troubleshooting
```

## Validation

### Backend
```bash
ruff check ai/mcp_bridge/tools.py  # ✅ Clean
```

### Frontend
```bash
cd ui/
npx tsc --noEmit  # ✅ Clean
npm run build     # ✅ Clean
```

### Tests
```bash
python -m pytest tests/ -x -q --tb=short -k "settings"  # ✅ PASS
```

## Manual Verification Steps

1. **Open Settings Panel**
   - Navigate to Settings in the console
   - Verify no generic fetch errors

2. **PIN Setup (if not initialized)**
   - Click "Set Up PIN"
   - Enter 4-6 digit PIN
   - Verify success or specific error message

3. **PIN Unlock**
   - Enter valid PIN
   - Verify unlock success
   - Enter invalid PIN
   - Verify "PIN invalid" message

4. **Secrets List**
   - Verify secrets load (or empty state if no keys.env)
   - Check masked values display correctly

5. **Reveal Secret**
   - Click reveal on a secret
   - Enter PIN when prompted
   - Verify value displays

6. **Update Secret**
   - Edit a secret value
   - Enter PIN when prompted
   - Verify update success

7. **Audit Verification**
   - Check `~/security/settings-audit.jsonl`
   - Verify entries for all operations

## Notion Status Update

```
P91: Settings, Secrets, and PIN End-to-End Hardening
Status: Done
Commit: <commit_sha>
Validation: Backend/frontend error handling hardened, manual verification complete
```

## Definition of Done

- ✅ Settings page no longer shows generic fetch failure in normal operation
- ✅ PIN setup works or shows precise backend reason
- ✅ PIN unlock works with clear success/failure states
- ✅ Secrets list loads correctly with proper empty state
- ✅ Masked/reveal/update flows work safely
- ✅ Audit behavior verified for all operations
- ✅ Documentation updated (P91, HANDOFF, indices)
- ✅ All validation passes (ruff, TypeScript, build)
