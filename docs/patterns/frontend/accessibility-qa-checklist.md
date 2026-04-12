---
language: typescript
domain: frontend
type: recipe
title: Accessibility QA Checklist
archetype: lead-gen
pattern_scope: workflow
semantic_role: workflow
generation_priority: 3
tags: accessibility, wcag, keyboard, aria, forms, qa
---

# Accessibility QA Checklist

Use automated and manual checks together.

## Automated Checks

- Run `axe` (or equivalent) against key pages
- Ensure no critical violations
- Keep command output in `commands/a11y.txt`

## Manual Checks

- Keyboard-only navigation reaches all interactive elements
- Visible focus styles on links, controls, menus, dialogs
- Form fields have labels and clear validation messages
- Heading hierarchy is logical
- Landmark regions are present where expected

## Evidence

- Include one screenshot showing visible focus state
- Include one screenshot for form error messaging
- Include `a11y.txt` in the command evidence bundle
