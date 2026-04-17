# P124 Validation Evidence

Date: 2026-04-17

## Service Checks

Executed before browser capture:

```bash
systemctl --user restart bazzite-mcp-bridge.service bazzite-llm-proxy.service
curl -s http://127.0.0.1:8766/health
curl -s http://127.0.0.1:8767/health
./scripts/start-console-ui.sh
```

Results:
- MCP health: `{"status":"ok","tools":193,"service":"bazzite-mcp-bridge"}`
- LLM health: `{"status":"ok","service":"bazzite-llm-proxy"}`
- UI dev server: running at `http://localhost:3000`

## Required Validation Commands

1) UI typecheck

```bash
cd ui && npx tsc --noEmit
```

Result:
- Pass (no type errors)

2) UI production build

```bash
cd ui && npm run build
```

Result:
- Pass (`Compiled successfully`, static routes generated)

3) Workbench MCP/UI contract tests

```bash
.venv/bin/python -m pytest tests/test_agent_workbench_tools.py -q
```

Result:
- `4 passed`

4) Repo lint

```bash
ruff check ai/ tests/
```

Result:
- `All checks passed!`

## Additional Required Checks

1) P123 regression coverage

```bash
.venv/bin/python -m pytest tests/test_agent_workbench.py -q
```

Result:
- `13 passed`

2) Allowlist YAML parse

```bash
python3 -c "import yaml; yaml.safe_load(open('configs/mcp-bridge-allowlist.yaml')); print('allowlist parse ok')"
```

Result:
- `allowlist parse ok`

## Browser Runtime Evidence (Unified Control Console)

Captured with Playwright against `http://localhost:3000`:

- `docs/evidence/p124/screenshots/01-project-selected.png`
  - Workbench panel open and registered project selected from real list.
- `docs/evidence/p124/screenshots/02-session-created.png`
  - Session created through `workbench.session_create`.
- `docs/evidence/p124/screenshots/03-git-and-tests.png`
  - Git metadata and test command execution surface visible with real output.
- `docs/evidence/p124/screenshots/04-handoff-saved.png`
  - Structured handoff note saved through `workbench.handoff_note`.
- `docs/evidence/p124/screenshots/05-session-stopped.png`
  - Session stop flow completed via `workbench.session_stop`.
- `docs/evidence/p124/screenshots/06-degraded-mcp-offline.png`
  - Truthful degraded-state rendering while MCP bridge was intentionally offline.

## Notes

- No fake projects, sessions, git, or test payloads were used.
- Core flow actions avoid browser-native prompt/confirm dialogs.
- Evidence artifacts avoid raw secret exposure.
