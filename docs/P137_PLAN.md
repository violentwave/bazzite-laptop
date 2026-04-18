# P137 Plan — Deployment Profiles and Environment Packaging

## Objective

Package the system into repeatable local deployment profiles for the Bazzite laptop and optional future machines, including services, UI launch, env checks, project roots, and workbench profiles.

## Dependencies

- P124 (Agent Workbench Core)
- P129 (Context Isolation)
- P135 (Integration Governance)
- P136 (Retention, Privacy, and Export Controls)

## Risk Tier

**medium** — Service and deployment configuration.

## Execution Mode

**bounded** — Predefined profiles with fixed validation checks.

## Scope Boundaries

### Implement (in scope)
- Three deployment profiles: local-only, security-autopilot, agent-workbench
- Service health validation
- Key presence validation (without printing secrets)
- MCP and LLM health endpoint checks
- UI build readiness
- Project root validation
- Workbench configuration validation

### Do NOT implement (out of scope)
- P138 or P139 work
- Secrets in profiles/docs/scripts
- Auto-start automation without approval

## Implementation Shape

### Modules Created/Modified

| Module | Purpose |
|--------|---------|
| `ai/deployment_profiles.py` | Profile registry, validation checks, fail-closed behavior |
| `tests/test_deployment_profiles.py` | 21 tests covering profiles, validation, safety |
| `docs/deploy/profiles.md` | Operator-facing deployment documentation |

### Profiles

| Profile | Services | Checks |
|---------|----------|--------|
| local-only | bazzite-llm-proxy, bazzite-mcp-bridge | MCP 8766, LLM health, repo root, venv |
| security-autopilot | + local-only | + API keys configured |
| agent-workbench | + local-only | + workbench config |

### Validation Checks

| Check | Type | Fail on Missing |
|-------|------|------------|
| service:active | critical | yes |
| mcp:port | critical | yes |
| llm:health | critical | yes |
| repo:root | critical | yes |
| python:venv | critical | yes |
| key:presence | warn | no |
| workbench:config | warn | no |

## Validation Commands

```bash
ruff check scripts/ ai/ tests/
.venv/bin/python -m pytest tests/test_deployment_profiles.py -q
cd ui && npm run build
```

## Done Criteria

- [ ] All 21 deployment profile tests pass
- [ ] Ruff check passes
- [ ] UI build passes
- [ ] Three profiles implemented
- [ ] Fail-closed on missing critical dependencies
- [ ] No secrets exposed in validation output
- [ ] Startup/shutdown/troubleshooting documented