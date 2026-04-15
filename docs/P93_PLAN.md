# P93 — Project, Workflow, and Phase Truth Integration

**Status**: ✅ COMPLETE
**Risk Tier**: Medium
**Backend**: opencode

## Objective

Make the project/workflow/phase panel use current HANDOFF and Notion truth, eliminating stale phase badges and placeholder project state. Surface Notion sync degradation clearly rather than hiding it.

## Problem Statement

The Projects & Phases panel (P86) was displaying stale and incorrect phase state:
- HANDOFF.md says `## Current Phase: P92 ✅ COMPLETE` but the UI showed P92 as "current" instead of inferring P93 as next
- No Notion integration — the panel only read local files, never consulting Notion for real-time phase status
- P80 (deferred) was treated as an incomplete blocker rather than a known-deferred phase
- Generic placeholder recommendations appeared when real data was unavailable
- No way to see whether Notion sync was active, stale, or unavailable

## Implementation

### Backend Changes (`ai/project_workflow_service.py`)

1. **Fixed HANDOFF parsing** (`_read_handoff`):
   - Correctly detects when "Current Phase" header points to a completed phase (P92 ✅ COMPLETE)
   - Infers the next phase (P93) as the effective current phase with "ready" status
   - Detects ⏸️ DEFERRED phases and adds them to a `deferred_phases` set
   - Handles "Current Phase" header pointing to a deferred phase (P80 ⏸️ DEFERRED)
   - Tracks both `completed_phases` dict and `deferred_phases` set

2. **Added Notion phase integration** (`_fetch_notion_phases`):
   - Queries `NotionPhaseSync._list_rows()` for real-time phase status
   - Returns `(phases_list, sync_status)` where sync_status is one of: synced, unavailable, degraded, stale
   - Gracefully falls back when Notion API key is not configured
   - Handles connection/permission errors with structured degradation

3. **Fixed `_infer_current_phase`**:
   - Returns tuple `(current_phase, latest_completed_phase)` — not just current
   - Deferred phases are skipped in dependency checks (P80 doesn't block P93)
   - Dependency range starts from earliest known completed phase, not hardcoded P76
   - Status correctly maps: completed→next phase is "ready", deferred→mark as "deferred"
   - Recommendations are derived from actual state, not hardcoded defaults

4. **Enhanced `get_phase_timeline`**:
   - Includes `deferred_phases` in the timeline (previously hidden)
   - Merges Notion phase status when available with local HANDOFF truth
   - Shows `notion_status` per timeline entry when Notion is synced

5. **Enhanced `get_project_context`**:
   - Returns `success: true` (P92 structured error pattern)
   - Includes `latest_completed_phase` alongside `current_phase`
   - Includes `notion_sync_status` and `notion_sync_message`
   - Recommendations reference real state (e.g., "Notion sync unavailable — local HANDOFF.md truth is authoritative")

### Frontend Changes

1. **`ui/src/types/project-workflow.ts`**:
   - Added `deferred` to `PhaseStatus` and `ReadinessStatus`
   - Added `NotionSyncStatus` type: synced | stale | unavailable | degraded
   - Added `LatestCompletedPhase` interface
   - `ProjectContext` now includes `success`, `latest_completed_phase`, `notion_sync_status`, `notion_sync_message`
   - `PhaseTimelineEntry` includes optional `notion_status`
   - `PhaseInfo` includes optional `notion_status`

2. **`ui/src/hooks/useProjectWorkflow.ts`**:
   - Handles `success` field in context response
   - Added `getNotionSyncColor()` utility
   - Added `deferred` handling in `getPhaseStatusColor()`
   - Updated `getReadinessColor()` to handle `deferred` and `in_progress`
   - Error handling for structured responses

3. **`ui/src/components/project-workflow/ProjectWorkflowContainer.tsx`**:
   - Added Notion sync status badge in header (synced/local only/degraded/stale)
   - Added contextual message banner when Notion is not synced
   - Passes `latestCompleted` to `CurrentPhaseHeader`
   - Removed generic placeholder badge behavior

4. **`ui/src/components/project-workflow/CurrentPhaseHeader.tsx`**:
   - Shows latest completed phase (P92 ✅) below current phase
   - Handles `deferred` readiness with appropriate amber styling
   - Handles `in_progress` readiness with cyan styling
   - Shows Notion status override badge when local and Notion status differ
   - No longer shows "No active phase" placeholder when there's real data

5. **`ui/src/components/project-workflow/PhaseTimelinePanel.tsx`**:
   - Handles `deferred` status with amber "Deferred" badge
   - Shows Notion status "N" badge per phase when Notion data differs from local
   - Proper dot coloring for deferred phases

6. **`ui/src/components/project-workflow/NextActionsPanel.tsx`**:
   - Eliminates hardcoded default recommendations ("Initialize phase documentation", etc.)
   - Shows contextual "Awaiting project context" when no real recommendations available
   - Always shows Quick Links even when no actions

### Test Changes

**`tests/test_project_workflow_service.py`** (rewritten for P93):
- 10 comprehensive tests covering:
  - Completed header → next phase inference (P92 COMPLETE → P93 ready)
  - In-progress header → keeps current phase (P93 in progress)
  - Deferred phase detection from header and body lines
  - Deferred dependencies don't block (P80 deferred doesn't block P93)
  - Timeline shows completed, deferred, and ready statuses correctly
  - Notion sync status fields present in context
  - Latest completed phase tracking
  - Recommendations derived from real state
  - MCP endpoint returns `success` and new fields

## Files Modified

- `ai/project_workflow_service.py` — Full rewrite of truth aggregation logic
- `ui/src/types/project-workflow.ts` — Added deferred, Notion sync, latest completed types
- `ui/src/hooks/useProjectWorkflow.ts` — Handle new fields, add utility functions
- `ui/src/components/project-workflow/ProjectWorkflowContainer.tsx` — Notion sync badge, latest completed
- `ui/src/components/project-workflow/CurrentPhaseHeader.tsx` — Latest completed, deferred handling, Notion badge
- `ui/src/components/project-workflow/PhaseTimelinePanel.tsx` — Deferred and Notion badges
- `ui/src/components/project-workflow/NextActionsPanel.tsx` — Remove hardcoded defaults
- `tests/test_project_workflow_service.py` — Full rewrite for P93 truth tests

## Validation

- `ruff check ai/project_workflow_service.py` ✅ PASS
- `npx tsc --noEmit` (ui/) ✅ PASS (0 errors)
- `python -m pytest tests/test_project_workflow_service.py -v` ✅ PASS (10/10)
- `python -m pytest tests/test_mcp_drift.py -q --tb=short` ✅ PASS (4/4)

## Key Design Decisions

1. **Truth hierarchy**: Notion (most current) > HANDOFF (repo truth) > docs/ filesystem (fallback)
2. **Deferred phases**: Tracked separately from completed phases; not counted as blockers
3. **Completed-phase inference**: When HANDOFF says "Current Phase: P92 ✅ COMPLETE", the effective current is P93 (next phase after latest completed)
4. **Notion degradation**: When Notion is unavailable, local HANDOFF is clearly marked as authoritative with "Local only" badge
5. **No fake data**: Removed hardcoded placeholder recommendations; show "Awaiting project context" instead
6. **Structured response**: `project.context` now returns `success: true` and new fields per P92 error pattern