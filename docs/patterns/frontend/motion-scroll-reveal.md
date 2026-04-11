---
language: typescript
domain: frontend
type: recipe
title: Scroll Reveal Animation
archetype: landing-page
pattern_scope: motion
semantic_role: animation
generation_priority: 2
tags: animation, scroll, intersection-observer, react, typescript, tailwind
---

# Scroll Reveal Animation

A scroll-triggered reveal animation using Intersection Observer API with reduced motion support.

## Hook Implementation

```tsx
import { useEffect, useRef, useState } from "react";

interface ScrollRevealOptions {
  threshold?: number;
  rootMargin?: string;
  triggerOnce?: boolean;
}

export function useScrollReveal<T extends HTMLElement>(
  options: ScrollRevealOptions = {}
): [React.RefObject<T>, boolean] {
  const { threshold = 0.1, rootMargin = "0px", triggerOnce = true } = options;
  const ref = useRef<T>(null);
  const [isVisible, setIsVisible] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    // If reduced motion is preferred, immediately show
    if (prefersReducedMotion) {
      setIsVisible(true);
      return;
    }

    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          if (triggerOnce) {
            observer.unobserve(element);
          }
        } else if (!triggerOnce) {
          setIsVisible(false);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [threshold, rootMargin, triggerOnce, prefersReducedMotion]);

  return [ref, isVisible];
}

interface ScrollRevealProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "down" | "left" | "right";
}

export function ScrollReveal({
  children,
  className = "",
  delay = 0,
  direction = "up",
}: ScrollRevealProps) {
  const [ref, isVisible] = useScrollReveal<HTMLDivElement>();
  const prefersReducedMotion = useReducedMotion();

  const getTransform = () => {
    if (prefersReducedMotion || isVisible) return "translate3d(0, 0, 0)";

    const distance = "2rem";
    switch (direction) {
      case "up":
        return `translate3d(0, ${distance}, 0)`;
      case "down":
        return `translate3d(0, -${distance}, 0)`;
      case "left":
        return `translate3d(${distance}, 0, 0)`;
      case "right":
        return `translate3d(-${distance}, 0, 0)`;
      default:
        return "translate3d(0, 0, 0)";
    }
  };

  return (
    <div
      ref={ref}
      className={`transition-all ${className}`}
      style={{
        opacity: isVisible || prefersReducedMotion ? 1 : 0,
        transform: getTransform(),
        transitionDuration: prefersReducedMotion ? "0ms" : "700ms",
        transitionDelay: prefersReducedMotion ? "0ms" : `${delay}ms`,
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
        willChange: prefersReducedMotion ? "auto" : "opacity, transform",
      }}
    >
      {children}
    </div>
  );
}
```

## Usage

```tsx
<ScrollReveal direction="up" delay={0}>
  <h2>Section Heading</h2>
</ScrollReveal>

<ScrollReveal direction="up" delay={100}>
  <p>First paragraph revealed after heading</p>
</ScrollReveal>

<ScrollReveal direction="left" delay={0}>
  <ImageCard />
</ScrollReveal>
```

## Accessibility Notes

- Respects prefers-reduced-motion automatically
- Uses translate3d for GPU acceleration
- Trigger once by default (no re-animation on scroll up)

## Related Patterns

- Fade-In On Mount (for page load animations)
- Staggered List (for list animations)
