# Prompt Pack — Reusable Templates

Structured prompts for React/Tailwind website generation.

---

## Prompt Structure

All prompts follow this framework:

```
TASK: [High-level goal]
CONTEXT: [Stack, tokens, brand]
FORMAT: [Output structure]
STYLE: [Conventions, linting]
CONSTRAINTS: [Accessibility, performance, motion]
```

---

## Landing Page Hero

```markdown
TASK: Generate a responsive React TSX hero component for a SaaS landing page.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4 with design tokens
- Brand colors: primary, secondary, neutral scale
- Target: desktop-first, mobile-optimized
- Content: headline, subheadline, primary CTA, social proof

FORMAT:
- Single file: Hero.tsx
- Export default component
- Props interface for customization
- Optional: companion CSS module for complex animations

STYLE:
- Airbnb ESLint config compatibility
- clsx for conditional classes
- Semantic HTML5 elements

CONSTRAINTS:
- WCAG AA compliance (contrast, focus states)
- Include role="banner" on container
- focus-visible:ring-2 for interactive elements
- Animation duration ≤ 300ms
- No external images > 200KB
- Export typed props interface
```

---

## Service/Business Feature Section

```markdown
TASK: Build a feature section with alternating layout cards for a service business site.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4, shadcn/ui Card component
- 3-4 feature blocks with icon, title, description
- Alternating left/right image placement

FORMAT:
- FeatureSection.tsx with FeatureCard subcomponent
- JSON data file for content (features.json)
- Props interface for feature array

STYLE:
- TypeScript strict mode
- React.memo for FeatureCard
- Semantic list structure (ul/li with role="list")

CONSTRAINTS:
- Keyboard-navigable if interactive
- ARIA labels on icons
- Alt text required for all images
- motion-safe wrapper for entrance animations
- Staggered reveal ≤ 150ms between items
```

---

## Dashboard KPI Widget

```markdown
TASK: Create a KPI widget that animates numbers on scroll into view.

CONTEXT:
- React 19+, TypeScript
- Tailwind v4 design tokens
- Framer Motion for orchestration
- Dashboard context: needs to work in grid layout

FORMAT:
- KpiWidget.tsx with subcomponents
- Props: title, value, change, format function
- Support for currency, percentage, raw number

STYLE:
- Design token --duration-fast for micro-interactions
- Memoized calculations
- Error boundary wrapper pattern

CONSTRAINTS:
- useReducedMotion hook integration
- Skip animation when reduced motion preferred
- will-change hints for GPU layers
- Avoid layout thrashing (no width/height animations)
- jest-axe testable structure
```

---

## Portfolio Gallery

```markdown
TASK: Scaffold a responsive gallery with modal lightbox for creative portfolio.

CONTEXT:
- React 18+, TypeScript
- Tailwind grid utilities
- Framer Motion for modal transitions
- Image-heavy: optimization required

FORMAT:
- Gallery.tsx (grid container)
- Lightbox.tsx (modal component)
- GalleryItem.tsx (individual item)
- Lazy loading for images below fold

STYLE:
- GalleryItemProps interface exported
- React.lazy for Lightbox code-splitting
- Semantic figure/figcaption structure

CONSTRAINTS:
- Alt text required for every image
- Focus trap inside modal
- ESC key closes modal
- Animation duration ≤ 400ms
- motion-safe for entrance animations
- Loading states for large images
```

---

## Lead-Gen Multi-Step Form

```markdown
TASK: Generate a multi-step signup form with inline validation for lead generation.

CONTEXT:
- React 18+, TypeScript
- React Hook Form + Zod for validation
- Tailwind form plugin utilities
- 2-3 steps: contact → preferences → confirmation

FORMAT:
- SignupForm.tsx (main container)
- StepIndicator.tsx (progress UI)
- validationSchema.ts (Zod schemas)
- types.ts (form data interfaces)

STYLE:
- Type-safe props throughout
- React.memo for step components
- ARIA live region for error announcements

CONSTRAINTS:
- WCAG AA: error messages announced to screen readers
- Focus management between steps
- Reduced motion on step transitions
- No more than 2KB JS per step
- Client-side validation before submit
- Server error handling with retry UI
```

---

## Navigation Header

```markdown
TASK: Create a responsive navigation header with mobile hamburger menu.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4
- 4-6 nav items, optional CTA button
- Logo left, nav center/desktop, CTA right

FORMAT:
- Header.tsx
- MobileMenu.tsx (slide-out drawer)
- NavItem.tsx (individual link)

STYLE:
- Semantic nav element with role="navigation"
- aria-current for active page
- clsx for conditional active states

CONSTRAINTS:
- Keyboard accessible (Tab, Enter, Escape)
- Focus trap in mobile menu
- No layout shift on mobile open
- motion-safe for menu animations
- Logo linked to home with aria-label
```

---

## Footer Component

```markdown
TASK: Generate a comprehensive footer with links, social, and newsletter signup.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4
- Multi-column layout (3-4 columns)
- Optional newsletter form

FORMAT:
- Footer.tsx
- FooterColumn.tsx (reusable column)
- SocialLinks.tsx (icon links)
- NewsletterForm.tsx (optional)

STYLE:
- Semantic footer element
- Heading hierarchy (h2 for footer sections)
- Visually hidden labels for icon-only links

CONSTRAINTS:
- All links keyboard accessible
- External links have external indicator
- Social links have aria-labels
- Newsletter form has associated label
- motion-safe for subtle hover effects
```

---

## CTA Section

```markdown
TASK: Build a conversion-focused CTA section for bottom of page.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4
- High contrast background option
- Primary action + secondary link

FORMAT:
- CTASection.tsx
- Props for headline, description, primary CTA, secondary CTA

STYLE:
- High color contrast (WCAG AA minimum)
- Large touch targets (min 44x44px)
- Semantic section with aria-labelledby

CONSTRAINTS:
- Focus visible on both CTAs
- Clear visual hierarchy
- Loading state for async actions
- Error state for failed submissions
- motion-safe for entrance animation
```

---

## Testimonials Section

```markdown
TASK: Create a testimonials carousel or grid section.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4
- 3-6 testimonials with quote, author, role
- Optional: carousel for mobile, grid for desktop

FORMAT:
- TestimonialsSection.tsx
- TestimonialCard.tsx
- Optional: Carousel.tsx with prev/next

STYLE:
- Semantic blockquote for quotes
- cite element for attribution
- Star rating with aria-label

CONSTRAINTS:
- Carousel: pause on hover/focus
- Carousel: manual controls (not auto-play)
- All content visible without JS (progressive enhancement)
- motion-safe for slide transitions
- Testimonial text readable (not too long)
```

---

## Pricing Table

```markdown
TASK: Generate a pricing table with 2-4 tiers and feature comparison.

CONTEXT:
- React 18+, TypeScript
- Tailwind v4
- Recommended tier highlighted
- Monthly/annual toggle (optional)

FORMAT:
- PricingTable.tsx
- PricingTier.tsx (individual card)
- FeatureRow.tsx (for comparison)

STYLE:
- Semantic table or list structure
- Recommended tier marked with aria-label
- Currency formatting helper

CONSTRAINTS:
- Keyboard navigable tier cards
- Focus visible on CTA buttons
- Clear visual distinction for recommended
- motion-safe for hover effects
- Screen reader announces pricing clearly
```

---

## Using These Prompts — Brief-First Workflow

All frontend generation must follow this workflow:

### Step 0: Complete Project Brief (NEW)

**Before retrieving patterns, populate the brief:**

1. **Gather** project requirements via intake form or client interview
2. **Populate** brief using [website-brief-schema.md](website-brief-schema.md):
   ```yaml
   website_brief:
     project_metadata:
       name: "Project Name"
       project_type: landing-page | service-site | dashboard | portfolio | lead-gen
       primary_goal: "Main conversion/business goal"
     target_audience:
       primary_persona: { demographics, goals, pain_points }
     sitemap:
       pages: [ { route, title, page_type, sections } ]
     # ... see full schema
   ```
3. **Complete** SEO intake using [content-seo-intake.md](content-seo-intake.md)
4. **Complete** brand intake using [brand-asset-intake.md](brand-asset-intake.md)
5. **Define** page maps and CTAs using [page-map-cta-requirements.md](page-map-cta-requirements.md)

**Brief completion is required before code generation begins.**

### Step 1: Retrieve Proven Patterns

Before generating any code, search for existing patterns:

```markdown
Search `knowledge.pattern_search` with:
- query: [component description, e.g., "hero section with CTA"]
- archetype: [landing-page|service-site|dashboard|portfolio|lead-gen]
- pattern_scope: [section|component|layout|motion|asset|token|workflow|media|effect]
- semantic_role: [hero|cta|navigation|pricing|testimonial|feature|illustration|background|proof|visual-effect|...]
```

### Step 2: Retrieve Similar Workflows

Find similar past successful tasks:

```markdown
Search `knowledge.task_patterns` with:
- query: [archetype + generation type, e.g., "landing page generation"]
- top_k: 3
```

### Step 3: Adapt Retrieved Patterns

1. **Copy** pattern structure from retrieved results
2. **Customize** CONTEXT with project specifics (colors, content, features)
3. **Apply** CONSTRAINTS based on project requirements
4. **Generate** code following the structured format
5. **Define runtime harness** using [runtime-harness.md](runtime-harness.md)
6. **Validate** against [validation-flow.md](validation-flow.md)
7. **Collect QA evidence package**:
   - checklist notes
   - screenshots (mobile/tablet/desktop + reduced-motion)
   - command outputs (lint/typecheck/test/build/a11y)
   - preview command + local URL + evidence manifest
8. **Apply design/media enhancements intentionally**:
   - retrieve one SVG/media pattern and one hero/CTA enhancement pattern
   - keep effects motion-safe and token-driven

---

## Prompt Metadata

When saving prompts for reuse, include:

```json
{
  "id": "landing_hero_v1",
  "version": "1.0.0",
  "archetype": "landing-page",
  "component": "hero",
  "created": "2026-04-11",
  "tags": ["hero", "landing", "cta", "responsive"],
  "constraints": ["wcag-aa", "motion-safe", "typescript"]
}
```

---

## References

- [Website Brief Schema](website-brief-schema.md) — Canonical project brief
- [Content & SEO Intake](content-seo-intake.md) — SEO metadata templates
- [Brand & Asset Intake](brand-asset-intake.md) — Brand and asset checklist
- [Page Map & CTA/Forms](page-map-cta-requirements.md) — Page structure specifications
- [Site Archetypes](site-archetypes/) — Detailed per-type guidance
- [Accessibility Guardrails](accessibility-guardrails.md) — Constraint details
- [Motion Guidance](motion-guidance.md) — Animation decision framework
- [Runtime Harness](runtime-harness.md) — Preview and browser evidence workflow
- [Validation Flow](validation-flow.md) — Post-generation checklist
