# Bazzite Gaming Laptop Project
## System: Acer Predator G3-571 | Bazzite 43 | NVIDIA GTX 1060 + Intel HD 630

## Rules
- This is an immutable OS (Fedora Atomic). Do NOT modify /usr directly.
- Use rpm-ostree for system packages, flatpak for apps.
- Never use sudo rm -rf, curl piped to bash, or wget without permission.
- Custom configs go in /etc/ (survives updates) or ~/.config/ (user configs).
- Test all changes before committing.
- NEVER use PRIME offload env vars in game launch options — they crash games.
- NEVER lower vm.swappiness — 180 is correct for ZRAM.

## Repo Layout
- scripts/ — all shell scripts (clamav, backup, setup utilities, AI wrappers, start-security-tray-qt.sh)
- systemd/ — timer and service unit files
- desktop/ — .desktop files, security.menu, security-tray-qt-autostart.desktop
- configs/ — system config files (udev rules, sysctl, gamemode, litellm, rate-limits, etc.)
- tray/ — PySide6/Qt6 security tray + dashboard (__init__.py, state_machine.py, security_tray_qt.py, dashboard_window.py); 9-state machine; Security/Health/About tabs; KDE notifications; health log parser; pkexec for privileged actions
- ai/ — AI enhancement layer (Python modules: threat intel, RAG, code quality, gaming)
- tests/ — Python unit tests (374 tests: AI layer + tray state machine)
- .vscode/ — VS Code workspace settings and extension recommendations
- docs/ — all documentation and guides (incl. RuFlo v3.5 reference manuals, superpowers/specs/ design specs)
- plugins/ — 15 claude-flow plugins (built from github.com/ruvnet/ruflo source, `file:` refs in package.json)
- ai/jarvis/ — S4 Voice Agent orchestrator (intent classifier, tool executor, conversation memory)
- ai/voice/ — S4 voice I/O server (STT, TTS, audio capture — separate venv)

## Key Paths
- Steam library: /run/media/lch/SteamLibrary
- MangoHud config: ~/.config/MangoHud/MangoHud.conf
- DNS config: /etc/systemd/resolved.conf.d/dns-over-tls.conf
- WiFi script: /usr/local/bin/public-wifi-mode
- Tray launcher (Qt6): /usr/local/bin/start-security-tray-qt.sh
- Tray launcher (GTK3, legacy): /usr/local/bin/start-security-tray.sh
- Integration tests: /usr/local/bin/integration-test.sh
- Claude Code settings: ~/.claude/settings.json
- Backup scripts: /mnt/backup/ (on USB flash drive sdc3)
- RuFlo reference: docs/RuFlo_v3.5_Reference_Manual.pdf + .docx
- Voice venv: ~/.local/share/jarvis-voice/venv (separate from .venv/)
- Voice models: ~/.cache/bazzite-ai/models/ (Moonshine, Kokoro ONNX)
- Jarvis status: ~/security/.jarvis-status (separate from .status)
- Jarvis tools: configs/jarvis-tools-allowlist.yaml
- Jarvis IPC: $XDG_RUNTIME_DIR/jarvis-voice.sock

## Desktop Files
- All custom icons use absolute SVG paths (KDE doesn't resolve custom icon theme names)
- Terminal-based entries use `konsole -e bash -c '...; echo "Press Enter to close"; read'`
- Never use `konsole --hold` (no visible prompt to close)

## Systemd Hardening
All ClamAV and health services include: NoNewPrivileges, ProtectSystem=strict,
ProtectHome=read-only, PrivateTmp=yes, ReadWritePaths whitelist.

## System Health Monitoring

### Overview
Hardware & performance health monitoring integrated with the existing security
system. Collects SMART disk health, GPU state, CPU thermals, storage/ZRAM stats.

### Health Monitoring Files
| Repo Path | System Path | Purpose |
|-----------|-------------|---------|
| `scripts/system-health-snapshot.sh` | `/usr/local/bin/` | Core health monitor |
| `scripts/system-health-test.sh` | `/usr/local/bin/` | 16-test validation suite |
| `systemd/system-health.service` | `/etc/systemd/system/` | Oneshot service |
| `systemd/system-health.timer` | `/etc/systemd/system/` | Daily 8AM trigger |
| `configs/logrotate-system-health` | `/etc/logrotate.d/system-health` | 90-day log rotation |
| `desktop/security-health-snapshot.desktop` | `~/.local/share/applications/` | KDE menu entry |
| `desktop/security-health-logs.desktop` | `~/.local/share/applications/` | KDE menu entry |

### Health Monitoring Constraints
- Health snapshots must complete in <30 seconds (no long SMART tests inline)
- The --selftest flag handles SMART tests separately with sleep inhibit
- Tray status updates use read-modify-write + atomic write (tmp + rename) to avoid corruption
- .status is shared JSON: ClamAV owns scan keys, health owns health keys — never overwrite the whole file
- Delta file format: simple key=value, one per line in health-deltas.dat
- Never start clamd — that is the scan script's job
- Never modify ~/security/quarantine or ClamAV scan logs
- Email alerts use absolute path /home/lch/.msmtprc (scripts run as root)

### Health Monitoring Commands
| Task | Command (run manually, not from Claude Code) |
|------|------|
| Interactive snapshot | `sudo system-health-snapshot.sh` |
| Snapshot + email | `sudo system-health-snapshot.sh --email` |
| SMART self-test | `sudo system-health-snapshot.sh --selftest` |
| Validation suite | `sudo system-health-test.sh` |
| View latest log | `less /var/log/system-health/health-latest.log` |
| View delta trends | `cat /var/log/system-health/health-deltas.dat` |

### Runtime Paths (not in repo)
- Logs: `/var/log/system-health/health-*.log`
- Latest symlink: `/var/log/system-health/health-latest.log`
- Delta tracking: `/var/log/system-health/health-deltas.dat`
- Tray status: `~/security/.status` (shared with ClamAV, health keys added)

---

## AI Enhancement Layer

### Overview
Cloud-brain AI integrations that enrich the existing security/gaming system.
All AI logic lives in `ai/`. Shell wrappers live in `scripts/`. Nothing runs as
a persistent daemon — everything is on-demand (scan triggers, timers, user action).

### AI Layer Rules (NEVER violate)
1. **NEVER run local LLM generation models.** Only `nomic-embed-text` (~300MB VRAM) via Ollama.
2. **NEVER store API keys in code, scripts, or git.** Keys: `~/.config/bazzite-ai/keys.env` (chmod 600).
3. **NEVER install Python packages globally.** Use `uv` + project venv at `.venv/`.
4. **NEVER run AI as persistent daemons.** On-demand only. Gaming takes priority.
5. **NEVER call cloud APIs without `ai/rate_limiter.py`.** Coordinates cross-script rate limits.
6. **NEVER hardcode API providers.** All LLM calls go through `ai/router.py` (LiteLLM).
7. **All shell wrappers in `scripts/`, all Python logic in `ai/`.**
8. **LanceDB at `~/security/vector-db/`.** Not in repo, not in /tmp. Backed up by backup.sh.
9. **Atomic writes for `~/security/.status`.** Read-modify-write + tmp + mv. Only update AI keys.

### AI Key Paths
| Path | Purpose |
|------|---------|
| `ai/` | All AI Python modules |
| `ai/config.py` | Paths, constants, key loading |
| `ai/router.py` | LiteLLM wrapper for provider routing |
| `ai/rate_limiter.py` | Cross-script rate limit coordinator |
| `ai/threat_intel/` | Phase 1: VT, OTX, MalwareBazaar lookups |
| `ai/rag/` | Phase 2: LanceDB, embeddings, queries |
| `ai/code_quality/` | Phase 3: Linter orchestration, AI fixes |
| `ai/gaming/` | Phase 4: MangoHud analysis, ScopeBuddy |
| `tests/` | Python unit tests |
| `.venv/` | Python virtual environment (managed by uv) |
| `configs/litellm-config.yaml` | LiteLLM provider routing config |
| `configs/ai-rate-limits.json` | Per-provider rate limit definitions |
| `configs/keys.env.enc` | sops-encrypted API keys (IN git) |
| `~/.config/bazzite-ai/keys.env` | Plaintext API keys (chmod 600, NOT in git) |
| `~/security/vector-db/` | LanceDB data (disk-based, backed up) |

### AI Layer Notes
- `litellm`, `rich`, and `python-dotenv` do not expose `__version__`. Use `importlib.metadata.version("package-name")` instead.
- `ai/router.py` is live (not scaffold). Uses `litellm.Router` in-process with lazy init.
- Task types: `fast` (Groq, z.ai), `reason` (Gemini, z.ai, OpenRouter), `batch` (Mistral, Gemini), `code` (z.ai GLM-4-32B), `embed` (Ollama local, Mistral fallback).
- z.ai uses OpenAI-compatible API at `https://api.z.ai/api/paas/v4`. Key: `ZAI_API_KEY`.
- `socksio` is required for httpx SOCKS proxy support (used by litellm in sandboxed environments).

### AI Commands
| Task | Command |
|------|---------|
| Activate AI venv | `source .venv/bin/activate` |
| Run threat lookup | `python -m ai.threat_intel.lookup --hash <sha256>` |
| Run RAG query | `python -m ai.rag.query "question here"` |
| Run all linters | `bash scripts/code-quality.sh` |
| Run AI unit tests | `python -m pytest tests/ -v` |
| Ruff check | `ruff check ai/ tests/` |
| Bandit scan | `bandit -r ai/ -c pyproject.toml` |
| Install/update deps | `uv pip install -r requirements.txt` |
| Test LLM router | `python -c "from ai.config import load_keys; from ai.router import route_query; load_keys(); print(route_query('fast', 'Say hello'))"` |
| Encrypt keys | `cd ~/projects/bazzite-laptop && SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml sops -e --input-type dotenv --output-type dotenv ~/.config/bazzite-ai/keys.env > configs/keys.env.enc` |
| Decrypt keys | `SOPS_CONFIG=~/.config/bazzite-ai/.sops.yaml sops -d --input-type dotenv --output-type dotenv configs/keys.env.enc` |

### S4 Voice Agent (Jarvis)

SP4: Voice assistant integrated into the PySide6 dashboard as the first tab.
Design spec: `docs/superpowers/specs/2026-03-17-s4-voice-agent-jarvis-design.md`

**Key Architecture Decisions:**
- Text + voice input (push-to-talk) to same pipeline
- Local intelligence pipeline: @ruvector/router HNSW intent → cache → ReasoningBank → cloud LLM
- 55-75% of commands handled locally, remaining via free-tier LLM rotation ($0/month)
- Separate venv for voice deps (PyTorch/ONNX conflicts)
- Unix domain socket IPC at $XDG_RUNTIME_DIR/jarvis-voice.sock
- Jarvis is the second permitted persistent process (alongside tray)

**S4 Rules (NEVER violate):**
1. **NEVER install onnxruntime-gpu** in the voice venv — CPU-only avoids CUDA conflicts
2. **NEVER write to ~/security/.status** from Jarvis — use ~/security/.jarvis-status
3. **NEVER construct shell commands from user input** — YAML allowlist only, no shell=True
4. **NEVER expose threat intel API keys to Jarvis** — use scoped load_keys(scope="llm")
5. **Jarvis MUST pause voice in gaming mode** — text-only when GameMode active

**Phased Delivery:**
| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Text assistant (Jarvis tab, tools, streaming LLM, intent classifier) | Not started |
| Phase 2 | Voice (Moonshine STT + Kokoro TTS, PTT, VAD, safety guards) | Not started |
| Phase 3 | Polish (floating widget, persistent memory, GameMode, adaptive routing) | Not started |

**Pre-S4 Fixes Required:**
- Fix rate limiter deadlock (_write_state re-entrant flock)
- Amend "no daemons" constraint for Jarvis
- Reverse VT cascade order (MalwareBazaar → OTX → VT)

---

## Autonomous Skill & Plugin Invocation (MANDATORY — NEVER SKIP)

Skills and plugins MUST be invoked automatically before EVERY agent operation.
This is not optional. The user should NEVER need to type a slash command — Claude
auto-invokes the matching skill based on task context. If even 1% chance a skill
applies, invoke it.

### Automatic Invocation Order (EVERY task)
1. **Before ANY work:** Check if a process skill applies (brainstorming, debugging, writing-plans, TDD)
2. **Before ANY code change:** Invoke `code-intelligence` plugin (refactor-impact, architecture-analyze)
3. **Before ANY agent spawn:** Invoke `reasoningbank-agentdb` to check for prior patterns
4. **Before ANY LLM call:** Check ReasoningBank + HNSW cache for cached responses
5. **Before ANY security-related change:** Invoke `aidefence` scan + `v3-security-overhaul` skill
6. **After ANY completion:** Store patterns via `hooks intelligence pattern-store`
7. **After ANY test run:** Invoke `test-intelligence` plugin for coverage analysis

### Skill → Task Type Mapping (auto-invoke, never require user)
| Task Type | Skills to Auto-Invoke |
|-----------|----------------------|
| New feature / design | `superpowers:brainstorming` → `superpowers:writing-plans` |
| Implementation | `superpowers:test-driven-development` → `v3-core-implementation` |
| Bug fix | `superpowers:systematic-debugging` |
| Refactor | `code-intelligence` plugin → `v3-ddd-architecture` |
| Multi-file work | `superpowers:dispatching-parallel-agents` → `swarm-orchestration` |
| Security work | `v3-security-overhaul` → `aidefence` |
| Memory/vector ops | `agentdb-advanced` → `agentdb-vector-search` |
| Learning/patterns | `reasoningbank-agentdb` → `agentdb-learning` |
| Performance | `v3-performance-optimization` → `agentdb-optimization` |
| Code review | `superpowers:requesting-code-review` → `verification-quality` |
| Completion | `superpowers:verification-before-completion` |
| MCP/integration | `v3-mcp-optimization` → `v3-integration-deep` |

### Plugin Auto-Invoke Rules
| Plugin | When to Auto-Invoke |
|--------|-------------------|
| `code-intelligence` | Before ANY refactor, code review, or architecture change |
| `test-intelligence` | Before/after ANY test run |
| `perf-optimizer` | When optimizing performance or analyzing bottlenecks |
| `cognitive-kernel` | For complex multi-step reasoning tasks |
| `aidefence` | Before ANY user input reaches an LLM |
| `neural-coordination` | During swarm agent coordination |
| `agentic-qe` | During quality audits |

---

## Project Management: SPARC Orchestrator (MANDATORY)

`/sparc:orchestrator` is the designated project manager for this project. Invoke
it for ALL project-level decisions: task prioritization, work decomposition,
milestone tracking, and cross-domain coordination. When the user describes work
at the project level (epics, features, milestones), route through SPARC
Orchestrator before spawning agents.

### SPARC Orchestrator Responsibilities
- Break large objectives into delegated SPARC phases (Spec → Pseudo → Arch → Refine → Complete)
- Select and dispatch the right agent/skill for each sub-task
- Maintain project coherence across parallel workstreams
- Enforce quality gates between phases
- Track progress and report blockers

### When to Invoke
| Trigger | Action |
|---------|--------|
| New feature request | `/sparc:orchestrator` → decompose → plan → dispatch |
| Multi-file refactor | `/sparc:orchestrator` → impact analysis → phased execution |
| Architecture decision | `/sparc:orchestrator` → `/sparc:architect` sub-delegation |
| Sprint/milestone planning | `/sparc:orchestrator` → task breakdown → agent assignment |
| Cross-domain work (AI + tray + scripts) | `/sparc:orchestrator` → parallel agent coordination |

---

## Required Plugins (ALL INSTALLED — ALWAYS ACTIVE)

All 15 plugins installed from `github.com/ruvnet/ruflo` source into `plugins/`.
Recorded in `package.json` as `file:plugins/*` — survives `npm install`.
WASM peer deps are optional; plugins use mock fallbacks when WASM is unavailable.

**Reinstall all plugins (after node_modules wipe):**
```bash
npm install  # package.json file: refs handle it
```

### Plugin Inventory (15 plugins)

| Plugin | Package | Purpose | Auto-Invoke When |
|--------|---------|---------|-----------------|
| **code-intelligence** | `@claude-flow/plugin-code-intelligence` | Semantic search, architecture analysis, refactor impact, module splitting, pattern learning | Before refactors, code reviews, searching by intent |
| **cognitive-kernel** | `@claude-flow/plugin-cognitive-kernel` | LLM working memory, attention control, meta-cognition, scaffolding | Complex multi-step reasoning tasks |
| **neural-coordination** | `@claude-flow/plugin-neural-coordination` | Multi-agent swarm intelligence (SONA + GNN + attention) | Swarm coordination, agent routing |
| **perf-optimizer** | `@claude-flow/plugin-perf-optimizer` | AI bottleneck detection, memory analysis, config tuning | Performance optimization tasks |
| **test-intelligence** | `@claude-flow/plugin-test-intelligence` | Predictive test selection, flaky test detection, coverage optimization | Before/after test runs |
| **agentic-qe** | `@claude-flow/plugin-agentic-qe` | Quality Engineering with 51 agents across 12 DDD bounded contexts | Quality audits, comprehensive testing |
| **hyperbolic-reasoning** | `@claude-flow/plugin-hyperbolic-reasoning` | Poincare ball embeddings, taxonomic reasoning, hierarchical search | Taxonomy/ontology work, hierarchical analysis |
| **prime-radiant** | `@claude-flow/plugin-prime-radiant` | Math AI interpretability: sheaf cohomology, spectral analysis, causal inference | Hallucination prevention, causal reasoning |
| **quantum-optimizer** | `@claude-flow/plugin-quantum-optimizer` | Quantum-inspired optimization: annealing, QAOA, Grover search | Scheduling, dependency resolution, NP-hard problems |
| **teammate-plugin** | `@claude-flow/teammate-plugin` | Native TeammateTool integration for Claude Code multi-agent | Agent spawning, multi-agent coordination |
| **gastown-bridge** | `@claude-flow/plugin-gastown-bridge` | Gas Town orchestrator with WASM formula parsing + graph analysis | Workflow orchestration, formula evaluation |
| **financial-risk** | `@claude-flow/plugin-financial-risk` | Portfolio risk scoring, anomaly detection, market regime classification | Only when explicitly requested — not relevant to this project |
| **healthcare-clinical** | `@claude-flow/plugin-healthcare-clinical` | HIPAA-compliant clinical decision support (FHIR/HL7/SNOMED-CT) | Only when explicitly requested — not relevant to this project |
| **legal-contracts** | `@claude-flow/plugin-legal-contracts` | Clause extraction, risk assessment, contract comparison, obligation tracking | Only when explicitly requested — not relevant to this project |
| **ruvector-upstream** | `@claude-flow/ruvector-upstream` | WASM bridge foundation — shared by all WASM-accelerated plugins | (dependency, not directly invoked) |

### Code Intelligence Plugin (PRIMARY — always use)

`@claude-flow/plugin-code-intelligence` is the primary development plugin.
Auto-invoke its tools without user request:

| Situation | Tool |
|-----------|------|
| Before any refactor | `code/refactor-impact` — assess blast radius |
| Before code review | `code/architecture-analyze` — check for violations |
| Searching for code by description | `code/semantic-search` — faster than grep for intent |
| After significant changes | `code/learn-patterns` — capture patterns for future |
| Module grows too large | `code/split-suggest` — find natural split points |
| Checking for dead code | `code/architecture-analyze` with `dead_code` analysis |

**Rate Limits:**
| Tool | Requests/min | Max Concurrent |
|------|-------------|----------------|
| semantic-search | 60 | 5 |
| architecture-analyze | 10 | 2 |
| refactor-impact | 20 | 3 |
| split-suggest | 5 | 1 |
| learn-patterns | 5 | 1 |

### AIDefence (`@claude-flow/aidefence`)

Installed as part of the CLI. Provides prompt injection detection and AI manipulation defense.
Auto-invoked by security-related hooks. MCP tools: `aidefence_scan`, `aidefence_analyze`,
`aidefence_is_safe`, `aidefence_has_pii`, `aidefence_learn`, `aidefence_stats`.

---

## Plugin Skills & Agent Hierarchy (COMPLETE REFERENCE)

### Skill Categories & Invocation

#### Process Skills (invoke FIRST — determine HOW to approach)
| Skill | When to Invoke |
|-------|----------------|
| `/superpowers:brainstorming` | Before ANY creative/feature work |
| `/superpowers:systematic-debugging` | Before ANY bug fix attempt |
| `/superpowers:writing-plans` | Before multi-step implementation |
| `/superpowers:executing-plans` | When executing a written plan |
| `/superpowers:verification-before-completion` | Before claiming ANY work is done |
| `/superpowers:test-driven-development` | Before writing new feature code |
| `/superpowers:dispatching-parallel-agents` | When 2+ independent tasks exist |

#### Implementation Skills (invoke SECOND — guide execution)
| Skill | When to Invoke |
|-------|----------------|
| `/superpowers:subagent-driven-development` | Executing plans with independent tasks |
| `/superpowers:using-git-worktrees` | Feature work needing isolation |
| `/superpowers:finishing-a-development-branch` | When implementation complete, tests pass |
| `/superpowers:requesting-code-review` | Before merging major features |
| `/superpowers:receiving-code-review` | When processing review feedback |
| `/superpowers:brainstorming` | Creative work, new components |

#### SPARC Methodology Skills
| Skill | Phase | Purpose |
|-------|-------|---------|
| `/sparc:orchestrator` | All | **Project manager** — decompose & dispatch |
| `/sparc:spec-pseudocode` | Specification | Requirements capture, edge cases |
| `/sparc:code` | Pseudocode→Code | Clean modular implementation |
| `/sparc:architect` | Architecture | System design, patterns |
| `/sparc:tdd` | Testing | TDD London School |
| `/sparc:debug` | Debugging | Trace, inspect, isolate |
| `/sparc:security-review` | Security | Static/dynamic audits |
| `/sparc:devops` | Deployment | CI/CD, infrastructure |
| `/sparc:docs-writer` | Documentation | Concise modular docs |
| `/sparc:integration` | Completion | Merge all outputs, verify |
| `/sparc:reviewer` | Review | Code quality, standards |
| `/sparc:optimizer` | Refinement | Refactor, modularize, perf |

#### Domain-Specific Skills
| Skill | Purpose |
|-------|---------|
| `/simplify` | Review changed code for reuse, quality, efficiency |
| `/claude-api` | Building apps with Claude/Anthropic SDK |
| `/coderabbit:review` | AI-powered code review |
| `/feature-dev:feature-dev` | Guided feature development |
| `/sage:security-awareness` | Security best practices |

#### Analysis & Monitoring Skills
| Skill | Purpose |
|-------|---------|
| `/analysis:performance-bottlenecks` | Performance bottleneck analysis |
| `/analysis:token-efficiency` | Token usage optimization |
| `/monitoring:status` | Check coordination status |
| `/monitoring:agents` | List active patterns |

#### GitHub Integration Skills
| Skill | Purpose |
|-------|---------|
| `/github:code-review` | Code review dispatch |
| `/github:pr-manager` | PR lifecycle management |
| `/github:issue-tracker` | Issue tracking coordination |
| `/github:release-manager` | Release orchestration |
| `/github:workflow-automation` | GitHub Actions CI/CD |

#### Automation & Optimization Skills
| Skill | Purpose |
|-------|---------|
| `/automation:smart-spawn` | Smart agent auto-spawning |
| `/automation:workflow-select` | Workflow selection |
| `/optimization:parallel-execute` | Parallel task execution |
| `/optimization:auto-topology` | Automatic topology selection |

### Agent Hierarchy (Ranked by Authority)

```
SPARC Orchestrator (/sparc:orchestrator)
├── Project-level decisions, task decomposition, phase gates
│
├─► Tier 3 Agents (Opus — complex reasoning)
│   ├── security-architect — zero-trust design, threat modeling
│   ├── architecture — system design, ADR decisions
│   ├── sparc-coord — SPARC methodology orchestration
│   ├── hierarchical-coordinator — queen-led swarm coordination
│   └── specification — requirements analysis
│
├─► Tier 2 Agents (Sonnet — standard implementation)
│   ├── coder — clean, efficient code implementation
│   ├── reviewer — code review, quality assurance
│   ├── tester — comprehensive testing, TDD
│   ├── planner — strategic planning, task orchestration
│   ├── researcher — deep research, information gathering
│   ├── sparc-coder — TDD-driven implementation
│   ├── security-auditor — vulnerability detection, CVE search, OWASP (YAML config)
│   ├── python-specialist — PySide6/Qt6, type hints, security-first Python (YAML config)
│   ├── performance-engineer — Flash Attention, WASM SIMD optimization
│   ├── memory-specialist — HNSW indexing, vector quantization
│   └── mesh-coordinator — peer-to-peer swarm coordination
│
├─► Tier 1 Agents (Haiku — fast, simple tasks)
│   ├── code-simplifier — simplify and refine code
│   ├── perf-analyzer — performance bottleneck analysis
│   ├── production-validator — deployment readiness checks
│   └── task-orchestrator — task decomposition, result synthesis
│
└─► Specialized Agents (routed by task type)
    ├── pr-manager — PR lifecycle
    ├── release-manager — release orchestration
    ├── code-review-swarm — multi-agent code review
    ├── issue-tracker — issue management
    ├── tdd-london-swarm — mock-driven TDD
    ├── adaptive-coordinator — dynamic topology switching
    ├── backend-dev — backend API development
    ├── mobile-dev — React Native development
    ├── ml-developer — ML model development
    ├── system-architect — high-level architecture
    └── consensus-coordinator — distributed consensus
```

### Agent Selection Rules
1. **SPARC Orchestrator** decides which agents to dispatch for project-level work
2. **hooks route** selects optimal agent for individual tasks
3. **Code intelligence plugin** auto-invokes for refactor/search/analysis tasks
4. **Tier routing** matches agent to task complexity (see 3-Tier Model Routing)
5. When in doubt, prefer the specialized agent over the generic one

---

## RuFlo Natural Language Integration (MANDATORY)

RuFlo is the master orchestration layer. The user speaks naturally; Claude Code
auto-invokes the matching RuFlo capability. NEVER require the user to type
exact commands — infer intent and invoke automatically.

### Intent → Action Mapping
| User Intent | RuFlo Action |
|---|---|
| build/create/implement | `hooks route` → spawn coder agents |
| review/check/audit | dispatch reviewer/security-architect |
| test/verify | tester agent + pytest |
| fix/debug | systematic-debugging skill |
| design/plan/architect | brainstorming → writing-plans skills |
| learn/remember | `memory store` + `intelligence pattern-store` |
| search/find | `memory search` (HNSW semantic) |
| optimize | perf-analyzer agent |
| secure/protect | security-architect + AIDefence |
| deploy/release | release-manager agent |
| coordinate/parallel | swarm init → spawn agents |
| check status/health/running | `/monitoring:status` + `/monitoring:agents` |
| analyze efficiency/tokens | `/analysis:token-efficiency` |
| simplify/clean up code | `/simplify` skill |

---

## Claude Code Permissions (VS Code)

### Sandbox
Claude Code runs as user `lch` inside bubblewrap sandbox. No root access.
Settings at `~/.claude/settings.json`. Sandbox is ALWAYS enabled.
Launch from `~/projects/bazzite-laptop/` — NEVER from $HOME.

### What Claude Code CAN Do
- Create/edit files in `~/projects/bazzite-laptop/`
- Run `git add`, `git commit`, `git push`
- Run Python scripts and `pytest` in the .venv
- Run Ruff, Bandit, ShellCheck on project files
- Create directories under the project root
- Read files anywhere (read-only access outside project)
- **Install tools via `curl`, `wget`, `brew`** (user-space only)
- **Manage Python env via `uv`** (venv, pip install)
- **Run `gpg` and `sops`** for key management
- **Run `ollama`** (pull models, generate embeddings)
- **Run AI Python modules** (threat intel, RAG queries, etc.)

### What Claude Code CANNOT Do (requires manual terminal)
- `sudo` anything — no root commands
- `systemctl enable/start/stop` — no service management
- `rpm-ostree` — no system package management
- `rm -rf` — destructive deletion blocked
- Read `*.env`, `*.key`, `*.pem` files — secrets are runtime-only
- Write to `/usr/local/bin/` — no script deployment
- Write to `/etc/` — no system config changes
- Run `deploy.sh` — requires sudo
- Run `integration-test.sh` — requires sudo

### Approved AI Toolchain (Claude Code can run these directly)
| Tool | What It Does | Install Method |
|------|-------------|----------------|
| `uv` | Python venv + package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `sops` | Encrypt/decrypt API keys | `brew install sops` |
| `gpg` | GPG key management for sops | Pre-installed on Bazzite |
| `ollama` | Local embedding model server | Flatpak or curl installer |
| `ruff` | Python linter/formatter | `uv pip install ruff` (in venv) |
| `bandit` | Python security scanner | `uv pip install bandit` (in venv) |
| `shellcheck` | Bash linter | Pre-installed on Bazzite |
| `pytest` | Python test runner | `uv pip install pytest` (in venv) |

### Security Settings
```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  },
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "deny": [
      "Read(**/.env)", "Read(**/.env.*)", "Read(**/secrets/**)",
      "Read(**/*.key)", "Read(**/*.pem)",
      "Bash(sudo:*)", "Bash(rm -rf:*)",
      "Bash(rpm-ostree:*)", "Bash(systemctl:*)"
    ]
  },
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

### Two-Phase Workflow (still applies for system-level changes)
- **Phase A**: Claude Code creates/edits files in the repo + runs approved tools
- **Phase B**: User manually runs sudo commands (deploy.sh, systemctl, integration tests)

Phase B is only needed for deploying to system paths. All development, testing,
venv management, and tool installation is Phase A (Claude Code handles it directly).

---

## RuFlo v3.5 Integration (ALWAYS ACTIVE)

### Mandatory for Every Session
RuFlo (Claude Flow) v3.5.15 is the orchestration backbone. Reference manual at
`docs/RuFlo_v3.5_Reference_Manual.pdf`. ALL operations MUST use RuFlo tools.

### Session Lifecycle (ALWAYS run these)
```bash
# Session start (auto-runs via hooks)
claude-flow daemon start
claude-flow hooks session-start
claude-flow hooks pretrain --depth medium
claude-flow embeddings init  # warm up ONNX embedding provider

# Session end
claude-flow hooks session-end
```

### 3-Tier Model Routing (ALWAYS apply)
| Tier | When | Model | Cost |
|------|------|-------|------|
| 1 | Simple transforms, edits | Agent Booster / Haiku | <1ms / $0 |
| 2 | Bug fixes, routine code | Sonnet | ~500ms / $0.0002 |
| 3 | Architecture, security, complex | Opus | 2-5s / $0.015 |

### Agent Training (ALWAYS do)
- `hooks intelligence trajectory-start` before multi-step work
- `hooks intelligence trajectory-step` after each significant action
- `hooks intelligence trajectory-end` when task completes
- `hooks intelligence pattern-store` for reusable learnings
- `hooks pretrain` at session start for codebase analysis

### Memory System (ALWAYS use)
- `memory store` — save patterns, decisions, constraints with HNSW embeddings
- `memory search` — semantic search before re-reading docs (saves tokens)
- Store patterns after successful completions for future agent reuse
- Namespaces: `patterns` (reusable solutions), `project` (decisions/constraints), `reference` (doc pointers), `default` (general)

### Swarm Orchestration (for multi-file/multi-step work)
- `swarm init --topology hierarchical --max-agents 6-8`
- Spawn agents via Claude Code Task tool (not CLI alone)
- ALL agents in ONE message for parallel execution
- Use `raft` consensus, `specialized` strategy
- Anti-drift: swarm init + agent spawn in SAME message

### Hooks (use for quality gates)
- `hooks route` — route tasks to optimal agent type
- `hooks post-task` — record success/failure for learning
- `hooks metrics` — check performance stats
- `hooks intelligence pattern-search` — find similar past solutions

### Security (run after security-related changes)
```bash
claude-flow security scan --depth full
claude-flow hooks intelligence pattern-search --query "security vulnerability"
```

### Guidance Control Plane
Machine-checkable gates for NEVER-violate rules. Config at `configs/guidance.config.mjs`.
```bash
node scripts/guidance-check.mjs <command>  # validate before destructive operations
```

### Available MCP Tools (213+)
All `mcp__claude-flow__*` tools are available. Key categories:
- `memory_*` — store, search, retrieve, delete, stats
- `hooks_intelligence_*` — trajectory tracking, pattern storage, learning
- `hooks_route` — semantic task routing
- `swarm_*` — init, status, health, shutdown
- `agent_*` — spawn, list, status, health, terminate
- `task_*` — create, assign, complete, cancel
- `session_*` — save, restore, list
- `neural_*` — train, predict, patterns, optimize
- `embeddings_*` — init, generate, compare, search, neural, hyperbolic, status
- `performance_*` — benchmark, bottleneck, metrics

### Token Optimizer (ALWAYS ACTIVE — `@claude-flow/integration`)

The Token Optimizer from `agentic-flow` MUST be used for all operations to reduce
API costs by 30-50%. This is not optional — every session must leverage these savings.

**Savings Stack (multiplicative):**
| Optimization | Token Savings | How It Works |
|-------------|--------------|--------------|
| ReasoningBank retrieval | -32% | Fetch relevant patterns instead of full context |
| Agent Booster edits | -15% | Simple edits skip LLM entirely (352x faster) |
| Cache (95% hit rate) | -10% | Reuse embeddings and patterns across operations |
| Optimal batch size | -20% | Group related operations into single calls |
| **Combined** | **30-50%** | Stacks multiplicatively |

**Mandatory Usage Rules:**
1. ALWAYS use `memory search` before re-reading large docs (32% savings)
2. ALWAYS check for `[AGENT_BOOSTER_AVAILABLE]` before spawning agents for simple edits
3. ALWAYS route simple tasks to Haiku/Tier 1 (skip LLM when possible)
4. ALWAYS batch ALL operations in single messages (20% savings)
5. ALWAYS store successful patterns for agent reuse via `hooks intelligence pattern-store`
6. ALWAYS run background agents for independent work
7. ALWAYS use hierarchical topology to limit drift and reduce redundant context

**Anti-Drift Swarm Configuration:**
- Use `raft` consensus (leader maintains authoritative state)
- Hierarchical topology keeps agents scoped to their domain
- Shared memory namespace prevents duplicate context loading
- Checkpoints via `post-task` hooks catch drift early

### Upgraded Memory & Embeddings (ALWAYS ACTIVE)

HNSW vector memory and embedding features MUST be used for ALL knowledge operations.
Never fall back to flat file reads when semantic search is available.

**Memory Features (use 24/7):**
| Feature | MCP Tool | When to Use |
|---------|----------|-------------|
| HNSW vector search | `memory_search` | Before reading any doc, searching patterns |
| Knowledge graph | `memory_store` with tags | After learning patterns, storing decisions |
| 3-scope memory | project/local/user namespaces | Scoping context to appropriate level |
| Cross-agent transfer | `memory_store` shared namespace | When agents need shared context |
| Sub-ms retrieval | `memory_retrieve` | Quick lookups of known keys |
| LRU cache | automatic | Reuses recent embeddings (95% hit rate) |
| SQLite persistence | automatic | Survives session restarts |

**Embedding Features (use 24/7):**
| Feature | MCP Tool | When to Use |
|---------|----------|-------------|
| Generate embeddings | `embeddings_generate` | Encoding new content for search |
| Semantic comparison | `embeddings_compare` | Comparing code/doc similarity |
| Neural embeddings | `embeddings_neural` | Deep semantic analysis |
| Hyperbolic embeddings | `embeddings_hyperbolic` | Hierarchical/taxonomic relationships |
| Embedding search | `embeddings_search` | Finding semantically similar content |
| Embedding status | `embeddings_status` | Check provider health |

**Mandatory Memory Workflow:**
1. Session start → `embeddings_init` to warm up embedding provider
2. Before reading docs → `memory_search` first (saves tokens)
3. After completing work → `memory_store` patterns + `hooks intelligence pattern-store`
4. Before spawning agents → `memory_search` for relevant prior solutions
5. After swarm completion → store learned patterns in shared namespace

**Two vector stores — do not conflate:**
- **LanceDB** (`~/security/vector-db/`) — used by the AI enhancement layer (`ai/rag/`) for threat intel and security RAG queries. Managed by Python code.
- **HNSW** (claude-flow `memory_search`) — used by RuFlo for orchestration patterns, agent routing, and session memory. Managed by MCP tools.
These are separate systems. Use `ai/rag/` Python modules for security queries, use `memory_search` MCP tool for orchestration queries.

---
