---
language: typescript
domain: frontend
type: pattern
title: Browser Evidence Loop
archetype: landing-page
pattern_scope: workflow
semantic_role: workflow
generation_priority: 1
tags: browser, screenshots, breakpoints, reduced-motion, qa, evidence
---

# Browser Evidence Loop

Use this loop after code generation and before closeout.

## Step Order

1. Start the local preview server
2. Open the primary route
3. Confirm the page renders without obvious runtime failures
4. Capture screenshots at required breakpoints
5. Capture one reduced-motion state
6. Record lint, typecheck, test, build, and accessibility outputs
7. Save findings in a stable evidence bundle

## Screenshot Set

Minimum required files:

```text
screenshots/
  mobile-home.png
  tablet-home.png
  desktop-home.png
  reduced-motion-home.png
```

Add route-specific files for:

- forms with validation states
- pricing or comparison tables
- dashboards with real data or representative fixtures
- navigation overlays or mobile menus

## Breakpoint Review Questions

- Does navigation remain usable at 375px?
- Does the layout avoid horizontal overflow at 768px?
- Does the primary content hierarchy still hold at 1280px?
- Do motion-enhanced elements still communicate clearly with reduced motion enabled?

## Output Notes

Keep `checklist.md` and `manifest.json` next to the screenshots so the evidence bundle can be reviewed quickly by operators or future agents.

## Related Patterns

- Frontend Runtime Harness
- Frontend QA Evidence Workflow
- Motion Sanity Review
