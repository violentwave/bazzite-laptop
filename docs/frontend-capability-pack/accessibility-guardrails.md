# Accessibility Guardrails

Practical accessibility requirements for React/Tailwind projects.

---

## Core Principles

| Pillar | Focus | Implementation |
|--------|-------|----------------|
| **Perceivable** | Content visible/audible | Color contrast, alt text, zoom support |
| **Operable** | Interface works with keyboard | Focus states, logical tab order |
| **Understandable** | Clear navigation/labels | Semantic HTML, error messages |
| **Robust** | Works with assistive tech | ARIA only when needed, valid markup |

---

## Heading Hierarchy

### Rules

1. **One h1 per page** — Page title only
2. **No skipped levels** — h2 → h3, not h2 → h4
3. **Logical nesting** — Headings reflect content structure
4. **Don't style with headings** — Use `className` for visual size

### Example

```tsx
// ❌ Bad: Using heading for styling
<h1 className="text-lg">Small heading</h1>

// ✅ Good: Semantic heading, Tailwind for sizing
<h2 className="text-lg font-semibold">Section title</h2>
```

### Pattern

```tsx
<main>
  <h1>Page Title</h1>
  
  <section aria-labelledby="features-heading">
    <h2 id="features-heading">Features</h2>
    <h3>Feature One</h3>
    <h3>Feature Two</h3>
  </section>
  
  <section aria-labelledby="pricing-heading">
    <h2 id="pricing-heading">Pricing</h2>
    <h3>Basic Plan</h3>
    <h3>Pro Plan</h3>
  </section>
</main>
```

---

## Semantic Landmarks

### Required Elements

```tsx
// Header with navigation
<header>
  <nav aria-label="Main navigation">
    {/* Nav links */}
  </nav>
</header>

// Main content (only one per page)
<main id="main-content">
  {/* Page content */}
</main>

// Footer
<footer>
  {/* Footer content */}
</footer>

// Complementary content (sidebars, asides)
<aside aria-label="Related articles">
  {/* Sidebar content */}
</aside>
```

### Skip Links

```tsx
// First focusable element on page
<a 
  href="#main-content" 
  className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-4"
>
  Skip to main content
</a>
```

---

## Color Contrast

### Minimum Ratios (WCAG AA)

| Use Case | Ratio | Example |
|----------|-------|---------|
| Normal text | 4.5:1 | Body text on background |
| Large text (18px+) | 3:1 | Headings |
| UI components | 3:1 | Buttons, form borders |

### Tailwind Patterns

```tsx
// ✅ Good: Sufficient contrast
<p className="text-gray-900 bg-white">Dark on light</p>
<p className="text-white bg-blue-600">Light on dark</p>

// ❌ Bad: Insufficient contrast
<p className="text-gray-400 bg-white">4.5:1 fail</p>
<p className="text-yellow-300 bg-white">4.5:1 fail</p>
```

### Testing

```bash
# Use browser dev tools accessibility panel
# Or online checker: https://webaim.org/resources/contrastchecker/
```

---

## Focus Visibility

### Requirements

1. **All interactive elements must show focus**
2. **Focus indicator must be visible**
3. **Don't remove focus styles without replacement**

### Tailwind Implementation

```tsx
// ✅ Good: Visible focus ring
<button className="focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2">
  Click me
</button>

// ❌ Bad: No focus indicator
<button className="outline-none">Click me</button>

// ✅ Good: Custom focus style
<button className="outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
  Click me
</button>
```

### Focus Trap Pattern

```tsx
// For modals, drawers
import { useEffect, useRef } from 'react';

function useFocusTrap(isOpen: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!isOpen || !containerRef.current) return;
    
    const container = containerRef.current;
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;
    
    firstElement?.focus();
    
    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };
    
    container.addEventListener('keydown', handleTabKey);
    return () => container.removeEventListener('keydown', handleTabKey);
  }, [isOpen]);
  
  return containerRef;
}
```

---

## Alt Text

### Rules

| Image Type | Alt Text |
|------------|----------|
| Informative | Describe content/purpose |
| Decorative | Empty string (`alt=""`) |
| Functional | Describe action (not appearance) |
| Complex (charts) | Brief alt + long description |

### Examples

```tsx
// ✅ Informative image
<img src="dashboard-screenshot.png" alt="Sales dashboard showing Q3 revenue of $125,000" />

// ✅ Decorative image (handled by CSS background usually)
<img src="decorative-wave.svg" alt="" role="presentation" />

// ✅ Functional image
<button>
  <img src="search-icon.svg" alt="Search" />
</button>

// ✅ Complex image
<figure>
  <img src="revenue-chart.png" alt="Revenue chart showing growth from Q1 to Q4" />
  <figcaption>
    Revenue increased 45% year over year. Q4 saw the strongest growth at $125K.
  </figcaption>
</figure>
```

---

## Form Accessibility

### Labels

```tsx
// ✅ Explicit label association
<label htmlFor="email">Email address</label>
<input id="email" type="email" name="email" />

// ✅ Implicit label (wrapping)
<label>
  Email address
  <input type="email" name="email" />
</label>

// ❌ Missing label
<input type="email" placeholder="Enter email" />

// ✅ Visually hidden label (icon-only fields)
<label>
  <span className="sr-only">Search</span>
  <input type="search" placeholder="Search..." />
</label>
```

### Error Messages

```tsx
// ✅ Error announced by screen reader
<div>
  <label htmlFor="email">Email</label>
  <input 
    id="email"
    type="email"
    aria-invalid={hasError}
    aria-describedby={hasError ? 'email-error' : undefined}
  />
  {hasError && (
    <span id="email-error" className="text-red-600" role="alert">
      Please enter a valid email address
    </span>
  )}
</div>
```

### Required Fields

```tsx
// ✅ Indicate required fields
<label htmlFor="email">
  Email <span aria-label="required">*</span>
</label>
<input 
  id="email" 
  type="email" 
  required 
  aria-required="true"
/>
```

---

## ARIA Usage

### When to Use ARIA

| Use ARIA | Don't Use ARIA |
|----------|----------------|
| Custom components (tabs, modals) | When semantic HTML exists |
| Dynamic content updates | For styling |
| Complex widgets | Redundant labeling |

### Common Patterns

```tsx
// ✅ Button group with selected state
<div role="group" aria-label="View options">
  <button aria-pressed={view === 'grid'}>Grid</button>
  <button aria-pressed={view === 'list'}>List</button>
</div>

// ✅ Progress indicator
<div role="progressbar" aria-valuenow={60} aria-valuemin={0} aria-valuemax={100}>
  60% complete
</div>

// ✅ Live region for updates
<div aria-live="polite" aria-atomic="true">
  {notificationMessage}
</div>

// ❌ Unnecessary ARIA
<button role="button">Click me</button> {/* Button already has implicit role */}
```

---

## Keyboard Navigation

### Required Behaviors

| Element | Key | Action |
|---------|-----|--------|
| Links, buttons | Enter | Activate |
| Checkboxes | Space | Toggle |
| Radio buttons | ↑/↓ | Change selection |
| Select | ↑/↓ or letter | Change option |
| Modal | Escape | Close |
| Menu | ↑/↓/Enter | Navigate/activate |

### Focus Management

```tsx
// ✅ Restore focus after modal closes
function Modal({ isOpen, onClose, triggerRef }) {
  useEffect(() => {
    if (!isOpen && triggerRef.current) {
      triggerRef.current.focus();
    }
  }, [isOpen]);
  
  // ...
}
```

---

## Screen Reader Text

### Pattern

```tsx
// ✅ Visually hidden text for screen readers
<span className="sr-only">Opens in new tab</span>

// Tailwind sr-only utility equivalent:
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.sr-only:focus {
  position: static;
  width: auto;
  height: auto;
  padding: inherit;
  margin: inherit;
  overflow: visible;
  clip: auto;
  white-space: normal;
}
```

---

## Mobile Accessibility

### Touch Targets

```tsx
// ✅ Minimum 44x44px touch target
<button className="min-h-[44px] min-w-[44px] p-2">
  Icon button
</button>
```

### Responsive Text

```tsx
// ✅ Respect user font size settings
html {
  font-size: 100%; /* Don't override with px */
}

// ✅ Fluid typography
<h1 className="text-2xl md:text-3xl lg:text-4xl">
  Responsive heading
</h1>
```

---

## Testing Checklist

- [ ] Keyboard navigation works (Tab, Enter, Escape, arrows)
- [ ] Focus indicators visible on all interactive elements
- [ ] Headings in logical order (no skipped levels)
- [ ] All images have appropriate alt text
- [ ] Form labels associated with inputs
- [ ] Error messages announced (aria-live or role="alert")
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Touch targets minimum 44x44px on mobile
- [ ] Screen reader announces content correctly
- [ ] Skip link present and functional

---

## Linting Tools

```bash
# ESLint plugin
npm install eslint-plugin-jsx-a11y --save-dev

# Jest testing
npm install jest-axe @testing-library/jest-dom --save-dev

# Storybook addon
npm install @storybook/addon-a11y --save-dev

# CLI scanner
npx pa11y https://your-site.com
```

---

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Articles](https://webaim.org/articles/)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)
