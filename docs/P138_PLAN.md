# P138 Plan — Browser/Service Canary Release Automation

## Objective

Automate browser and service canary checks for Security Autopilot and Agent Workbench to catch UI, MCP tools, service health, routing, and policy behavior regressions early.

## Dependencies

- P125 (Full Autopilot Acceptance Gate)
- P134 (Self-healing Control Plane)
- P137 (Deployment Profiles)

## Risk Tier

**high** — Canary validates system health and policy gates.

## Execution Mode

**bounded** — Non-destructive checks only.

## Scope Boundaries

### Implement (in scope)
- Redeploy preflight: deploy services, validate profiles, rebuild UI
- Service health checks: MCP (8766), LLM proxy (8767)
- MCP tool manifest validation
- UI build validation
- Policy gate proof (approval/block enforcement)
- Evidence bundle generation

### Do NOT implement (out of scope)
- P139 work
- GA acceptance language
- Destructive auto-fix

## Implementation Shape

### Modules Created/Modified

| Module | Purpose |
|--------|---------|
| `ai/canary.py` | Canary runner with stages, checks, evidence bundle |
| `scripts/canary.sh` | Operator entry point |
| `tests/test_canary.py` | 14 tests |

### Canary Stages

| Stage | Checks |
|-------|--------|
| preflight | deploy-services.sh, profile validation |
| service_health | MCP 8766, LLM 8767, systemd services |
| mcp_tools | allowlist tools, port listening |
| ui_build | npm run build |
| policy_gates | security-autopilot-policy.yaml approval/block |

### Evidence Bundle

- `canary-bundle.json` — full results
- `canary-summary.txt` — failure summary + troubleshooting

## Validation Commands

```bash
curl -s http://127.0.0.1:8766/health
curl -s http://127.0.0.1:8767/health
cd ui && npm run build
.venv/bin/python -m pytest tests/test_canary.py -q
```

## Done Criteria

- [ ] All 14 canary tests pass
- [ ] All validation commands pass
- [ ] Redeploy preflight functional
- [ ] Evidence bundle generated
- [ ] Failure summary actionable
- [ ] No secrets in output
- [ ] Non-destructive canary