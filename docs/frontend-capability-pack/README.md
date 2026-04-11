# Frontend Capability Pack

A phase-scoped capability pack for generating React/Tailwind websites via OpenCode.

---

## Purpose

This pack provides reusable prompts, scaffolds, and validation workflows for generating high-quality React/Tailwind websites. It stays within the Bazzite/RuFlo control plane and does not create a detached parallel tool stack.

---

## What's Included

| Resource | Location | Purpose |
|----------|----------|---------|
| **Prompt Templates** | [prompt-pack.md](prompt-pack.md) | Reusable prompts for 5 site types |
| **Scaffold Guidance** | [scaffolds.md](scaffolds.md) | File organization patterns |
| **Accessibility Rules** | [accessibility-guardrails.md](accessibility-guardrails.md) | Practical a11y requirements |
| **Motion Guidance** | [motion-guidance.md](motion-guidance.md) | Animation best practices |
| **Validation Flow** | [validation-flow.md](validation-flow.md) | Post-generation checklist |
| **Site Archetypes** | [site-archetypes/](site-archetypes/) | Detailed guides per site type |

---

## Quick Start

### For OpenCode Agents — Retrieval-First Workflow

All frontend generation follows this retrieval-first workflow:

1. **Retrieve Patterns** — Search the curated pattern corpus
   - Use `knowledge.pattern_search` to find proven patterns
   - Filter by `archetype`, `pattern_scope`, `semantic_role`
   - Query: "hero section with social proof", "pricing table", etc.

2. **Retrieve Task Patterns** — Find similar past work
   - Use `knowledge.task_patterns` to retrieve successful workflows
   - Query: "landing page generation", "dashboard creation", etc.

3. **Read** `docs/bazzite-ai-system-profile.md` for repo context

4. **Use Retrieved Patterns** — Adapt retrieved patterns to project needs
   - Copy pattern structure from `docs/patterns/frontend/`
   - Apply brand colors, content, images
   - Follow accessibility and motion guidelines

5. **Generate** — Create code based on retrieved patterns

6. **Validate** — Run through [validation-flow.md](validation-flow.md)

### Direct Pattern Access

Browse the curated pattern corpus at `docs/patterns/frontend/`:

| Category | Patterns Available |
|----------|-------------------|
| Sections | Hero, Feature Grid, Testimonials, Pricing Table, FAQ, CTA Band |
| Components | Navigation Header, Contact Form, Footer |
| Dashboard | KPI Strip, Chart Panel |
| Portfolio | Gallery with Lightbox |
| Lead-Gen | Multi-Step Form |
| Motion | Fade-in, Scroll Reveal, Staggered List, Mobile Menu, Modal |
| Assets | Naming Conventions, SVG Workflow |
| Workflows | Landing Page Flow, Dashboard Flow |

### Site Archetypes

Choose your target:

- [Landing Pages](site-archetypes/landing-pages.md) — Single-page conversion sites
- [Service Sites](site-archetypes/service-sites.md) — Business/service offerings
- [Dashboards](site-archetypes/dashboards.md) — Data-rich admin interfaces
- [Portfolios](site-archetypes/portfolios.md) — Creative work showcases
- [Lead-Gen Sites](site-archetypes/lead-gen.md) — Multi-step conversion funnels

---

## Code Generation Standards

All generated code must follow:

1. **TypeScript** — fully typed components
2. **Tailwind v4** — design tokens via `@theme`, no arbitrary values
3. **Accessibility-first** — semantic HTML, proper focus states
4. **Motion-safe** — respect `prefers-reduced-motion`
5. **Component-first** — atomic sections, reusable layouts

---

## Integration with Bazzite Systems

This pack uses existing infrastructure:

- **Notion** — Track frontend work as phases
- **Knowledge Base** — Store successful patterns in RAG
- **Task Patterns** — Log reusable frontend workflows
- **Phase Control** — Execute via OpenCode backend

**Do NOT create:**
- New build tools (use Vite/Next.js from target project)
- New component libraries (use Tailwind + shadcn/ui)
- New deployment pipelines (use target project's CI/CD)

---

## File Map

```
docs/frontend-capability-pack/
├── README.md                           # This file — entry point
├── prompt-pack.md                      # Reusable prompt templates
├── scaffolds.md                        # File organization patterns
├── accessibility-guardrails.md         # WCAG-aligned practical rules
├── motion-guidance.md                  # Animation decision framework
├── validation-flow.md                  # Post-generation checklist
└── site-archetypes/
    ├── landing-pages.md               # Landing page specifics
    ├── service-sites.md               # Business site specifics
    ├── dashboards.md                  # Dashboard specifics
    ├── portfolios.md                  # Portfolio specifics
    └── lead-gen.md                    # Lead-gen funnel specifics
```

---

## Phase-Scoped Workflow

When using this pack for phase work:

1. **Pre-flight**: Read HANDOFF.md, verify repo state
2. **Planning**: Select archetype, review prompt template
3. **Generation**: Use prompt template with project specifics
4. **Validation**: Run through [validation-flow.md](validation-flow.md)
5. **Documentation**: Update HANDOFF.md with what was created
6. **Completion**: Update Notion phase status

---

## Validation Requirements

Before marking any frontend generation complete:

- [ ] Code passes lint/typecheck in target project
- [ ] Accessibility checks pass (headings, focus, contrast)
- [ ] Motion respects `prefers-reduced-motion`
- [ ] Responsive breakpoints verified
- [ ] Documentation written for generated components

---

## References

- [System Profile](../bazzite-ai-system-profile.md) — Repo identity and constraints
- [Agent Reference](../AGENT.md) — Detailed architecture
- [Handoff Process](../../HANDOFF.md) — Session context
