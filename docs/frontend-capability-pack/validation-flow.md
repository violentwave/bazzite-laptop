# Validation Flow

Post-generation checklist for React/Tailwind frontend work.

---

## Overview

Every generated frontend codebase must pass these validation levels before being marked complete. The flow is designed to be agent-friendly while ensuring production-quality output.

Live preview evidence is required. Static code review alone is not enough for closeout.

---

## Level 0: Runtime Harness

### Preview Definition

Before QA begins, document the target project's preview path:

```bash
# Example Vite
npm run dev -- --host 127.0.0.1 --port 4173

# Example Next.js
npm run dev -- --hostname 127.0.0.1 --port 3000
```

**Checks:**
- [ ] Preview command recorded
- [ ] Local URL recorded
- [ ] Preview bound to `127.0.0.1` unless project requirements say otherwise
- [ ] Evidence output directory defined

### Browser Evidence Bundle

Create a stable bundle in the target project:

```text
qa/browser-evidence/<date>-<phase-or-ticket>/
  checklist.md
  manifest.json
  commands/
  screenshots/
```

**Checks:**
- [ ] `checklist.md` includes pass/fail notes
- [ ] `manifest.json` records preview URL and breakpoints
- [ ] Screenshot filenames are stable
- [ ] Command outputs are saved alongside screenshots

---

## Level 1: Syntax & Static Analysis

### Linting

```bash
# ESLint + Prettier
npm run lint

# Should pass with zero errors
# Warnings acceptable if documented
```

**Checks:**
- No syntax errors
- Consistent code style
- Import organization
- No unused variables

### Type Checking

```bash
# TypeScript
npm run typecheck
# or
npx tsc --noEmit
```

**Checks:**
- All components typed
- Props interfaces defined
- No `any` types without justification
- Generic types properly constrained

### Tailwind Class Validation

```bash
# Ensure all Tailwind classes are valid
npx tailwindcss -i ./src/styles/globals.css -o /dev/null
```

**Checks:**
- No invalid Tailwind classes
- No arbitrary values where tokens exist
- Proper responsive prefixes

---

## Level 2: Accessibility Audit

### Automated Testing

```bash
# jest-axe for component tests
npm run test:axe

# pa11y for full page scan
npx pa11y http://localhost:3000
```

**Checks:**
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Heading hierarchy valid
- [ ] Color contrast meets WCAG AA
- [ ] Focus states visible
- [ ] ARIA used correctly

### Manual Checklist

- [ ] Keyboard navigation works (Tab through all interactive elements)
- [ ] Focus trap works in modals
- [ ] Skip link present and functional
- [ ] Screen reader announces content correctly
- [ ] No keyboard traps

### Tools

```bash
# Browser extension: axe DevTools
# Chrome DevTools: Accessibility panel
# Firefox: Accessibility inspector
```

---

## Level 3: Responsive Design

### Breakpoint Testing

| Breakpoint | Width | Priority |
|------------|-------|----------|
| Mobile | 320px - 375px | Must work |
| Tablet | 768px | Must work |
| Desktop | 1024px+ | Must work |
| Large | 1440px+ | Should work |

### Testing Checklist

- [ ] No horizontal scroll at any breakpoint
- [ ] Touch targets ≥ 44x44px on mobile
- [ ] Text readable without zoom (16px minimum)
- [ ] Navigation usable on mobile (hamburger if needed)
- [ ] Images scale appropriately
- [ ] Tables/data views adapt (stack or scroll)

### Tools

```bash
# Chrome DevTools Device Mode
# Firefox Responsive Design Mode
# Actual device testing (if available)
```

### Required Browser Captures

- [ ] `mobile-home.png` at 375px
- [ ] `tablet-home.png` at 768px
- [ ] `desktop-home.png` at 1280px or project desktop baseline
- [ ] One route-specific capture if the main value is not visible on the home route

---

## Level 4: Performance

### Bundle Analysis

```bash
# Analyze bundle size
npm run analyze

# Check for unused code
npx unimported
```

**Limits:**
- Initial JS bundle < 200KB gzipped
- Total page weight < 1MB
- No unused dependencies

### Lighthouse CI

```bash
# Run Lighthouse audit
npm run lighthouse

# Or use CLI
npx lighthouse http://localhost:3000 --output=json
```

**Targets:**
- Performance score ≥ 90
- Accessibility score ≥ 95
- Best Practices score ≥ 90
- SEO score ≥ 90

### Core Web Vitals

| Metric | Target |
|--------|--------|
| LCP (Largest Contentful Paint) | < 2.5s |
| FID (First Input Delay) | < 100ms |
| CLS (Cumulative Layout Shift) | < 0.1 |

---

## Level 5: Content & UX

### Content Verification

- [ ] No placeholder text (lorem ipsum, "Example", etc.)
- [ ] All CTAs have clear action text
- [ ] Form validation messages helpful
- [ ] Error states designed
- [ ] Loading states considered
- [ ] Empty states handled

### UX Patterns

- [ ] Consistent spacing (follows 8px grid)
- [ ] Consistent typography scale
- [ ] Hover states on all interactive elements
- [ ] Active/pressed states on buttons
- [ ] Loading indicators for async actions
- [ ] Success/error feedback for forms

### Navigation

- [ ] All links functional
- [ ] 404 page exists
- [ ] Breadcrumbs (if applicable)
- [ ] Back button behavior logical

---

## Level 5.5: Design & Media Enhancements

- [ ] SVG assets are optimized and appropriately labeled
- [ ] Hero/CTA enhancements keep conversion hierarchy clear
- [ ] Premium effects do not degrade contrast/readability
- [ ] Media and effects follow tokenized visual language

---

## Level 6: Motion & Animation

### Reduced Motion

- [ ] `motion-safe:` or `useReducedMotion()` used
- [ ] Animations disabled when reduced motion preferred
- [ ] No vestigial motion (animations that don't work)
- [ ] Reduced-motion screenshot captured for a key animated view

### Performance

- [ ] Only `transform` and `opacity` animated
- [ ] No layout-triggering animations
- [ ] Animation durations ≤ 500ms
- [ ] `will-change` used sparingly

### Quality

- [ ] Animations have purpose (not decorative-only)
- [ ] Timing feels natural (not too fast/slow)
- [ ] No jank or frame drops

---

## Level 7: Integration

### Environment

- [ ] Builds successfully in production mode
- [ ] Environment variables handled
- [ ] API endpoints configurable
- [ ] Error boundaries implemented

### Meta & SEO

- [ ] Page titles set
- [ ] Meta descriptions present
- [ ] OG tags for social sharing
- [ ] Favicon present
- [ ] robots.txt configured

### Analytics (if applicable)

- [ ] Tracking script loading
- [ ] Events firing correctly
- [ ] No PII in tracking data

---

## Validation Scripts

### package.json Scripts

```json
{
  "scripts": {
    "validate": "npm run lint && npm run typecheck && npm run test && npm run build",
    "validate:ci": "npm run validate && npm run lighthouse",
    "lint": "eslint src/ --ext .ts,.tsx",
    "typecheck": "tsc --noEmit",
    "test": "jest",
    "test:axe": "jest --testPathPattern=a11y",
    "build": "next build",
    "lighthouse": "lhci autorun",
    "analyze": "ANALYZE=true npm run build"
  }
}
```

### GitHub Actions Workflow

```yaml
name: Validate Frontend
on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Lint
        run: npm run lint
        
      - name: Type check
        run: npm run typecheck
        
      - name: Test
        run: npm run test
        
      - name: Build
        run: npm run build
        
      - name: Lighthouse CI
        run: npm run lighthouse
```

---

## Quick Validation Checklist

For rapid iteration, use this abbreviated list:

- [ ] Preview command and local URL recorded
- [ ] `npm run lint` passes
- [ ] `npm run typecheck` passes
- [ ] Manual keyboard navigation works
- [ ] Responsive at 375px, 768px, 1024px
- [ ] Lighthouse score ≥ 90
- [ ] No placeholder content
- [ ] Reduced motion respected

---

## Required Evidence Package

For phase completion, attach all three evidence types:

- [ ] Checklist evidence: completed validation checklist with pass/fail notes
- [ ] Screenshot evidence: mobile/tablet/desktop captures plus one reduced-motion capture
- [ ] Runtime harness evidence: preview command, local URL, and manifest
- [ ] Command output evidence: lint/typecheck/test/build/a11y command output (or CI link)

Store evidence in a predictable folder for review handoff, for example:

```text
qa-evidence/
  checklist.md
  manifest.json
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

---

## Post-Validation Actions

### Documentation

Update these docs after validation:
- [ ] Component README with usage examples
- [ ] Props documentation
- [ ] Any non-obvious implementation details

### Knowledge Capture

If using Bazzite knowledge systems:
- [ ] Log successful patterns to task_patterns
- [ ] Ingest component docs to RAG
- [ ] Update HANDOFF.md with what was learned

### Phase Closure

- [ ] Notion phase status updated to "Done"
- [ ] HANDOFF.md updated
- [ ] Git commit with validation results

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Layout shift | Images without dimensions | Add `width`/`height` or aspect-ratio |
| Slow LCP | Large hero image | Optimize, use WebP, lazy load below fold |
| A11y warnings | Missing labels | Add `htmlFor` or `aria-label` |
| Type errors | Missing interfaces | Add TypeScript prop types |
| Bundle bloat | Unused imports | Run `unimported`, remove dead code |
| Animation jank | Layout properties | Switch to `transform`/`opacity` |

---

## References

- [Lighthouse Scoring](https://web.dev/performance-scoring/)
- [Web Vitals](https://web.dev/vitals/)
- [axe-core Rules](https://dequeuniversity.com/rules/axe/4.8)
- [WCAG Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
