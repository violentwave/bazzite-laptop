# Historical: Newelle System Prompt

This file is retained for migration traceability only.

- Status: deprecated historical artifact
- Runtime role: none
- Last active period: pre-console-first migration and compatibility window

The active operator surface is the Unified Control Console. Runtime wrappers once used by Newelle (`scripts/newelle-exec.sh`, `scripts/newelle-sudo.sh`) are removed and must not be treated as available commands.

For active operations, use:

- MCP bridge tooling via `http://127.0.0.1:8766`
- LLM proxy via `http://127.0.0.1:8767/v1`
- Workflow/runbook APIs exposed by the MCP bridge
