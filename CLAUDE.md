# Bazzite AI Layer — Phase 7 Execution

## READ FIRST (only these two files, nothing else yet)
- docs/phase7-master-plan.md — your mission and CC Prompt Sequence
- docs/bazzite-ai-system-profile.md — hardware constraints (1 page, read fully)

Do NOT read any other files until a prompt step explicitly requires it.
Read files on demand, one at a time, only when needed for the current step.

## STACK (memorize, don't re-read)
- LLM Proxy: http://127.0.0.1:8767/v1 (OpenAI-compatible, all model calls go here)
- MCP Bridge: http://127.0.0.1:8766 (41 tools, use for verify steps)
- Python: uv + .venv/ only
- Repo root: /var/home/lch/projects/bazzite-laptop/
- Keys file: ~/.config/bazzite-ai/keys.env (names only, never read values)

## HARD STOPS
- No /usr/ /boot/ /ostree/ writes
- No rpm-ostree upgrade/rebase
- No keys.env value reads
- No swappiness changes
- No PRIME offload env vars

## PROTOCOL
For each prompt in the CC Prompt Sequence:
1. State what you will do (3 lines max) — wait for "go"
2. Execute, run the plan's verification commands
3. Output ✅/❌ per verification item
4. STOP at every Manual Step gate
