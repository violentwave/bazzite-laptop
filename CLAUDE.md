# Bazzite AI Layer — Claude Code Instructions

## Current State (P21 complete, 2026-04-03)
- **50 MCP tools** + 1 health endpoint
- **1680 tests** (0 failures) · **16 timers** · **6 LLM providers**
- Repo: `/var/home/lch/projects/bazzite-laptop/` (ai/ directory)
- Active roadmap: `docs/phase-roadmap-p19-p23.md`

## Read Order
1. `HANDOFF.md` — session context from previous agent
2. `docs/phase-roadmap-p19-p23.md` — current phase plan (if executing a phase)
3. `docs/AGENT.md` — architecture, tools, paths, rules (reference, don't memorize)
4. Read other files **on demand only** when a task requires them

## Stack
| Component | Location |
|-----------|----------|
| LLM Proxy | `http://127.0.0.1:8767/v1` (OpenAI-compat, all model calls) |
| MCP Bridge | `http://127.0.0.1:8766` (50 tools, FastMCP streamable-http) |
| Python | 3.12, `uv` + `.venv/` only |
| Vector DB | LanceDB at `~/security/vector-db/` → ext SSD |
| Keys | `~/.config/bazzite-ai/keys.env` (names only, NEVER read values) |
| Configs | `configs/litellm-config.yaml`, `configs/ai-rate-limits.json`, `configs/mcp-bridge-allowlist.yaml` |

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

## After Every Code Change
1. `ruff check ai/ tests/ scripts/` — must be clean
2. `python -m pytest tests/ -x -q --tb=short` — must pass
3. `restorecon` after any systemd unit install
4. Atomic writes for `~/security/.status` (tempfile + os.replace)
5. All LLM calls through `ai/router.py`, all API calls through `ai/rate_limiter.py`

## Prompt Execution Protocol
When executing CC prompts from the user:
1. Read the prompt fully before starting
2. Execute each deliverable in order
3. Run verification commands specified in the prompt
4. Report results clearly: pass/fail counts, files modified
5. Stop at "Do NOT" boundaries — never exceed scope
6. If a prompt says "Done when": verify all conditions before declaring done

## Plugin Usage

### /feature-dev (primary workflow)
Use for all implementation tasks. It provides architect + reviewer agents.
Start every prompt with `/feature-dev` unless told otherwise.

### /code-review
Run after implementation is complete. Catches bugs, style issues, security problems.
Always run on the final commit of a phase.

### /superpowers:brainstorm
Use when the task requires exploring design options before implementation.
Output goes to the user for review before proceeding.

### /superpowers:write-plan + /superpowers:execute-plan
Use for complex multi-file changes that need a written plan first.
Plan → user reviews → execute.

### /save-handoff
Run at session end. Writes HANDOFF.md with session state.
Note: SessionEnd hook in `~/.claude/settings.json` auto-triggers this on clean exit.
On crash: run manually before closing terminal.

## RuFlo MCP (available globally)
RuFlo CLI at `/home/linuxbrew/.linuxbrew/bin/ruflo`. Available as MCP server.
Use for: complex refactors, security swarms, parallel task dispatch.
Do NOT auto-start RuFlo — it's manual-only (`/superpowers:*` commands).

## Key Architecture Rules
- **2 persistent services only**: `bazzite-llm-proxy.service` + `bazzite-mcp-bridge.service`
- **MCP bridge never imports ai.router** — uses scoped key loading
- **All services bind 127.0.0.1 only** — never 0.0.0.0
- **Output truncated to 4 KB** in tool responses, paths redacted
- **PingMiddleware** (25s keepalive) prevents MCP connection drops
- **48 tools carry MCP annotations**: readOnly/destructive/openWorld hints

## Git Discipline
- Review staging carefully before committing
- Catch junk: backup files, session logs, `Created:` artifacts, `.pyc`
- Never use `sudo` with git
- Never commit files from `~/security/` or `~/.config/`
- Commit message format: `phase-N: short description` or `fix: description`

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

## Phase Roadmap Reference
Current roadmap: `docs/phase-roadmap-p19-p23.md`
- **P19**: Input validation & MCP safety layer
- **P20**: Headless security & timer sentinel
- **P21**: Code knowledge base expansion
- **P22**: Task pattern learning
- **P23**: Semantic caching & token budget

Each phase: own Claude.ai chat thread generates prompts → user pastes here.
Prompts numbered sequentially continuing from 85.
