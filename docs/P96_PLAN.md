# P96 — Figma MCP + Design Artifact Reconciliation

> Phase status: **Done**
> Completed: 2026-04-14

## Objective

Establish a direct Figma integration path for OpenCode using a Figma personal access token, reconcile the Bazzite Figma project against the Midnight Glass Design Lab inventory, and produce a missing-artifact report.

## Security Alert

**The Figma PAT was exposed in the initial prompt. It must be rotated immediately.** The token was never stored in code, logs, or commits. All access goes through `ai/config.py`'s `get_key("FIGMA_PAT")` which reads from `~/.config/bazzite-ai/keys.env` at runtime.

## Artifacts

| Type | Path | Description |
|------|------|-------------|
| Service | `ai/figma_service.py` | Figma REST API integration (406 lines) |
| Tests | `tests/test_figma_service.py` | 18 test cases |
| Config | `configs/mcp-bridge-allowlist.yaml` | 6 new Figma tool definitions |
| Config | `ai/config.py` | `FIGMA_PAT` added to `KEY_SCOPES` |
| Handler | `ai/mcp_bridge/tools.py` | 6 Figma tool handlers |

## MCP Tools Added

| Tool Name | readOnly | Description |
|-----------|----------|-------------|
| `figma.list_teams` | true | List Figma teams accessible to the PAT |
| `figma.list_projects` | true | List projects in a Figma team |
| `figma.list_project_files` | true | List files in a Figma project |
| `figma.get_file` | true | Get file metadata and page list |
| `figma.find_project` | true | Find Bazzite project by name |
| `figma.reconcile` | true | Reconcile Midnight Glass artifacts vs actual project |

## Expected Midnight Glass Artifacts (12)

1. Midnight Glass - Color Tokens
2. Midnight Glass - Typography
3. Midnight Glass - Spacing & Grid
4. Midnight Glass - Components
5. Midnight Glass - Panels
6. Midnight Glass - Chat Workspace
7. Midnight Glass - Shell Gateway
8. Midnight Glass - Security Dashboard
9. Midnight Glass - Provider Cards
10. Midnight Glass - Settings Panels
11. Midnight Glass - Motion & Transitions
12. Midnight Glass - Iconography

## Figma REST API Limitations

The Figma REST API is **read-only** for project/file structure operations:

- **Cannot** create new Figma files via API
- **Cannot** duplicate files via API
- **Cannot** move files between projects via API
- **Can** list teams, projects, files, and retrieve file metadata
- **Can** read file content and node data (read-only)

This means missing artifacts identified by `figma.reconcile` **must be created manually** in Figma and placed in the target project by the operator.

## Setup

1. Generate a Figma PAT at Settings > Personal access tokens
2. Add `FIGMA_PAT=your_token` to `~/.config/bazzite-ai/keys.env`
3. Restart `bazzite-mcp-bridge.service`
4. Use `figma.find_project` to locate the Bazzite project
5. Use `figma.reconcile` to generate a missing-artifact report

## Reconciliation Workflow

1. `figma.list_teams` → discover team IDs
2. `figma.find_project` → locate the Bazzite project
3. `figma.list_project_files` → list existing files
4. `figma.reconcile` → compare expected vs actual, produce report
5. Manually create any missing artifacts in Figma
6. Re-run `figma.reconcile` to verify completeness

## Tests

18 tests covering PAT handling, API operations, project discovery, reconciliation logic, and default artifacts list. All passing.