# P87 — Legacy Client Migration + Compatibility Cutover

**Status**: Complete
**Dependencies**: P81, P82, P83, P84, P85, P86
**Risk Tier**: High
**Backend**: opencode

## Objective

Define and execute the UX cutover from legacy-client-first operator guidance to Unified Control Console-first guidance, while preserving runtime compatibility, explicit fallback paths, and rollback safety.

## Scope

P87 is a migration-truth phase. It updates operator-facing truth, cutover policy, and rollback guidance. It does not remove legacy client runtime support.

## Authoritative Interface Decision

- **Primary interface**: Unified Control Console
- **Fallback interface**: Legacy chat/voice client (tool orchestration)
- **Secondary interface**: Legacy tray surface (status awareness)
- **Deferred capabilities**: P80 auth/2FA/Gmail remains deferred unless separately delivered

## Primary UX Threshold

Unified Control Console is considered primary when all of the following are present and documented:

1. Chat + MCP Workspace (P83)
2. PIN-Gated Settings + Secrets Service (P81)
3. Provider + Routing Console (P82)
4. Security Ops Center (P84)
5. Interactive Shell Gateway (P85)
6. Project + Workflow + Phase Panels (P86)

These thresholds are met in repo docs and implementation artifacts.

## Acceptable Temporary Gaps

The following do not block primary-UX cutover:

- P80 auth/recovery/Gmail flows still deferred
- Legacy chat/voice conveniences (voice-centric interaction style)
- Tray-only lightweight status visibility conveniences

These are explicitly documented as non-blocking to avoid false completeness claims.

## Parallel-Run Model

During transition and steady state:

- Unified Control Console is the authoritative operator workflow surface.
- Legacy chat/voice client remains supported for conversational fallback and quick command workflows.
- Legacy tray surface remains supported as low-friction status surface.

### Operator Clarity Rules

- Documentation must use "primary" only for Unified Control Console.
- Legacy chat/voice client must be described as "fallback" or "secondary".
- Legacy tray surface must be described as "secondary status surface".
- No document may imply legacy surfaces are removed while they remain runnable.

## Compatibility Requirements

To preserve migration safety:

- Keep MCP bridge and LLM proxy contracts unchanged.
- Keep local-only single-user assumptions unchanged.
- Keep legacy assistant system prompt and skills operational.
- Keep legacy tray launch path operational.
- Do not fork backend APIs by interface.

## Rollback Model

### Rollback Triggers

Rollback to legacy-primary guidance is triggered if one or more occur:

1. Unified Control Console fails core operator flows (chat, security, shell, phase context)
2. Console introduces blocking reliability regressions in normal daily operation
3. Console guidance causes user confusion severe enough to impact safe operation

### Rollback Path

1. Revert documentation primacy statements first (USER-GUIDE, AGENT, HANDOFF)
2. Restore legacy-client-first quickstart wording while keeping console sections available
3. Keep backend and service topology unchanged (no architectural rollback required)

### Safe-Revert Boundaries

- Safe to revert: documentation labels and runbook ordering
- Unsafe to revert without separate phase: core backend architecture, MCP contracts, tool namespaces

## Deprecation and Support Guidance

| Surface | State | Notes |
|---|---|---|
| Unified Control Console | Primary | Authoritative operator path for daily workflow |
| Legacy chat/voice client | Fallback | Supported for chat/voice and quick tool access |
| Legacy tray surface | Secondary | Supported for glanceable status and alerts |
| Legacy-client-primary docs stance | Deprecated | Replaced by console-first documentation in P87 |

## Documentation Reconciliation Performed

P87 updates guidance so repo truth matches runtime and phase completion:

- Updated `docs/USER-GUIDE.md` to console-first operator stance
- Updated `docs/AGENT.md` legacy-client section to fallback role
- Updated historical legacy-prompt doc at `docs/newelle-system-prompt.md` with compatibility role preface
- Updated phase tracking docs (`HANDOFF.md`, phase index/register, changelog)

## Validation Checklist

- Search for stale primary-language references and reconcile
- Confirm fallback and rollback language exists in operator docs
- Confirm P86/P87 status consistency across docs and handoff
- Confirm no runtime removal is claimed for legacy client surfaces

## Manual/External Steps

Notion status and metadata updates are required after commit creation:

- Ensure P86 = Done (if stale)
- Set P87 = Done
- Record commit SHA
- Add validation summary and blockers/deferred notes (P80 still deferred)

## Outcome

P87 establishes a deliberate, reversible migration stance: Unified Control Console is now the primary documented UX, while legacy client surfaces remain supported as fallback/secondary paths with explicit rollback criteria.

## Historical Supersession

The 2026-04 cleanup sweep removed active legacy wrapper scripts and the legacy tray launch path. This document remains a historical record of the migration posture at the time P87 closed.
