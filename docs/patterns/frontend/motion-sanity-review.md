---
language: typescript
domain: frontend
type: recipe
title: Motion Sanity Review
archetype: portfolio
pattern_scope: workflow
semantic_role: animation
generation_priority: 4
tags: motion, animation, reduced-motion, performance, qa
---

# Motion Sanity Review

Validate motion quality without over-animating.

## Required Checks

- `prefers-reduced-motion` is respected
- Motion is purposeful, not decorative noise
- Animation duration remains controlled (generally <= 500ms)
- Animations use `transform`/`opacity` where possible
- No stutter during open/close interactions

## Reduced-Motion Evidence

Capture one screenshot (or short recording) showing reduced-motion mode for a key interactive element.

```text
screenshots/reduced-motion-home.png
```

## Command Evidence

If using automated checks, include their output in `commands/`.
