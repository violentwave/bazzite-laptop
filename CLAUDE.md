# Bazzite AI Layer — Claude Code Instructions

## Current State (P121 active, 2026-04-16)
- Security Autopilot foundation shipped: **P119** and **P120** complete
- **Active / Next Phase:** P121 — Security Autopilot UI
- **Next Gated Phase:** P122 — Safe Remediation Runner
- Repo: `/var/home/lch/projects/bazzite-laptop/` (ai/ directory)
- **Phase Truth:** `HANDOFF.md` is the lightweight pointer; Notion Bazzite Phases is the primary source of truth

## Read Order
1. `HANDOFF.md` — short session context and current phase pointer
2. Notion Bazzite Phases row for the active phase — authoritative phase scope, dependencies, blockers, validation, approval state
3. `docs/AGENT.md` — architecture, tools, paths, rules (reference, don't memorize)
4. Read other files **on demand only** when a task requires them

## Stack
| Component | Location |
|-----------|----------|
| LLM Proxy | `http://127.0.0.1:8767/v1` (OpenAI-compat, all model calls) |
| MCP Bridge | `http://127.0.0.1:8766` (FastMCP streamable-http; tool count evolves) |
| Python | 3.12, `uv` + `.venv/` only |
| Vector DB | LanceDB at `~/security/vector-db/` → ext SSD |
| Keys | `~/.config/bazzite-ai/keys.env` (names only, NEVER read values) |
| Configs | `configs/litellm-config.yaml`, `configs/ai-rate-limits.json`, `configs/mcp-bridge-allowlist.yaml`, `configs/security-autopilot-policy.yaml` |

## Hard Stops (violations = immediate revert)
1. No `/usr/`, `/boot/`, `/ostree/` writes (immutable OS)
2. No `rpm-ostree upgrade/rebase`
3. No `keys.env` value reads (names/presence only)
4. No `vm.swappiness` changes (ZRAM tuned)
5. No PRIME offload env vars (crash Proton games)
6. No `shell=True` in subprocess (static arg lists only)
7. No `ai.router` imports in `ai/mcp_bridge/` (scoped key loading)
8. No global pip installs (`uv` + `.venv/` only)
9. No local LLM generation (Ollama embed-only, emergency fallback)
10. No API keys in code/scripts/git
11. No arbitrary shell or model-generated command execution
12. No sudo automation
13. No destructive remediation without policy and approval gating

## After Every Code Change
1. `ruff check ai/ tests/ scripts/` — must be clean
2. `python -m pytest tests/ -x -q --tb=short` — must pass unless a pre-existing failure is explicitly documented
3. `restorecon` after any systemd unit install
4. Atomic writes for `~/security/.status` (tempfile + os.replace)
5. All LLM calls through `ai/router.py`, all API calls through `ai/rate_limiter.py`
6. Update repo docs and Notion after verified phase completion

## Prompt Execution Protocol
When executing Claude Code prompts from the user:
1. Read the prompt fully before starting
2. Read `HANDOFF.md`
3. Query the active Notion phase row before implementation
4. Execute each deliverable in order
5. Run verification commands specified in the prompt
6. Report results clearly: pass/fail counts, files modified, blockers
7. Stop at "Do NOT" boundaries — never exceed scope
8. If a prompt says "Done when": verify all conditions before declaring done
9. Do not start the next phase opportunistically

## Plugin Usage

### /feature-dev (primary workflow)
Use for implementation tasks when the user wants Claude Code to build the phase.

### /code-review
Run after implementation is complete. Use for bugs, style issues, and safety review.

### /superpowers:brainstorm
Use when the task requires exploring design options before implementation.
Output goes to the user for review before proceeding.

### /superpowers:write-plan + /superpowers:execute-plan
Use for complex multi-file changes that need a written plan first.
Plan → user reviews → execute.

### /save-handoff
Run at session end. Writes `HANDOFF.md` with session state.
If session-end automation fails or the session crashes, run it manually before closing.

## RuFlo MCP (available globally)
RuFlo CLI at `/home/linuxbrew/.linuxbrew/bin/ruflo`. Available as MCP server.
Use for: complex refactors, security swarms, parallel task dispatch, code/test intelligence.
Do NOT auto-start RuFlo — use it when the active phase benefits from orchestration or deeper analysis.

## Key Architecture Rules
- **2 persistent services only**: `bazzite-llm-proxy.service` + `bazzite-mcp-bridge.service`
- **MCP bridge never imports ai.router** — uses scoped key loading
- **All services bind 127.0.0.1 only** — never 0.0.0.0
- **Output truncated to 4 KB** in tool responses, paths redacted
- **PingMiddleware** (25s keepalive) prevents MCP connection drops
- MCP tools carry readOnly/destructive/openWorld hints where supported
- Notion row properties are authoritative over stale phase page body text

## Git Discipline
- Review staging carefully before committing
- Catch junk: backup files, session logs, `Created:` artifacts, `.pyc`
- Never use `sudo` with git
- Never commit files from `~/security/` or `~/.config/`
- Prefer phase-scoped commit messages, for example: `feat(p121): add security autopilot ui`

## Services After Changes
After modifying Python source in `ai/`:
```bash
bash scripts/deploy-services.sh
systemctl --user restart bazzite-mcp-bridge.service bazzite-llm-proxy.service
```

## Test Commands
```bash
source .venv/bin/activate
python -m pytest tests/ -q --tb=short          # Full suite
python -m pytest tests/ -x -q -k "keyword"     # Targeted
ruff check ai/ tests/ scripts/                  # Lint
python -m pytest tests/test_specific.py -v      # Single file
```

## Context7 Requirement
Always query Context7 MCP **before** writing code that touches:
- LanceDB (API changed between versions — use 0.29+ patterns)
- LiteLLM (router API evolves frequently)
- FastMCP (3.x API differs from 2.x)

## Active Phase Reference

| Phase | Status | Description |
|-------|--------|-------------|
| P119 | Done | Security Autopilot Core — findings, incidents, plans, audit, evidence |
| P120 | Done | Security Policy Engine — modes, allow/approval/block decisions, safe defaults |
| P121 | **Active** | Security Autopilot UI — extend the Unified Control Console Security Ops surface |
| P122 | Gated | Safe Remediation Runner — fixed, allowlisted, policy-approved actions only |

**Phase truth source:** Notion Bazzite Phases database (primary). `HANDOFF.md` points to it.

### Phase-specific reminders
- **P121** should remain UI-first and read-only.
- **P122** must not drift into generic orchestration or arbitrary shell execution.
- Do not treat stale page body text as authoritative when row properties disagree.

Each phase should be executed from its own scoped prompt. Do not reuse older P19–P23 roadmap assumptions.
