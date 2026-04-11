---
language: typescript
domain: frontend
type: recipe
title: Fade-In On Mount Animation
archetype: landing-page
pattern_scope: motion
semantic_role: animation
generation_priority: 1
tags: animation, fade-in, motion, react, typescript, tailwind, prefers-reduced-motion
---

# Fade-In On Mount Animation

A reusable fade-in animation hook and component that respects reduced motion preferences.

## Hook Implementation

```tsx
import { useEffect, useState } from "react";

export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  return prefersReducedMotion;
}

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

export function FadeIn({
  children,
  delay = 0,
  duration = 500,
  className = "",
}: FadeInProps) {
  const [isVisible, setIsVisible] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (prefersReducedMotion) {
      setIsVisible(true);
      return;
    }

    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay, prefersReducedMotion]);

  return (
    <div
      className={`transition-opacity ${className}`}
      style={{
        opacity: isVisible ? 1 : 0,
        transitionDuration: prefersReducedMotion ? "0ms" : `${duration}ms`,
        willChange: prefersReducedMotion ? "auto" : "opacity",
      }}
    >
      {children}
    </div>
  );
}
```

## Usage

```tsx
<FadeIn delay={0}>
  <HeroSection />
</FadeIn>
<FadeIn delay={200}>
  <FeatureGrid />
</FadeIn>
<FadeIn delay={400}>
  <Testimonials />
</FadeIn>
```

## CSS Alternative (Tailwind)

```css
@media (prefers-reduced-motion: reduce) {
  .motion-safe\:fade-in {
    animation: none;
    opacity: 1;
  }
}

@supports not (prefers-reduced-motion: reduce) {
  .motion-safe\:fade-in {
    animation: fadeIn 500ms ease-out forwards;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
```

## Accessibility Notes

- Always check prefers-reduced-motion
- Skip animation if user prefers reduced motion
- Use will-change sparingly (GPU hint)

## Related Patterns

- Scroll Reveal (for scroll-triggered animations)
- Staggered List (for sequential animations)
