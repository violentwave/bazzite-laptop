---
language: typescript
domain: frontend
type: pattern
title: CTA Inline Form
archetype: lead-gen
pattern_scope: component
semantic_role: form
generation_priority: 5
tags: cta, inline-form, conversion, validation, accessibility
---

# CTA Inline Form

Inline email/request form embedded in hero or CTA band.

## Requirements

- Label every input visibly or with an accessible equivalent.
- Validate before submit and present clear error messaging.
- Preserve keyboard flow and focus visibility.

## Example Fields

- Email
- Team size (optional)
- CTA submit button

## QA Notes

- Verify mobile layout stays usable and does not overflow.
- Confirm error states are announced/accessibly discoverable.
