---
language: typescript
domain: frontend
type: pattern
title: Frontend QA Evidence Workflow
archetype: landing-page
pattern_scope: workflow
semantic_role: workflow
generation_priority: 1
tags: qa, workflow, evidence, screenshots, accessibility, responsive, tailwind
---

# Frontend QA Evidence Workflow

Use this workflow before marking generated frontend work as complete.

## Required Evidence

1. Checklist evidence (pass/fail notes)
2. Screenshot evidence (mobile, tablet, desktop, reduced-motion)
3. Command output evidence (lint, typecheck, test, build, a11y)

## Recommended Output Structure

```text
qa-evidence/
  checklist.md
  screenshots/
    mobile-home.png
    tablet-home.png
    desktop-home.png
    reduced-motion-home.png
  commands/
    lint.txt
    typecheck.txt
    test.txt
    build.txt
    a11y.txt
```

## Checklist Template

```markdown
# QA Checklist

- [ ] Responsive checks passed (375, 768, 1024+)
- [ ] Accessibility checks passed (automated + manual keyboard pass)
- [ ] Motion checks passed (prefers-reduced-motion respected)
- [ ] Visual consistency checks passed
- [ ] Tailwind quality checks passed
```

## Related Patterns

- Responsive QA Checklist
- Accessibility QA Checklist
- Motion Sanity Review
- Visual Consistency Review
- Tailwind Quality Review
