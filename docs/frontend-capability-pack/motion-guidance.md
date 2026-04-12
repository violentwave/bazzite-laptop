# Motion Guidance

Animation decision framework for React/Tailwind projects.

---

## Core Decision Tree

```
Need motion?
├── No → Static design
├── Yes → What's the purpose?
    ├── Micro-interaction (hover, focus) → Tailwind transitions
    ├── State change (open/close) → Tailwind transitions + motion-safe
    ├── Entrance/reveal (scroll, load) → Framer Motion
    ├── Complex orchestration (stagger, gesture) → Framer Motion
    └── Layout shift (reorder, resize) → Framer Motion layout
```

---

## Tailwind Transitions (First Choice)

### When to Use

- Hover states
- Focus states
- Simple open/close toggles
- Color/opacity changes

### Pattern

```tsx
// ✅ Hover with transition
<button className="transition-colors duration-200 ease-out hover:bg-blue-600">
  Hover me
</button>

// ✅ Focus with ring
<input className="transition-shadow duration-150 focus:ring-2 focus:ring-blue-500" />

// ✅ Collapsible panel
<div className="transition-all duration-300 ease-in-out data-[open=true]:h-48 data-[open=false]:h-0">
  Content
</div>
```

### Motion-Safe Wrapper

```tsx
// ✅ Only animate if user hasn't requested reduced motion
<div className="motion-safe:transition-transform motion-safe:duration-300 hover:motion-safe:scale-105">
  Scales on hover (if motion allowed)
</div>

// ✅ Or disable transitions for reduced motion
<div className="transition-opacity duration-300 motion-reduce:transition-none">
  Fades in (disabled if reduced motion)
</div>
```

---

## Framer Motion (When Needed)

### When to Use

- Entrance animations on scroll
- Staggered list reveals
- Gesture-driven interactions
- Layout animations
- Complex orchestration

### Basic Pattern

```tsx
import { motion } from 'framer-motion';

// ✅ Simple fade in
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.3 }}
>
  Content
</motion.div>
```

### Reduced Motion Support

```tsx
import { motion, useReducedMotion } from 'framer-motion';

function FadeIn({ children }) {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.3 }}
    >
      {children}
    </motion.div>
  );
}
```

---

## Design Tokens for Motion

### CSS Custom Properties

```css
@theme {
  /* Duration */
  --duration-instant: 0ms;
  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --duration-slow: 500ms;
  
  /* Easing */
  --ease-linear: linear;
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  
  /* Stagger */
  --stagger-fast: 50ms;
  --stagger-normal: 100ms;
  --stagger-slow: 150ms;
}
```

### Tailwind Config

```ts
// tailwind.config.ts
export default {
  theme: {
    extend: {
      transitionDuration: {
        'fast': '150ms',
        'normal': '300ms',
        'slow': '500ms',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
};
```

---

## Common Patterns

### Fade In On Mount

```tsx
import { motion } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';

function FadeIn({ children, delay = 0 }) {
  const reduced = useReducedMotion();
  
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ 
        duration: reduced ? 0 : 0.3,
        delay: reduced ? 0 : delay 
      }}
    >
      {children}
    </motion.div>
  );
}
```

### Scroll-Triggered Reveal

```tsx
import { motion } from 'framer-motion';

function ScrollReveal({ children }) {
  const reduced = useReducedMotion();
  
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ 
        duration: reduced ? 0 : 0.5,
        ease: [0.4, 0, 0.2, 1]
      }}
    >
      {children}
    </motion.div>
  );
}
```

### Staggered List

```tsx
import { motion } from 'framer-motion';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

function StaggeredList({ items }) {
  const reduced = useReducedMotion();
  
  if (reduced) {
    return <ul>{items.map(i => <li key={i.id}>{i.content}</li>)}</ul>;
  }
  
  return (
    <motion.ul
      variants={container}
      initial="hidden"
      animate="show"
    >
      {items.map((item) => (
        <motion.li key={item.id} variants={item}>
          {item.content}
        </motion.li>
      ))}
    </motion.ul>
  );
}
```

---

## Premium Effects Guardrail

When using premium visual effects (glow, blur, gradient mesh, layered depth):

- Choose one dominant effect per section.
- Keep animation optional and motion-safe.
- Prefer `transform` and `opacity` transitions over layout-driven animation.
- Re-validate readability after applying overlays or glow treatments.

### Hover Scale (with Tailwind)

```tsx
// ✅ Prefer Tailwind for simple hover effects
<button className="motion-safe:transition-transform motion-safe:duration-200 motion-safe:hover:scale-105">
  Scales on hover
</button>

// ✅ Use Framer Motion only for complex hover
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  transition={{ type: "spring", stiffness: 400, damping: 17 }}
>
  Springy button
</motion.button>
```

### Modal/Drawer

```tsx
import { motion, AnimatePresence } from 'framer-motion';

function Modal({ isOpen, onClose, children }) {
  const reduced = useReducedMotion();
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduced ? false : { opacity: 0 }}
            className="fixed inset-0 bg-black/50"
            onClick={onClose}
          />
          
          {/* Modal */}
          <motion.div
            initial={reduced ? false : { opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reduced ? false : { opacity: 0, scale: 0.95, y: 10 }}
            transition={{ 
              duration: reduced ? 0 : 0.2,
              ease: [0.4, 0, 0.2, 1]
            }}
            className="fixed inset-0 m-auto h-fit w-fit max-w-lg"
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

---

## Performance Guidelines

### GPU-Accelerated Properties

✅ **Safe to animate (composited):**
- `transform` (translate, scale, rotate)
- `opacity`

❌ **Avoid animating (triggers layout/paint):**
- `width`, `height`, `top`, `left`
- `margin`, `padding`
- `background-color` (on large areas)

### will-change Hint

```tsx
// ✅ Add will-change for elements that will animate
<motion.div
  style={{ willChange: 'transform, opacity' }}
  animate={{ x: 100 }}
>
  Animated content
</motion.div>
```

### Animation Duration Limits

| Type | Maximum Duration |
|------|------------------|
| Micro-interaction | 150ms |
| State change | 300ms |
| Entrance | 500ms |
| Complex sequence | 800ms |

---

## Reduced Motion Hook

```ts
// hooks/useReducedMotion.ts
import { useState, useEffect } from 'react';

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mediaQuery.matches);
    
    const handler = (event: MediaQueryListEvent) => {
      setReduced(event.matches);
    };
    
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);
  
  return reduced;
}
```

---

## Anti-Patterns

### ❌ Don't: Animate Everything

```tsx
// Bad: Every element animates
<div className="animate-fade">
  <h1 className="animate-slide">Title</h1>
  <p className="animate-fade">Content</p>
  <button className="animate-bounce">Click</button>
</div>
```

### ❌ Don't: Long Durations

```tsx
// Bad: Animation takes too long
<motion.div transition={{ duration: 2 }}>
  Too slow
</motion.div>
```

### ❌ Don't: Ignore Reduced Motion

```tsx
// Bad: No reduced motion support
<motion.div animate={{ x: 100, rotate: 360 }}>
  Ignores user preference
</motion.div>
```

### ❌ Don't: Layout-Triggering Animations

```tsx
// Bad: Animates layout properties
<motion.div animate={{ width: 300, height: 200 }}>
  Triggers layout recalculation
</motion.div>
```

---

## Decision Summary

| Scenario | Tool | Pattern |
|----------|------|---------|
| Hover/focus feedback | Tailwind | `transition-* hover:*` |
| Simple show/hide | Tailwind | `motion-safe:transition-all` |
| Scroll-triggered reveal | Framer Motion | `whileInView` |
| Staggered list | Framer Motion | `variants` + `staggerChildren` |
| Modal/drawer | Framer Motion | `AnimatePresence` |
| Layout animation | Framer Motion | `layout` prop |
| Gesture-driven | Framer Motion | `drag`, `whileDrag` |

---

## References

- [Framer Motion Docs](https://www.framer.com/motion/)
- [Tailwind Motion](https://tailwindcss.com/docs/animation)
- [prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
