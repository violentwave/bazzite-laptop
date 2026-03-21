# Phase B Manual Steps

Commands that cannot be run by Claude Code (require sudo or systemctl).
Run these in a terminal after Claude Code finishes its Phase A changes.

---

## After code changes to MCP bridge or LLM proxy

Restart the affected service(s) to pick up the new code:

```bash
systemctl --user restart bazzite-mcp-bridge.service
systemctl --user restart bazzite-llm-proxy.service
```

---

## First-time setup or after systemd unit file changes

After running `bash scripts/deploy-services.sh` (or editing files in `systemd/`):

```bash
# User services (no sudo)
systemctl --user enable bazzite-llm-proxy.service
systemctl --user enable bazzite-mcp-bridge.service
systemctl --user start bazzite-llm-proxy.service
systemctl --user start bazzite-mcp-bridge.service

# System services (sudo required)
sudo systemctl enable --now system-health.timer
sudo bash scripts/deploy-services.sh
```

---

## After changes to `configs/mcp-bridge-allowlist.yaml` or `configs/litellm-config.yaml`

These files are read at service startup — restart the relevant service:

```bash
systemctl --user restart bazzite-mcp-bridge.service   # allowlist changes
systemctl --user restart bazzite-llm-proxy.service    # litellm-config changes
```

---

## After Newelle system prompt changes

Paste the updated prompt into Newelle manually:

1. Open `docs/newelle-system-prompt.md`
2. Copy the text between the triple-backtick fences
3. In Newelle: Settings → Prompts → System prompt → paste → Save

---

## After Python dependency changes (`requirements.txt` or `pyproject.toml`)

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## Verification (no sudo needed)

Run after any of the above to confirm everything is healthy:

```bash
bash scripts/verify-services.sh
```

---

## Quick reference: service names

| Service | Scope | What it does |
|---|---|---|
| `bazzite-llm-proxy.service` | user | LiteLLM router proxy on :8767 |
| `bazzite-mcp-bridge.service` | user | FastMCP tool bridge on :8766 |
| `system-health.timer` | system | Daily 8AM health snapshot trigger |
| `clamav-freshclam.service` | system | ClamAV signature updater |
