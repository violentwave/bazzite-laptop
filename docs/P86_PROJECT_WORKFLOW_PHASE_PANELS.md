# P86 — Project + Workflow + Phase Panels

**Status**: Complete  
**Dependencies**: P75, P79, P81, P82, P83, P84, P85  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Implement the Project + Workflow + Phase workspace for the Unified Control Console, making project execution state a first-class operator surface.

## Summary / Scope

This phase delivers the Project + Workflow + Phase Panels — a unified workspace that exposes:
- Current phase context with blockers and readiness
- Workflow runs and run history
- Artifact and evidence relationships
- Project intelligence / preflight summaries (from P75)
- Next recommended actions
- Cross-links into chat, shell, security ops, and artifact detail

**Key Features**:
- Aggregates data from phase-control, workflow runs, HANDOFF.md, and artifacts
- Reuses P75 preflight intelligence substrate
- Real-time status with 30-second auto-refresh
- Midnight Glass design compliance
- Follow-up paths to chat, shell, and artifacts

## Implementation

### Backend Components

#### `ai/project_workflow_service.py` (~400 lines)

**ProjectWorkflowService**:
- Aggregates data from multiple sources:
  - HANDOFF.md for current phase info
  - Phase documentation files (docs/P*_*.md)
  - Workflow runs from LanceDB
  - Artifacts from artifacts/ directory
- Generates recommendations based on state
- Provides preflight summary integration

**Data Structures**:
- `PhaseInfo`: Current phase with status, blockers, readiness
- `WorkflowRun`: Workflow execution summary
- `ArtifactInfo`: Artifact metadata and source phase
- `ProjectContext`: Complete project state for UI

**MCP Tools (4 tools)**:
- `project.context`: Complete project context (phase, workflows, artifacts, recommendations)
- `project.workflow_history`: Recent workflow runs
- `project.phase_timeline`: Phase timeline from documentation
- `project.artifacts`: Recent artifacts list

### Frontend Components

#### `ui/src/components/project-workflow/` (~900 lines)

**ProjectWorkflowContainer.tsx**:
- Main panel with 3-column responsive layout
- Header with preflight status indicator
- Auto-refresh every 30 seconds
- Error handling display

**CurrentPhaseHeader.tsx**:
- Phase number and name with status badge
- Readiness indicator (ready/blocked/degraded)
- Blockers list
- Next action recommendation
- Backend and risk tier metadata

**WorkflowRunsPanel.tsx**:
- Recent workflow runs list
- Status indicators (pending/running/completed/failed/cancelled)
- Step counts and error messages
- Timestamps with relative formatting

**ArtifactHistoryPanel.tsx**:
- Recent artifacts list
- File type icons
- Size and source phase display
- Timestamp formatting

**PhaseTimelinePanel.tsx**:
- Vertical timeline of phases
- Status indicators per phase
- Active phase highlighting
- Visual timeline connections

**NextActionsPanel.tsx**:
- Recommended actions list
- Priority ordering
- Quick links to chat, shell, security

#### Supporting Files

**`ui/src/types/project-workflow.ts`**:
- TypeScript interfaces for all data structures
- PhaseStatus, WorkflowStatus, ReadinessStatus enums

**`ui/src/hooks/useProjectWorkflow.ts`**:
- React hook for project data
- Parallel data fetching
- Auto-refresh with 30-second interval
- Utility functions (status colors, byte formatting, timestamps)

### Design Compliance

All components follow P78 Midnight Glass specifications:

**Colors**:
- Completed phases: `--success` (green)
- In-progress phases: `--live-cyan` (cyan)
- Ready: `--accent-primary` (indigo)
- Blocked: `--danger` (red)
- Planned: `--text-tertiary` (gray)

**Layout**:
- 3-column grid on desktop (current/actions | timeline | workflows/artifacts)
- Single column on mobile
- Compact headers with status badges
- Card-based organization

**Status Chips**:
- Consistent with P82/P84 patterns
- Color-coded by status
- Pulse animation for active states

## File Structure

```
ai/
├── project_workflow_service.py      # Backend aggregation service
├── mcp_bridge/tools.py              # 4 project tool handlers added

configs/
└── mcp-bridge-allowlist.yaml        # 4 project tools registered

ui/src/components/project-workflow/
├── ProjectWorkflowContainer.tsx     # Main panel (80 lines)
├── CurrentPhaseHeader.tsx           # Phase context (130 lines)
├── WorkflowRunsPanel.tsx            # Workflow list (100 lines)
├── ArtifactHistoryPanel.tsx         # Artifacts list (110 lines)
├── PhaseTimelinePanel.tsx           # Phase timeline (120 lines)
├── NextActionsPanel.tsx             # Actions panel (100 lines)
└── index.ts                         # Exports

ui/src/hooks/
├── useProjectWorkflow.ts            # Project data hook (150 lines)

ui/src/types/
├── project-workflow.ts              # TypeScript types (70 lines)

ui/src/app/page.tsx                  # Updated with ProjectWorkflowContainer
```

## Deliverables

- [x] ProjectWorkflowService with data aggregation
- [x] 4 MCP tools for project operations
- [x] ProjectWorkflowContainer main panel
- [x] CurrentPhaseHeader with readiness indicators
- [x] WorkflowRunsPanel with status display
- [x] ArtifactHistoryPanel with file metadata
- [x] PhaseTimelinePanel with visual timeline
- [x] NextActionsPanel with recommendations
- [x] useProjectWorkflow hook with auto-refresh
- [x] TypeScript types for all data structures
- [x] Midnight Glass design compliance
- [x] Integration with P75 preflight data
- [x] P86 documentation

## Validation Results

### Backend
```bash
ruff check ai/project_workflow_service.py
```
All checks passed

### Frontend
```bash
cd ui && npx tsc --noEmit
```
No type errors

### Integration
```bash
grep -c "project\." configs/mcp-bridge-allowlist.yaml
```
4 tools registered

## Usage

### Viewing Project Context
1. Navigate to Projects & Phases panel via icon rail
2. View current phase context (number, name, status)
3. Check readiness indicator and any blockers
4. Review next recommended action

### Monitoring Workflow Runs
1. View recent workflow runs in right panel
2. Check status, step counts, and timestamps
3. Identify failed runs by error messages

### Tracking Phase Progress
1. View phase timeline in middle column
2. Identify completed, in-progress, and planned phases
3. Active phase highlighted with cyan accent

### Following Up on Actions
1. Review recommended actions list
2. Use quick links to open chat, shell, or security ops
3. Click action items for context

## Integration Points

### From P75 (Preflight Intelligence)
- Reuses preflight gate status
- Integrates with PhaseControlRunner
- Uses existing project-intelligence substrate

### From P81 (PIN-Gated Settings)
- Security-sensitive settings patterns
- Audit logging conventions

### From P82 (Provider Discovery)
- Auto-refresh patterns (30s interval)
- Status chip components
- Panel header patterns

### From P83 (Chat Workspace)
- Panel integration patterns
- Tool result conventions
- Quick link affordances

### From P84 (Security Ops Center)
- Card-based layout patterns
- Status indicator conventions
- Error display patterns

### From P85 (Shell Gateway)
- Audit strip patterns
- Session status concepts
- Follow-up path conventions

## Data Sources

**HANDOFF.md**:
- Current phase detection
- Last updated timestamps

**Phase Documentation (docs/P*_*.md)**:
- Phase names and numbers
- Status inference from file presence
- Timeline generation

**Workflow Runs (LanceDB)**:
- Run status and history
- Step-level progress
- Error tracking

**Artifacts Directory**:
- File metadata
- Source phase tracking
- Size and timestamps

## Security Considerations

- All data sourced from local files only
- No external API calls in aggregation layer
- Read-only access to project files
- File path redaction in outputs

## Next Phase Ready

**P87 — Responsive Polish / Migration Prep** can proceed:
- All 6 primary panels complete
- Consistent design patterns established
- Cross-panel navigation functional
- Ready for responsive refinement

## Commit

```
P86: Project + Workflow + Phase Panels with preflight integration and artifact tracking
```

## References

- P75 — Project Intelligence Preflight + Execution Gating
- P77 — UI Architecture + Trust Boundaries
- P78 — Midnight Glass Design System
- P79 — Frontend Shell Bootstrap
- P81 — PIN-Gated Settings + Secrets Service
- P82 — Provider + Model Discovery
- P83 — Chat + MCP Workspace Integration
- P84 — Security Ops Center
- P85 — Interactive Shell Gateway
- AGENT.md — System capabilities
- HANDOFF.md — Current session context
