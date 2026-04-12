# Bazzite AI System Profile

**Repository:** bazzite-laptop  
**Purpose:** AI enhancement layer for Bazzite gaming laptops  
**Backend:** opencode  
**Last Updated:** 2026-04-11

---

## Repository Identity

This is a **Python-based AI control plane**, not a React application. The core deliverables are:

- MCP Bridge (96 tools) for AI assistant integration
- LLM Proxy with 6 cloud providers
- Agent orchestration bus (5 agents)
- Workflow engine with Notion/Slack phase control
- RAG knowledge base (LanceDB)
- Security intel and system monitoring
- PySide6 system tray dashboard

**Frontend work in this repo is documentation and capability-pack only** — we generate guidance and prompts for React/Tailwind sites, not the sites themselves.

---

## Hard Constraints (Never Violate)

1. **No API keys in code** — runtime only via `keys.env`
2. **No `shell=True` in subprocess** — static argument lists only
3. **No writes to `/usr`, `/boot`, `/ostree`** — immutable OS
4. **No PRIME offload variables** — crashes Proton games
5. **Never lower `vm.swappiness` below 180** — ZRAM requirement
6. **MCP Bridge NEVER imports `ai.router`** — scoped key loading
7. **All services bind 127.0.0.1 only** — never 0.0.0.0

---

## When to Use the Frontend Capability Pack

The frontend capability pack (P61) exists to help OpenCode agents generate high-quality React/Tailwind websites for **external projects**. Use it when:

- Creating landing pages, service sites, dashboards, portfolios, or lead-gen sites
- Working with a team member who needs frontend scaffolding guidance
- Generating prompts for a client deliverable
- Building reference implementations for common site patterns

**Do NOT use the capability pack for:**
- Modifying this repo's Python backend
- Creating frontend tooling that duplicates existing MCP tools
- Building a detached parallel stack outside Bazzite/RuFlo control plane

---

## Phase-Scoped Work Requirements

All OpenCode work must remain phase-scoped:

1. **Read HANDOFF.md first** — check current phase context
2. **Follow the phase prompt** — do not skip ahead or improvise
3. **Run pre-flight** — verify git clean, tests pass, ruff clean
4. **Execute sequentially** — complete each deliverable in order
5. **Validate after each file** — ruff check immediately
6. **Update docs/handoff** — record what was done
7. **Close Notion phase** — update status to Done

---

## Control Plane Integration

This profile integrates with:

- **Notion** — phase database for project tracking
- **Slack** — notifications and threaded discussions
- **RuFlo** — manual orchestration (on-demand only, never auto-start)
- **Bazzite MCP Bridge** — 96 tools for system intelligence
- **Phase Control** — automated runner with lease management

When generating frontend work, ensure outputs can reference these existing systems rather than creating new coordination layers.

---

## File Organization for Frontend Capability Work

Frontend prompts and scaffolds live in:

```
docs/frontend-capability-pack/
├── README.md                    # Entry point
├── prompt-pack.md              # Reusable prompt templates
├── scaffolds.md                # Site archetype guidance
├── accessibility-guardrails.md # Practical a11y rules
├── motion-guidance.md          # Animation best practices
├── validation-flow.md          # Post-generation checks
└── site-archetypes/            # Specific site type guides
    ├── landing-pages.md
    ├── service-sites.md
    ├── dashboards.md
    ├── portfolios.md
    └── lead-gen.md
```

---

## Code Generation Guidelines

When generating React/Tailwind code using this profile:

1. **Use TypeScript** — all components typed
2. **Tailwind v4 patterns** — design tokens in CSS, `@theme` imports
3. **Accessibility first** — semantic HTML, ARIA only when needed, focus visible
4. **Motion-safe by default** — respect `prefers-reduced-motion`
5. **Component-first architecture** — atomic sections, layout wrappers
6. **No arbitrary values** — use design tokens, bracket syntax only when necessary

---

## Validation Checklist for Generated Work

Before marking frontend generation complete:

- [ ] Code follows project ESLint/Prettier config
- [ ] TypeScript compiles without errors
- [ ] Accessibility: heading hierarchy, landmarks, focus states
- [ ] Motion: `motion-safe` used, reduced-motion respected
- [ ] Responsive: mobile-first, breakpoint strategy clear
- [ ] Performance: bundle size reasonable, no layout thrashing
- [ ] Documentation: README explains component usage

---

## Phase Completion Requirements

When finishing a phase with frontend deliverables:

1. All code passes lint and typecheck
2. Documentation updated in `docs/frontend-capability-pack/`
3. HANDOFF.md records what was created
4. Notion phase status updated to "Done"
5. Knowledge base refreshed if new patterns learned
6. Task patterns logged for similar future work

---

## References

- [Agent Reference](docs/AGENT.md) — Detailed architecture
- [User Guide](docs/USER-GUIDE.md) — End-user instructions
- [Frontend Capability Pack](docs/frontend-capability-pack/README.md) — P61 deliverables
- [HANDOFF.md](HANDOFF.md) — Session context (read first, update last)
