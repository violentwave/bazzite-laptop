# Bazzite Workflow Skill Bundle

Tools for running and listing saved multi-step workflows. Workflows combine
multiple MCP tool calls into a single named, repeatable operation.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `workflow.list` | List available workflows, optionally filtered by status | `status` (optional: active/draft/archived) |
| `workflow.run` | Execute a saved workflow by ID with optional inputs | `workflow_id` (required), `inputs` (optional dict) |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "What workflows are available?" | `workflow.list` |
| "List all active workflows" | `workflow.list` with `status="active"` |
| "Run the morning audit workflow" | `workflow.run` with `workflow_id="morning-audit"` |
| "Execute the deep scan workflow" | `workflow.run` with `workflow_id="deep-scan"` |
| "Run the weekly report workflow" | `workflow.run` with `workflow_id="weekly-report"` |

---

## Safety Rules

- `workflow.list` is read-only and fast.
- `workflow.run` executes the named workflow. Some workflows trigger background
  systemd jobs (e.g., scans, ingestion). They return quickly with a confirmation
  that execution started.
- If `workflow_id` does not exist, the tool returns an error with available IDs.
  Always check `workflow.list` first if you are unsure of the exact ID.
- Workflow inputs are validated against the workflow's parameter schema. Pass
  a dict of key-value pairs matching the workflow's expected inputs.
