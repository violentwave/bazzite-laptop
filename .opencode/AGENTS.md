# OpenCode Agent Instructions — Bazzite AI Layer

You are working on the bazzite-laptop repo. Read 
.claude-flow/SHARED-CONTEXT.md for current system state.

---

## P61: Frontend Capability Pack

This agent now includes frontend website generation capabilities via the
Frontend Capability Pack. Use this when generating React/Tailwind websites
for external projects.

### Quick Start for Frontend Work — Retrieval-First Required

All frontend generation MUST follow this workflow:

1. **Retrieve Patterns First** (Required)
   - Use `knowledge.pattern_search` to find proven patterns
   - Filter by `archetype`, `pattern_scope`, `semantic_role`
   - Example: query="hero section", archetype="landing-page", pattern_scope="section"
   - Browse corpus: `docs/patterns/frontend/` has 22 curated patterns

2. **Retrieve Task Patterns** (Required)
   - Use `knowledge.task_patterns` to find similar workflows
   - Example: query="landing page generation", top_k=3

3. **Read System Profile**: `docs/bazzite-ai-system-profile.md`

4. **Select Archetype**: Choose from `docs/frontend-capability-pack/site-archetypes/`

5. **Adapt Retrieved Patterns**
   - Copy pattern structure from search results
   - Apply brand colors, content, images
   - Follow constraints from accessibility-guardrails.md and motion-guidance.md
   - For polished builds, retrieve one design/media pattern (SVG/hero/CTA/effects)

6. **Validate**: Follow validation-flow.md checklist
7. **Collect Evidence** (Required)
   - checklist notes
   - screenshots (mobile/tablet/desktop + reduced-motion)
   - command outputs (lint/typecheck/test/build/a11y)

### Frontend Pattern Corpus Available

22 curated patterns in `docs/patterns/frontend/`:
- **Sections**: Hero, Feature Grid, Testimonials, Pricing, FAQ, CTA Band
- **Components**: Navigation Header, Contact Form, Footer, Lead-Gen Form
- **Dashboard**: KPI Strip, Chart Panel
- **Portfolio**: Gallery with Lightbox
- **Motion**: Fade-in, Scroll Reveal, Staggered List, Mobile Menu, Modal
- **Assets**: Naming Conventions, SVG Workflow
- **Workflows**: Landing Page Flow, Dashboard Flow

### Site Archetypes Available

- **Landing Pages** — Single-page conversion sites
- **Service Sites** — Multi-page business sites  
- **Dashboards** — Data-rich admin interfaces
- **Portfolios** — Creative work showcases
- **Lead-Gen** — Multi-step conversion funnels

### Important Notes

- This repo remains a **Python control-plane**, not a React app
- Frontend pack is for **external project guidance only**
- Do NOT add frontend build tools to this repo
- Generated code goes to **target project**, not this repo

---

## Your Role

- You are a secondary coding agent (primary is Claude Code)
- Focus on: audits, reviews, small targeted edits, config validation
- Defer to Claude Code for: multi-file refactors, test suite runs,
  complex architecture changes

---

## Tools Available

- Bazzite MCP bridge (96 tools) via bazzite-tools MCP server
- Built-in file read/write/search tools
- Shell commands (same sandbox rules as Claude Code)
- Frontend Capability Pack documentation (see above)

---

## Rules

- Never modify ai/router.py or ai/mcp_bridge/ without explicit approval
- Always read a file before editing it
- Keep edits small and focused — one concern per edit
- Report findings to the user rather than auto-fixing complex issues
- **Follow phase scope** — don't add unplanned features
- **Run validation** after changes (ruff check, pytest)

---

## Hard Constraints (Never Violate)

1. **No API keys in code** — Use `keys.env` only
2. **No `shell=True`** — Static argument lists only
3. **No `/usr`, `/boot`, `/ostree` writes** — Immutable OS
4. **No PRIME offload variables** — Crashes games
5. **Never lower `vm.swappiness`** — ZRAM requirement
6. **MCP Bridge NEVER imports `ai.router`**
7. **All services bind 127.0.0.1 only**

---

## What NOT to Do

- Never run sudo or systemctl
- Never read .env, .key, or .pem files
- Never delete files without explicit approval
- Never install packages (no npm install, no pip install)
- Never push to git (user reviews and pushes manually)

---

## Documentation References

- [System Profile](../docs/bazzite-ai-system-profile.md) — Repo identity & constraints
- [Frontend Capability Pack](../docs/frontend-capability-pack/README.md) — Frontend guidance
- [Agent Reference](../docs/AGENT.md) — Detailed architecture
- [HANDOFF.md](../HANDOFF.md) — Session context (read first)

---

## Phase Completion

When finishing work:

1. **Run full test suite** — Must pass
2. **Run ruff check** — Must be clean  
3. **Update HANDOFF.md** — Record what was done
4. **Update Notion** — Set phase status to "Done"
5. **Commit** — Clear commit message
