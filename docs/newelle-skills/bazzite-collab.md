# Bazzite Collab Skill Bundle

Tools for managing a collaborative task queue and shared knowledge base.
Useful for tracking work items across sessions and searching accumulated
solutions and notes.

---

## Tools

| Tool | Description | Args |
|------|-------------|------|
| `collab.queue_status` | List pending collaborative tasks and their status | none |
| `collab.add_task` | Add a task to the collaborative queue | `title` (required), `description` (optional), `priority` (optional: low/medium/high) |
| `collab.search_knowledge` | Search shared agent knowledge base for solutions and notes | `query` (string, required) |

---

## Usage Examples

| User says | Tool to call |
|-----------|-------------|
| "What tasks are pending?" | `collab.queue_status` |
| "Show the task queue" | `collab.queue_status` |
| "Add a task: update the security scan schedule" | `collab.add_task` with `title="update security scan schedule"` |
| "Remember to check the GPU driver version next session" | `collab.add_task` with `title="check GPU driver version"` |
| "How did we fix the LanceDB timeout last time?" | `collab.search_knowledge` with `query="LanceDB timeout fix"` |
| "Find any notes about the MCP bridge rate limiting" | `collab.search_knowledge` with `query="MCP bridge rate limiting"` |

---

## Safety Rules

- `collab.add_task` writes to a shared task store. Tasks persist across sessions.
  Use clear, actionable titles.
- `collab.search_knowledge` performs semantic search over accumulated agent
  notes and solutions. Results may reference past sessions.
- Neither tool makes external network calls or modifies system configuration.
