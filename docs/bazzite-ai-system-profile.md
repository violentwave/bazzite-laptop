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
├── website-brief-schema.md      # P66: Canonical project brief schema
├── content-seo-intake.md        # P66: Content and SEO intake templates
├── brand-asset-intake.md        # P66: Brand and asset intake checklist
├── page-map-cta-requirements.md  # P66: Page map and CTA/form specifications
├── deployment-target-pack.md     # P67: Deployment platform guides
├── environment-config-checklist.md  # P67: Environment variables checklist
├── analytics-forms-integration.md   # P67: Analytics and form integration
├── launch-handoff-checklist.md  # P67: Go-live and client delivery
├── ops-dns-domain-setup.md      # P69: DNS configuration and troubleshooting
├── ops-tls-ssl-provisioning.md  # P69: TLS certificate provisioning
├── ops-reverse-proxy-config.md  # P69: Caddy/nginx reverse proxy
├── ops-launch-procedures.md     # P69: Launch day runbooks
├── ops-troubleshooting-playbook.md  # P69: Troubleshooting decision trees
├── ops-monitoring-alerting.md   # P69: Monitoring and alerting
├── prompt-pack.md               # Reusable prompt templates
├── scaffolds.md                 # Site archetype guidance
├── accessibility-guardrails.md  # Practical a11y rules
├── motion-guidance.md           # Animation best practices
├── runtime-harness.md           # Preview and browser evidence workflow
├── validation-flow.md           # Post-generation checks
└── site-archetypes/             # Specific site type guides
    ├── landing-pages.md
    ├── service-sites.md
    ├── dashboards.md
    ├── portfolios.md
    └── lead-gen.md
```

---

## Code Generation Guidelines

When generating React/Tailwind code using this profile:

1. **Brief-First (Required)** — Complete project brief before code generation
   - Populate `website-brief-schema.md` with all sections
   - Complete content intake via `content-seo-intake.md`
   - Complete brand intake via `brand-asset-intake.md`
   - Define page maps via `page-map-cta-requirements.md`
2. **Use TypeScript** — all components typed
3. **Tailwind v4 patterns** — design tokens in CSS, `@theme` imports
4. **Accessibility first** — semantic HTML, ARIA only when needed, focus visible
5. **Motion-safe by default** — respect `prefers-reduced-motion`
6. **Component-first architecture** — atomic sections, layout wrappers
7. **No arbitrary values** — use design tokens, bracket syntax only when necessary

---

## Validation Checklist for Generated Work

Before marking frontend generation complete:

- [ ] **Brief complete**: Project brief, content intake, brand intake, page maps all filled
- [ ] Code follows project ESLint/Prettier config
- [ ] TypeScript compiles without errors
- [ ] Accessibility: heading hierarchy, landmarks, focus states
- [ ] Motion: `motion-safe` used, reduced-motion respected
- [ ] Responsive: mobile-first, breakpoint strategy clear
- [ ] Runtime: preview command + local URL defined for the target project
- [ ] Performance: bundle size reasonable, no layout thrashing
- [ ] Documentation: README explains component usage
- [ ] Evidence: browser screenshots + command outputs + manifest captured

Before client handoff (deployment):

- [ ] Environment variables documented per `environment-config-checklist.md`
- [ ] Analytics tracking configured per `analytics-forms-integration.md`
- [ ] Forms submitting correctly
- [ ] Launch checklist complete per `launch-handoff-checklist.md`
- [ ] Client deliverables package prepared

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
- [Website Brief Schema](docs/frontend-capability-pack/website-brief-schema.md) — P66: Project brief schema
- [Content & SEO Intake](docs/frontend-capability-pack/content-seo-intake.md) — P66: SEO templates
- [Brand & Asset Intake](docs/frontend-capability-pack/brand-asset-intake.md) — P66: Brand checklist
- [Page Map & CTA/Forms](docs/frontend-capability-pack/page-map-cta-requirements.md) — P66: Page structure
- [Deployment Target Pack](docs/frontend-capability-pack/deployment-target-pack.md) — P67: Platform guides
- [Environment Config Checklist](docs/frontend-capability-pack/environment-config-checklist.md) — P67: Env vars
- [Analytics & Forms Integration](docs/frontend-capability-pack/analytics-forms-integration.md) — P67: Analytics
- [Launch Handoff Checklist](docs/frontend-capability-pack/launch-handoff-checklist.md) — P67: Go-live
- [Ops: DNS & Domain Setup](docs/frontend-capability-pack/ops-dns-domain-setup.md) — P69: DNS config
- [Ops: TLS/SSL Provisioning](docs/frontend-capability-pack/ops-tls-ssl-provisioning.md) — P69: Certificates
- [Ops: Reverse Proxy Config](docs/frontend-capability-pack/ops-reverse-proxy-config.md) — P69: Caddy/nginx
- [Ops: Launch Procedures](docs/frontend-capability-pack/ops-launch-procedures.md) — P69: Runbooks
- [Ops: Troubleshooting Playbook](docs/frontend-capability-pack/ops-troubleshooting-playbook.md) — P69: Diagnosis
- [Ops: Monitoring & Alerting](docs/frontend-capability-pack/ops-monitoring-alerting.md) — P69: Observability
- [HANDOFF.md](HANDOFF.md) — Session context (read first, update last)
