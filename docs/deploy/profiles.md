# Deployment Profiles — Bazzite AI Layer

Repeatable deployment configurations for local Bazzite laptop setups.

## Profiles

### 1. Local Only (Laptop)

Core services only — simplest deployment for local AI assistance.

**Required services:**
- `bazzite-llm-proxy` — LLM proxy (port 8767)
- `bazzite-mcp-bridge` — MCP bridge (port 8766)

**Validation checks:**
- MCP bridge port 8766 listening
- LLM proxy health `http://127.0.0.1:8767/health`
- Repository root exists
- Python venv at `.venv/`

**Startup:**
```bash
bash scripts/deploy-services.sh
systemctl --user restart bazzite-llm-proxy bazzite-mcp-bridge
```

**Validation:**
```bash
curl -sf http://127.0.0.1:8767/health
ss -tln | grep :8766
```

---

### 2. Security Autopilot

Security scanning and remediation — run security scans and get automated findings.

**Required services:**
- `bazzite-llm-proxy`
- `bazzite-mcp-bridge`

**Additional validation:**
- At least one API key configured in `~/.config/bazzite-ai/keys.env`

Supported keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`

**Startup:**
```bash
bash scripts/deploy-services.sh
# Verify keys configured
cat ~/.config/bazzite-ai/keys.env  # NO SECRETS SHOWN - verify presence only
```

**Scanning:**
```bash
# Run security audit
systemctl --user start security-audit.service

# Check findings
curl -s http://127.0.0.1:8766/security_findings | jq
```

---

### 3. Agent Workbench

Project and session management — develop with agentic tooling.

**Required services:**
- `bazzite-llm-proxy`
- `bazzite-mcp-bridge`

**Additional validation:**
- Workbench config at `ai/agent_workbench/config.json`

**Startup:**
```bash
bash scripts/deploy-services.sh
# Verify workbench config
cat ai/agent_workbench/config.json | jq '.projects'
```

**Workbench tools:**
```bash
curl -s http://127.0.0.1:8766/workbench_projects | jq
curl -s http://127.0.0.1:8766/workbench_sessions | jq
```

---

## Common Validation

Run all profile checks via Python:

```bash
source .venv/bin/activate
python -c "
from ai.deployment_profiles import validate_all_profiles, get_profile_summary
results = validate_all_profiles()
for mode, checks in results.items():
    profile = __import__('ai.deployment_profiles').load_profile(mode)
    summary = get_profile_summary(profile)
    print(f'{mode.value}: {summary[\"passed\"]}/{summary[\"total\"]} passed, critical_failed={summary[\"critical_failed\"]}'
"
```

Or run tests:

```bash
.venv/bin/python -m pytest tests/test_deployment_profiles.py -q
```

---

## Startup Sequence

1. **Deploy services** (one-time):
   ```bash
   bash scripts/deploy-services.sh
   ```

2. **Verify services running**:
   ```bash
   systemctl --user status bazzite-llm-proxy bazzite-mcp-bridge
   ```

3. **Run profile validation**:
   ```bash
   .venv/bin/python -m pytest tests/test_deployment_profiles.py -q
   ```

4. **Check health endpoints**:
   ```bash
   curl -sf http://127.0.0.1:8767/health | jq
   ss -tln | grep -E ':876[67] '
   ```

---

## Shutdown Sequence

```bash
# Stop user services
systemctl --user stop bazzite-llm-proxy bazzite-mcp-bridge

# Or disable entirely
systemctl --user disable bazzite-llm-proxy bazzite-mcp-bridge
```

---

## Service Ports

| Service | Port | Endpoint | Health |
|---------|-----|----------|--------|
| LLM Proxy | 8767 | `/v1/*` | `/health` |
| MCP Bridge | 8766 | `/mcp/*` | `ss -tln` |

---

## Troubleshooting

**Services not starting:**
```bash
journalctl --user -u bazzite-mcp-bridge -n 50 --no-pager
```

**Health endpoint failing:**
```bash
curl -v http://127.0.0.1:8767/health
ss -tln | grep :8766
```

**Missing keys:**
```bash
ls -la ~/.config/bazzite-ai/keys.env
```

**Missing venv:**
```bash
ls -la .venv/bin/python
```