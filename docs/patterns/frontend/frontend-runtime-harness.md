---
language: typescript
domain: frontend
type: pattern
title: Frontend Runtime Harness
archetype: landing-page
pattern_scope: workflow
semantic_role: workflow
generation_priority: 1
tags: runtime, preview, browser, workflow, evidence, vite, nextjs
---

# Frontend Runtime Harness

Use this pattern to define how an external frontend project is previewed and verified before signoff.

## Required Inputs

1. Framework or runtime target (`vite`, `nextjs`, static site, other)
2. Preview command
3. Local preview URL
4. Breakpoint matrix
5. Evidence output directory

## Harness Contract

```text
Preview host: 127.0.0.1
Preview port: project-defined but stable
Main route: /
Breakpoint captures: 375, 768, 1280
Reduced-motion capture: required
```

## Preferred Preview Commands

```bash
# Vite
npm run dev -- --host 127.0.0.1 --port 4173

# Next.js dev
npm run dev -- --hostname 127.0.0.1 --port 3000

# Next.js production preview
npm run build && npm run start -- --hostname 127.0.0.1 --port 3000
```

## Required Outputs

- Preview command transcript
- Browser screenshots for mobile, tablet, desktop
- One reduced-motion screenshot
- QA checklist references
- Machine-readable evidence manifest

## Evidence Directory

```text
qa/browser-evidence/<date>-<phase-or-ticket>/
  checklist.md
  manifest.json
  commands/
  screenshots/
```

## Related Patterns

- Browser Evidence Loop
- Frontend QA Evidence Workflow
- Responsive QA Checklist
