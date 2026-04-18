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
2. Start from the `Home Dashboard` to select/create a project, review recent chat threads, and check live runtime/security widgets.
3. Enter `Chat Workspace` for project-bound execution and tool-assisted operator work.
4. Use workflow panels for repeatable operations.
5. Use runbook workflows when a task requires explicit human approval steps.
6. Keep high-risk actions policy-gated and audit-visible.

### Home vs Chat responsibilities

- `Home Dashboard`: operator entry surface (project select/create, recent threads, health/security/runtime widgets, quick navigation) with Guided/Standard/Expert presets.
- Home widgets are customizable in-session via `Add Widget` and per-widget `Remove` controls; `Reset Layout` restores the selected preset default.
- `Chat Workspace`: active execution surface (bound provider/model/mode/project, operator actions, tool traces, degraded-state visibility).
- Chat header is summary-first: current thread + project context, compact runtime strip, and collapsible diagnostics/advanced controls.
- Thread organization (rename/move/archive/project assignment) is managed from the `Thread Rail` inside Chat Workspace.
- Thread rail views are explicit: `Active` groups into pinned/recent/by-project, and `Archived` is a dedicated restore-focused view.
- Thread bulk operations are local-first and explicit: enter `Select` mode in the Threads sidebar to merge, move, or archive multiple threads.
- Thread merge is chronological and auditable: merged threads retain source IDs in message metadata and require explicit project choice for cross-project merges.
- Archive destination is explicit: archived threads move to the `Archived` section in the Threads sidebar and return via thread actions `Restore`.

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

## Provenance Queries

Use provenance tools to answer timeline and attribution questions across
security/workbench/phase flows:

- `provenance.timeline` for scoped event history
- `provenance.explain` for why/evidence chain around one record
- `provenance.what_changed` for scoped git/test/artifact/handoff deltas

All provenance queries require `workspace_id` and support optional
`actor_id`/`project_id`/`session_id` filters to enforce scoped retrieval.

## Data Retention and Privacy

The system stores data across 7 retention classes:

| Data Class | Retention | Description |
|------------|-----------|-------------|
| security_findings | 90 days | Scan results, CVE reports |
| incidents | 365 days | Active and resolved incidents |
| plans | 180 days | Remediation action tracking |
| audit_logs | 730 days | Compliance audit trail |
| agent_artifacts | 90 days | Agent workbench content |
| knowledge_base | 365 days | RAG vector store |
| provenance | 365 days | Provenance records |

All outbound data is redacted for secrets (api_key, token, sk-*, xoxb-*), paths (/home/*, /var/home/*, /root/*), and PII before display or export.

## Exporting Data

Export bundles include:
- Export timestamp and source metadata
- SHA256 integrity hash
- Redacted content only (no raw secrets/paths)

Use the retention manager to generate compliant export bundles.

## Deployment Profiles

Validate your deployment with profiles:

```bash
source .venv/bin/activate
python -m pytest tests/test_deployment_profiles.py -q
```

Three profiles available:
- **local-only**: Core services (LLM proxy, MCP bridge)
- **security-autopilot**: + Security scanning
- **agent-workbench**: + Agent Workbench

See `docs/deploy/profiles.md` for full startup/shutdown/troubleshooting docs.

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

If the console appears as unstyled white HTML during local UI development:

```bash
bash scripts/start-console-ui.sh
```

The launcher uses a stable dev path that clears stale Turbopack chunk caches before startup.

For browser checks on `http://127.0.0.1:3000`, dev-origin access is explicitly allowed so HMR/runtime assets are not blocked during local validation.

## Compatibility and History

- Current operations are console-first and workflow-first.
- Legacy Newelle/PySide material is historical and should not be treated as active runtime guidance.
- Phase history and migration rationale remain in `docs/P87_MIGRATION_CUTOVER.md` and `docs/P88_UI_HARDENING_LAUNCH_HANDOFF.md`.
