# Frontend Capability Pack

A phase-scoped capability pack for generating React/Tailwind websites via OpenCode.

---

## Purpose

This pack provides reusable prompts, scaffolds, and validation workflows for generating high-quality React/Tailwind websites. It stays within the Bazzite/RuFlo control plane and does not create a detached parallel tool stack.

---

## What's Included

| Resource | Location | Purpose |
|----------|----------|---------|
| **Website Brief Schema** | [website-brief-schema.md](website-brief-schema.md) | Canonical project brief structure |
| **Content & SEO Intake** | [content-seo-intake.md](content-seo-intake.md) | SEO metadata and structured data templates |
| **Brand & Asset Intake** | [brand-asset-intake.md](brand-asset-intake.md) | Brand identity and asset delivery checklist |
| **Page Map & CTA/Form** | [page-map-cta-requirements.md](page-map-cta-requirements.md) | Page structure and conversion specifications |
| **Deployment Target Pack** | [deployment-target-pack.md](deployment-target-pack.md) | P67: Platform guides (Vercel, Netlify, Cloudflare) |
| **Environment Config** | [environment-config-checklist.md](environment-config-checklist.md) | P67: Environment variables and configuration |
| **Analytics & Forms** | [analytics-forms-integration.md](analytics-forms-integration.md) | P67: Analytics and form integration requirements |
| **Launch Handoff** | [launch-handoff-checklist.md](launch-handoff-checklist.md) | P67: Go-live and client delivery checklist |
| **Ops: DNS & Domain** | [ops-dns-domain-setup.md](ops-dns-domain-setup.md) | P69: DNS configuration and troubleshooting |
| **Ops: TLS/SSL** | [ops-tls-ssl-provisioning.md](ops-tls-ssl-provisioning.md) | P69: Certificate provisioning and management |
| **Ops: Reverse Proxy** | [ops-reverse-proxy-config.md](ops-reverse-proxy-config.md) | P69: Caddy/nginx configuration for self-hosted |
| **Ops: Launch** | [ops-launch-procedures.md](ops-launch-procedures.md) | P69: Launch day runbooks and rollback |
| **Ops: Troubleshooting** | [ops-troubleshooting-playbook.md](ops-troubleshooting-playbook.md) | P69: Symptom-diagnosis-fix decision trees |
| **Ops: Monitoring** | [ops-monitoring-alerting.md](ops-monitoring-alerting.md) | P69: Uptime, error tracking, and alerting |
| **Prompt Templates** | [prompt-pack.md](prompt-pack.md) | Reusable prompts for 5 site types |
| **Scaffold Guidance** | [scaffolds.md](scaffolds.md) | File organization patterns |
| **Accessibility Rules** | [accessibility-guardrails.md](accessibility-guardrails.md) | Practical a11y requirements |
| **Motion Guidance** | [motion-guidance.md](motion-guidance.md) | Animation best practices |
| **Runtime Harness** | [runtime-harness.md](runtime-harness.md) | Preview + browser evidence workflow |
| **Validation Flow** | [validation-flow.md](validation-flow.md) | Post-generation checklist |
| **Site Archetypes** | [site-archetypes/](site-archetypes/) | Detailed guides per site type |

---

## Quick Start

### For OpenCode Agents — Brief-First + Retrieval Workflow

All frontend generation follows this workflow:

**Step 0: Complete Project Brief (NEW)**

Before retrieving patterns or generating code, populate the project brief:

1. **Gather** project requirements via intake form or client interview
2. **Populate** brief using [website-brief-schema.md](website-brief-schema.md):
   - Project metadata (name, type, goals)
   - Target audience and personas
   - Sitemap and page structure
   - CTA specifications and form requirements
   - SEO inputs and structured data
   - Brand rules (colors, typography, voice)
   - Asset expectations (imagery, icons, illustrations)
3. **Complete** content intake using [content-seo-intake.md](content-seo-intake.md)
4. **Complete** brand/asset intake using [brand-asset-intake.md](brand-asset-intake.md)
5. **Define** page maps using [page-map-cta-requirements.md](page-map-cta-requirements.md)
6. **Validate** brief completeness before proceeding

**Step 1: Retrieve Patterns**

Search the curated pattern corpus:
- Use `knowledge.pattern_search` to find proven patterns
- Filter by `archetype`, `pattern_scope`, `semantic_role`
- Query: "hero section with social proof", "pricing table", etc.

**Step 2: Retrieve Task Patterns**

Find similar past work:
- Use `knowledge.task_patterns` to retrieve successful workflows
- Query: "landing page generation", "dashboard creation", etc.

**Step 3: Read Context**

Read `docs/bazzite-ai-system-profile.md` for repo context.

**Step 4: Use Retrieved Patterns**

Adapt retrieved patterns to project needs:
- Copy pattern structure from `docs/patterns/frontend/`
- Apply brand colors, content, images from brief
- Follow accessibility and motion guidelines

**Step 5: Generate**

Create code based on retrieved patterns and brief data.

**Step 6: Define Runtime Harness**

Choose preview command and local URL via [runtime-harness.md](runtime-harness.md).

**Step 7: Validate**

Run through [validation-flow.md](validation-flow.md).

**Step 8: Collect Evidence**

Checklist + screenshots + command outputs from a live preview.

---

### Brief-First Requirement

**Code generation MUST NOT begin until the brief is complete.**

Brief completion means:
- [ ] Project metadata defined (name, type, goals)
- [ ] Target audience documented
- [ ] Sitemap with all routes
- [ ] Page modules mapped to patterns
- [ ] CTAs specified per page
- [ ] Forms specified with fields and validation
- [ ] SEO inputs per page (title, meta, structured data)
- [ ] Brand rules collected (colors, typography, voice)
- [ ] Asset expectations defined

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
| Runtime Workflows | Frontend Runtime Harness, Browser Evidence Loop |
| QA Workflows | QA Evidence, Responsive QA, Accessibility QA, Motion Sanity, Visual Consistency, Tailwind Quality |
| Design/Media | SVG Illustration System, Hero Split Media, Hero Proof-Driven, CTA Proof Stack, Premium Visual Effects |

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
6. **Runtime-evidenced** — signoff requires live preview artifacts, not static review alone

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
├── website-brief-schema.md              # P66: Canonical project brief schema
├── content-seo-intake.md                # P66: Content and SEO intake templates
├── brand-asset-intake.md                # P66: Brand and asset intake checklist
├── page-map-cta-requirements.md         # P66: Page map and CTA/form specifications
├── deployment-target-pack.md            # P67: Deployment platform guides
├── environment-config-checklist.md      # P67: Environment variables checklist
├── analytics-forms-integration.md       # P67: Analytics and form integration
├── launch-handoff-checklist.md          # P67: Go-live and client delivery
├── ops-dns-domain-setup.md              # P69: DNS configuration and troubleshooting
├── ops-tls-ssl-provisioning.md          # P69: TLS certificate provisioning
├── ops-reverse-proxy-config.md          # P69: Caddy/nginx reverse proxy
├── ops-launch-procedures.md             # P69: Launch day runbooks
├── ops-troubleshooting-playbook.md      # P69: Troubleshooting decision trees
├── ops-monitoring-alerting.md           # P69: Monitoring and alerting
├── prompt-pack.md                       # Reusable prompt templates
├── scaffolds.md                         # File organization patterns
├── accessibility-guardrails.md          # WCAG-aligned practical rules
├── motion-guidance.md                   # Animation decision framework
├── runtime-harness.md                   # Preview + browser evidence workflow
├── validation-flow.md                    # Post-generation checklist
└── site-archetypes/
    ├── landing-pages.md                 # Landing page specifics
    ├── service-sites.md                 # Business site specifics
    ├── dashboards.md                     # Dashboard specifics
    ├── portfolios.md                     # Portfolio specifics
    └── lead-gen.md                       # Lead-gen funnel specifics
```

---

## Phase-Scoped Workflow

When using this pack for phase work:

1. **Pre-flight**: Read HANDOFF.md, verify repo state
2. **Brief**: Complete project brief (P66 schema)
3. **Planning**: Select archetype, review prompt template
4. **Generation**: Use prompt template with project specifics
5. **Validation**: Run through [validation-flow.md](validation-flow.md)
6. **Runtime Evidence**: Use [runtime-harness.md](runtime-harness.md) to capture preview artifacts
7. **Deployment Prep**: Configure environment per [environment-config-checklist.md](environment-config-checklist.md)
8. **Launch**: Follow [launch-handoff-checklist.md](launch-handoff-checklist.md) for go-live
9. **Handoff**: Deliver client documentation and access credentials
10. **Documentation**: Update HANDOFF.md with what was created
11. **Completion**: Update Notion phase status to `Done`

---

## Validation Requirements

Before marking any frontend generation complete:

- [ ] **Brief complete**: Project brief, content intake, brand intake, page maps all filled
- [ ] Code passes lint/typecheck in target project
- [ ] Accessibility checks pass (headings, focus, contrast)
- [ ] Motion respects `prefers-reduced-motion`
- [ ] Responsive breakpoints verified
- [ ] Runtime harness documented for the target project
- [ ] Documentation written for generated components
- [ ] QA evidence package captured from a live browser preview

Before launch (deployment handoff):

- [ ] Environment variables documented and configured
- [ ] Analytics tracking verified (GA4, custom events)
- [ ] Forms submitting correctly
- [ ] Security headers configured
- [ ] SSL certificate valid
- [ ] Performance acceptable (Lighthouse ≥90)
- [ ] Cross-browser testing complete
- [ ] Client handoff documentation delivered

---

## References

- [System Profile](../bazzite-ai-system-profile.md) — Repo identity and constraints
- [Agent Reference](../AGENT.md) — Detailed architecture
- [Handoff Process](../../HANDOFF.md) — Session context
- [Deployment Target Pack](deployment-target-pack.md) — P67: Platform guides
- [Launch Handoff Checklist](launch-handoff-checklist.md) — P67: Go-live procedures
