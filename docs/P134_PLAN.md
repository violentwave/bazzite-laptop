# P134 Plan — Self-healing Control Plane

## Objective

Add safe self-healing behavior for service health, stale timers, failed ingestion, degraded provider routing, and known UI/backend contract mismatches using policy-gated fixed actions.

## Dependencies

- P119 (Security Autopilot Core)
- P122 (Safe Remediation Runner)
- P124 (Agent Workbench Core)
- P127 (MCP Policy-as-Code)

## Risk Tier

**high** — Self-healing involves service-level repair actions.

## Execution Mode

**manual-approval** — High-risk or destructive actions require explicit operator approval.

## Scope Boundaries

### Implement (in scope)
- Detection checks for service health, timers, providers, LLM status
- Fixed allowlisted repair actions only
- Policy evaluation on every action
- Cooldown/no-loop prevention
- Audit/evidence emission for every attempt

### Do NOT implement (out of scope)
- Arbitrary shell repair capability
- Uncontrolled retry/repair loops
- Silent "auto-fix succeeded" without visibility
- Bypass of policy/approval gates
- P135, P138, or P139 features

## Implementation Shape

### Modules Created/Modified

| Module | Purpose |
|--------|---------|
| `ai/self_healing.py` | Self-healing coordinator with detection checks, repair actions, cooldown, policy integration |

### Detection Checks

| Check ID | Name | Sensor Tool |
|----------|------|-----------|
| service_health | Service Health Check | system.service_status |
| timer_health | Timer Health Check | agents.timer_health |
| provider_health | Provider Health Check | providers.health |
| llm_status | LLM Status Check | system.llm_status |

### Repair Actions

| Action ID | Name | Risk | Approval Required |
|-----------|------|------|------------------|
| probe_health | Probe Service Health | low | No |
| retry_timer_check | Retry Timer Health Check | low | No |
| retry_provider_discovery | Retry Provider Discovery | low | No |
| request_llm_proxy_restart | Request LLM Proxy Restart | high | Yes |
| request_mcp_bridge_restart | Request MCP Bridge Restart | high | Yes |

### Safety Properties

1. **No arbitrary shell**: All actions are fixed-name, allowlisted
2. **No uncontrolled loops**: Cooldown prevents rapid retry cycles
3. **Approval for destructive**: Restart actions require explicit approval
4. **Audit/evidence**: Every attempt is recorded with IDs
5. **Degraded visibility**: Failed actions show degraded state, not hidden success

## Validation Commands

```bash
.venv/bin/python -m pytest tests/test_self_healing.py -q
ruff check ai/ tests/
```

## Done Criteria

- [ ] All 30 self-healing tests pass
- [ ] Ruff check passes
- [ ] No arbitrary shell actions
- [ ] Cooldown prevents loops
- [ ] Destructive actions blocked without approval
- [ ] Degraded state always visible
- [ ] Test coverage for all safety proofs