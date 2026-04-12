---
language: typescript
domain: frontend
type: recipe
title: SVG Background Treatment
archetype: landing-page
pattern_scope: effect
semantic_role: background
generation_priority: 5
tags: svg, background, decorative, hero, performance
---

# SVG Background Treatment

Use SVG as subtle background structure for hero and CTA regions.

## Recommended Usage

- Keep SVG decorative and non-essential to comprehension.
- Position backgrounds with low visual dominance (`opacity-10` to `opacity-30`).
- Prefer static or very subtle motion.

## Example Pattern

```tsx
<section className="relative overflow-hidden">
  <svg
    aria-hidden="true"
    className="absolute inset-0 h-full w-full opacity-20"
    viewBox="0 0 1200 600"
    preserveAspectRatio="xMidYMid slice"
  >
    {/* decorative paths */}
  </svg>
  <div className="relative z-10">
    {/* hero or CTA content */}
  </div>
</section>
```

## Guardrails

- Do not reduce text contrast with bright/complex backgrounds.
- Avoid heavy blur/filter stacks on every section.
- Keep backgrounds optional in reduced-motion contexts.
