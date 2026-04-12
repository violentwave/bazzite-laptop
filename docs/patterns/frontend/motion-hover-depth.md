---
language: typescript
domain: frontend
type: recipe
title: Motion Hover Depth
archetype: portfolio
pattern_scope: motion
semantic_role: visual-effect
generation_priority: 6
tags: motion, hover, depth, transform, reduced-motion
---

# Motion Hover Depth

Subtle hover depth effect for cards and CTA elements.

## Pattern

- Use `transform` and `shadow` only.
- Keep duration short (150-250ms).
- Wrap all motion in `motion-safe:` utilities.

## Example Utility Strategy

```text
motion-safe:transition-transform motion-safe:duration-200
motion-safe:hover:-translate-y-0.5 motion-safe:hover:shadow-lg
motion-reduce:transition-none
```

## Guardrails

- No continuous hover oscillation.
- Do not stack multiple heavy effects (blur + scale + glow) on the same element.
