---
language: typescript
domain: frontend
type: pattern
title: SVG Illustration System
archetype: service-site
pattern_scope: media
semantic_role: illustration
generation_priority: 2
tags: svg, illustration, svgo, accessibility, theming
---

# SVG Illustration System

A reusable workflow for using SVG illustrations across sections without creating one-off assets.

## Principles

- Keep source SVG files optimized (viewBox preserved, dimensions removable).
- Use `currentColor` where practical so theme tokens can drive color.
- Export as typed React components for consistency.
- Avoid decorative complexity that hurts readability or performance.

## File Conventions

```text
src/assets/illustrations/
  hero-workflow.svg
  feature-automation.svg
  cta-trust.svg
src/components/illustrations/
  IllustrationHeroWorkflow.tsx
  IllustrationFeatureAutomation.tsx
  IllustrationCtaTrust.tsx
```

## Component Contract

```tsx
interface IllustrationProps {
  className?: string;
  title?: string;
}
```

- `title` present: set `role="img"` and `aria-label`
- `title` absent: mark decorative (`aria-hidden="true"`)

## QA Notes

- Verify SVGs scale cleanly at mobile and desktop breakpoints.
- Confirm contrast remains acceptable over hero/CTA backgrounds.
- Keep illustration bundle size lean by avoiding unnecessary path complexity.
