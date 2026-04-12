---
language: typescript
domain: frontend
type: recipe
title: Responsive QA Checklist
archetype: service-site
pattern_scope: workflow
semantic_role: workflow
generation_priority: 2
tags: responsive, breakpoints, mobile, tablet, desktop, qa
---

# Responsive QA Checklist

Validate layout behavior at the minimum breakpoints:

- Mobile: 375px
- Tablet: 768px
- Desktop: 1024px+

## Required Checks

- No horizontal overflow
- Navigation is usable on touch devices
- Tap targets are at least 44x44
- Typography remains readable without zoom
- Media blocks scale correctly
- Tables/charts either adapt or scroll intentionally

## Screenshot Set

Capture at least one primary page at each breakpoint and keep filenames stable:

```text
screenshots/mobile-home.png
screenshots/tablet-home.png
screenshots/desktop-home.png
```

## Failure Notes

Document fixes directly in `checklist.md` with before/after screenshot references.
