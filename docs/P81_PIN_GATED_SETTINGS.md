# P81 — PIN-Gated Settings + Secrets Service

**Status**: Complete  
**Dependencies**: P79  
**Risk Tier**: Critical  
**Backend**: opencode  

## Objective

Implement the sensitive settings and backend secrets-management layer for the Bazzite Control Console with PIN-based access control, masked secret display, and comprehensive audit logging.

## Summary / Scope

This phase delivers the PIN-gated settings infrastructure that protects API keys and sensitive configuration. All secret operations require PIN verification, secrets are displayed in masked form by default, and every access is logged to an audit trail.

**Key Features**:
- PIN enrollment and verification with PBKDF2 hashing
- Masked secret display (first 4 + ... + last 4)
- PIN-gated reveal/update/delete operations
- SQLite-based settings storage
- Atomic writes to keys.env
- JSONL audit logging
- Provider refresh hooks (prepared for P82)
- 3-attempt lockout with 5-minute timeout

## Implementation

### Backend Components

#### `ai/settings_service.py` (~550 lines)
Core settings and secrets management service with four main classes:

**PINManager**:
- PBKDF2-SHA256 hashing with 100,000 iterations
- Salt generation and storage in SQLite
- Attempt tracking and lockout enforcement
- 4-6 digit PIN validation

**AuditLogger**:
- JSONL append-only audit log
- Logs: unlock, reveal, replace, add, delete, failure, lockout
- Timestamp and success/failure tracking
- Recent entries query (last N entries)

**SecretsService**:
- Reads/writes to ~/.config/bazzite-ai/keys.env
- Masked value generation (XXXX...XXXX)
- Category-based secret organization
- Atomic file writes (temp + rename)
- Provider refresh hooks for P82 integration

**Public API**:
- `get_pin_manager()` - Singleton PIN manager
- `get_secrets_service()` - Singleton secrets service
- `get_audit_logger()` - Singleton audit logger
- `unlock_settings(pin)` - Verify PIN and log access

#### MCP Tools Added (8 tools)

**settings.pin_status**:
- Check if PIN is configured
- Get current lockout status
- Read-only, idempotent

**settings.setup_pin**:
- Configure new 4-6 digit PIN
- Requires no existing PIN
- Validates digit-only input

**settings.verify_pin**:
- Verify PIN for unlock
- Handles lockout logic
- Logs unlock attempts

**settings.list_secrets**:
- List all secrets with masked values
- Grouped by category
- No PIN required for masked view

**settings.reveal_secret**:
- Reveal full secret value
- Requires PIN verification
- Logs reveal action

**settings.set_secret**:
- Add or update a secret
- Atomic write to keys.env
- Triggers provider refresh hook
- Logs add/replace action

**settings.delete_secret**:
- Remove a secret
- Requires PIN verification
- Logs delete action

**settings.audit_log**:
- Query recent audit entries
- Configurable limit (default 100)

### Frontend Components

#### `ui/src/components/settings/` (~1,200 lines)

**SettingsContainer.tsx**:
- Main settings panel component
- Manages unlock state
- Fetches PIN status and secrets
- Shows setup flow if PIN not configured
- Shows unlock flow if locked
- Renders SecretsList when unlocked
- Displays audit strip at bottom

**PINSetup.tsx**:
- PIN enrollment form
- 4-6 digit validation
- Confirm PIN matching
- Visual feedback for errors
- Security note about lockout

**PINUnlock.tsx**:
- PIN entry with numeric input
- Lockout timer display
- Failed attempt warnings
- Visual lock indicator
- Cancel/Unlock actions

**SecretsList.tsx**:
- Grouped by category (LLM, Threat Intel, etc.)
- Masked value display
- Reveal action (gated by unlock)
- Edit action with inline input
- Delete action with confirmation
- Visual state indicators (set/not set)

### Data Flow

```
User → SettingsContainer → PINUnlock → PIN verified
  ↓
SecretsList displayed with masked values
  ↓
User requests reveal → settings.reveal_secret MCP tool
  ↓
PIN verified again → Full value displayed
  ↓
Action logged to audit.jsonl
```

### Security Model

**PIN Storage**:
- Hashed with PBKDF2-SHA256
- 100,000 iterations
- Unique salt per installation
- Stored in ~/.config/bazzite-ai/settings.db

**Lockout Protection**:
- 3 failed attempts max
- 5-minute lockout duration
- Attempt counter reset on success
- Lockout status returned in all PIN responses

**Secret Display**:
- Default: masked (first 4 + ... + last 4)
- Reveal requires fresh PIN
- No bulk reveal operation
- Values not cached in frontend

**Audit Logging**:
- All actions logged with timestamp
- Success/failure tracking
- Key name association
- Details for failures
- Append-only JSONL format

## File Structure

```
ai/
├── settings_service.py          # Backend service (550 lines)
├── mcp_bridge/
│   └── tools.py                 # MCP tool handlers
└── config.py                    # Existing (unchanged)

configs/
└── mcp-bridge-allowlist.yaml    # Added 8 settings tools

ui/src/components/settings/
├── SettingsContainer.tsx        # Main panel (300 lines)
├── PINSetup.tsx                 # PIN enrollment (150 lines)
├── PINUnlock.tsx                # PIN unlock (180 lines)
├── SecretsList.tsx              # Secret list (250 lines)
└── index.ts                     # Exports

docs/
├── P80_AUTH_2FA_GMAIL.md        # Placeholder for P80
└── P81_PIN_GATED_SETTINGS.md    # This document
```

## Deliverables

- [x] PINManager with PBKDF2 hashing
- [x] SecretsService with masked display
- [x] AuditLogger with JSONL output
- [x] 8 MCP tools for settings operations
- [x] SettingsContainer UI component
- [x] PINSetup and PINUnlock forms
- [x] SecretsList with reveal/edit/delete
- [x] Atomic file writes
- [x] Lockout protection
- [x] Provider refresh hooks
- [x] TypeScript types
- [x] Midnight Glass design compliance

## Validation Results

### Backend
```bash
ruff check ai/settings_service.py
```
✅ All checks passed (20 auto-fixes applied)

### Frontend
```bash
cd ui && npx tsc --noEmit
```
✅ No type errors

### Integration
```bash
grep -n "settings\." configs/mcp-bridge-allowlist.yaml | wc -l
```
✅ 8 tools registered

## Usage

### Setting up PIN (first time)
1. Navigate to Settings panel
2. Click "Set Up PIN" button
3. Enter 4-6 digit PIN
4. Confirm PIN
5. PIN is stored hashed in settings.db

### Unlocking settings
1. Click "Unlock Settings" button
2. Enter PIN
3. If correct: settings unlock for session
4. If incorrect: attempt counter increments
5. After 3 failures: 5-minute lockout

### Revealing a secret
1. Ensure settings are unlocked
2. Click eye icon next to secret
3. Enter PIN in prompt
4. Full value displayed temporarily

### Updating a secret
1. Ensure settings are unlocked
2. Click edit icon
3. Enter new value
4. Click save
5. Enter PIN to confirm
6. Value written atomically to keys.env

## Audit Log Format

```jsonl
{"timestamp": "2026-04-13T10:30:00", "action": "unlock", "key_name": null, "success": true}
{"timestamp": "2026-04-13T10:31:15", "action": "reveal", "key_name": "GROQ_API_KEY", "success": true}
{"timestamp": "2026-04-13T10:32:30", "action": "replace", "key_name": "GEMINI_API_KEY", "success": true}
```

## Integration Points

### For P82 (Provider + Model Discovery)
SecretsService includes `_trigger_provider_refresh()` method that:
- Detects LLM key changes
- Logs refresh trigger
- Placeholder for P82 provider manager integration

### For P80 (Auth/2FA/Gmail)
Settings service provides foundation:
- PIN verification can be extended to 2FA
- Audit logging supports security event tracking
- Lockout mechanism can trigger Gmail notifications

## Next Phase Ready

**P82 — Provider + Model Discovery / Routing Console** can proceed:
- Settings infrastructure complete
- Secret management functional
- Provider refresh hooks in place
- API keys accessible via MCP tools

## Commit

```
Backend: 4a8f2ba P81: Settings Service backend with PIN auth, masked secrets, and audit logging
Frontend: 3cde9df P81: Settings UI components with PIN unlock, masked secrets, and audit strip
```

## References

- P77 — UI Architecture (Security model)
- P78 — Midnight Glass Design System
- P79 — Frontend Shell Bootstrap
- P83 — Chat + MCP Workspace Integration (reconciled)
- AGENT.md — System capabilities
- HANDOFF.md — Current session context
