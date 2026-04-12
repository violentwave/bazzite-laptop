---
language: typescript
domain: frontend
type: pattern
title: Landing Page Generation Flow
archetype: landing-page
pattern_scope: workflow
semantic_role: workflow
generation_priority: 1
tags: workflow, landing-page, generation, process
---

# Landing Page Generation Flow

A retrieval-first workflow for generating landing pages using project intelligence.

## Phase 1: Retrieve Patterns

```markdown
1. Search `knowledge.pattern_search` for:
   - archetype: "landing-page"
   - pattern_scope: "section"
   - Query: "hero section with social proof"

2. Search `knowledge.pattern_search` for:
   - archetype: "landing-page"
   - pattern_scope: "component"
   - Query: "navigation header responsive"

3. Retrieve `knowledge.task_patterns` for:
   - Query: "landing page generation"
   - Top 3 similar past tasks

4. Search `knowledge.pattern_search` for:
   - archetype: "landing-page"
   - pattern_scope: "media" or "effect"
   - Query: "svg illustration hero premium visual effect"
```

## Phase 2: Select Sections

Based on project requirements, select from retrieved patterns:

| Priority | Section | Semantic Role |
|----------|---------|---------------|
| 1 | Navigation Header | navigation |
| 2 | Hero Section | hero |
| 3 | Feature Grid | feature |
| 4 | Testimonials | testimonial |
| 5 | CTA Band | cta |
| 6 | FAQ Accordion | list |
| 7 | Footer | footer |

## Phase 3: Adapt Patterns

For each selected pattern:

1. **Copy pattern content** from `code_patterns` table
2. **Apply project specifics**:
   - Brand colors (map to Tailwind classes)
   - Content (headlines, descriptions)
   - Images (reference from assets/)
3. **Validate accessibility**:
   - Heading hierarchy
   - Focus states
   - ARIA attributes
4. **Add motion** (see motion recipes):
   - Fade-in on mount
   - Scroll reveal
   - Reduced motion fallback

## Phase 4: Generate Code

```tsx
// 1. Generate each section component
// 2. Compose in page.tsx
// 3. Add shared layout
// 4. Configure metadata
```

## Phase 5: Validate

Run validation checklist:

- [ ] TypeScript compiles without errors
- [ ] ESLint passes
- [ ] Accessibility audit (axe-core)
- [ ] Responsive breakpoints
- [ ] Motion respects prefers-reduced-motion
- [ ] Performance (Lighthouse)
- [ ] Evidence package collected (checklist + screenshots + command outputs)
- [ ] Design/media enhancement pass completed (SVG + hero/CTA polish)

## Phase 6: Document

Log successful generation to task patterns:

```bash
python scripts/log-task-success.py \
  --description "Landing page generation with QA evidence package" \
  --approach "Retrieval-first patterns + evidence-first validation" \
  --outcome "Responsive, accessible, and reviewed landing page output" \
  --files "docs/patterns/frontend/workflow-landing-page.md,docs/frontend-capability-pack/validation-flow.md" \
  --tools "knowledge.pattern_search,knowledge.task_patterns" \
  --phase "P63"
```

## Related Patterns

- Dashboard Generation Flow (for admin interfaces)
- Validation Flow (for post-generation checks)
- Frontend QA Evidence Workflow
