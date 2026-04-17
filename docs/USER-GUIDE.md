# Bazzite AI Layer - User Guide

This guide covers day-to-day operation of the local Bazzite AI control plane.

## Operator Model

- Primary interface: Unified Control Console
- Runtime services: `bazzite-mcp-bridge.service` and `bazzite-llm-proxy.service`
- Host binding: localhost only (`127.0.0.1`)
- Scope: MCP tools, workflows, runbooks, provider routing, and security operations

Historical note: Newelle fallback wrappers and the PySide tray launch path were removed from active runtime support in the 2026-04 cleanup sweep. Historical documents may still mention those surfaces for phase traceability.

## Start and Verify

```bash
bash scripts/deploy-services.sh
systemctl --user restart bazzite-mcp-bridge.service bazzite-llm-proxy.service
```

Quick health checks:

```bash
curl -s http://127.0.0.1:8766/health
curl -s http://127.0.0.1:8767/health
```

Expected: both endpoints return `status: ok`.

## Core Workflows

1. Open the Unified Control Console.
2. Use chat or tool panels to run MCP tools.
3. Use workflow panels for repeatable operations.
4. Use runbook workflows when a task requires explicit human approval steps.
5. Keep high-risk actions policy-gated and audit-visible.

## Security Operations

Common tool families:

- `security.*` for scans, findings, and threat analysis
- `system.*` for host status, updates, and telemetry
- `workflow.*` for orchestrated procedures
- `project.*` for artifacts and phase context
- `settings.*` and `providers.*` for local configuration views

Policy reminders:

- No arbitrary shell execution from model output
- No destructive remediation without policy and approval gates
- No key material in logs, prompts, or commits

## Troubleshooting

If MCP bridge is unavailable:

```bash
systemctl --user status bazzite-mcp-bridge.service
journalctl --user -u bazzite-mcp-bridge.service -n 80 --no-pager
```

If LLM proxy is unavailable:

```bash
systemctl --user status bazzite-llm-proxy.service
journalctl --user -u bazzite-llm-proxy.service -n 80 --no-pager
```

If tests or lint fail after edits:

```bash
source .venv/bin/activate
ruff check ai/ tests/ scripts/
python -m pytest tests/ -x -q --tb=short
```

## Compatibility and History

- Current operations are console-first and workflow-first.
- Legacy Newelle/PySide material is historical and should not be treated as active runtime guidance.
- Phase history and migration rationale remain in `docs/P87_MIGRATION_CUTOVER.md` and `docs/P88_UI_HARDENING_LAUNCH_HANDOFF.md`.
