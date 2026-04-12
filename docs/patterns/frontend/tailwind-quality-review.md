---
language: typescript
domain: frontend
type: recipe
title: Tailwind Quality Review
archetype: dashboard
pattern_scope: workflow
semantic_role: token
generation_priority: 6
tags: tailwind, utilities, tokens, class-quality, qa
---

# Tailwind Quality Review

Apply this review to keep Tailwind usage intentional and maintainable.

## Required Checks

- Prefer token-based utilities over arbitrary values when tokens exist
- Avoid contradictory utility combinations on the same element
- Keep responsive variants explicit and readable
- Keep class sets grouped by layout, spacing, typography, and states
- Remove dead or duplicated utility classes during cleanup

## Command Evidence

Store output from lint/typecheck/build checks in `commands/`.

```text
commands/lint.txt
commands/typecheck.txt
commands/build.txt
```
