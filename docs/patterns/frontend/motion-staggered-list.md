---
language: typescript
domain: frontend
type: recipe
title: Staggered List Animation
archetype: landing-page
pattern_scope: motion
semantic_role: animation
generation_priority: 3
tags: animation, list, stagger, react, typescript, tailwind, children
---

# Staggered List Animation

A staggered list animation that reveals items sequentially with configurable delay.

## Component Implementation

```tsx
interface StaggeredListProps {
  children: React.ReactNode[];
  staggerDelay?: number;
  initialDelay?: number;
  className?: string;
  itemClassName?: string;
}

export function StaggeredList({
  children,
  staggerDelay = 100,
  initialDelay = 0,
  className = "",
  itemClassName = "",
}: StaggeredListProps) {
  const prefersReducedMotion = useReducedMotion();
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (prefersReducedMotion) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [prefersReducedMotion]);

  return (
    <ul ref={containerRef} className={className}>
      {React.Children.map(children, (child, index) => (
        <li
          className={`transition-all ${itemClassName}`}
          style={{
            opacity: isVisible || prefersReducedMotion ? 1 : 0,
            transform:
              isVisible || prefersReducedMotion
                ? "translateY(0)"
                : "translateY(20px)",
            transitionDelay: prefersReducedMotion
              ? "0ms"
              : `${initialDelay + index * staggerDelay}ms`,
            transitionDuration: "500ms",
            transitionTimingFunction: "ease-out",
          }}
        >
          {child}
        </li>
      ))}
    </ul>
  );
}
```

## Usage

```tsx
<StaggeredList staggerDelay={100} initialDelay={0} className="space-y-4">
  <FeatureCard title="Feature 1" description="..." />
  <FeatureCard title="Feature 2" description="..." />
  <FeatureCard title="Feature 3" description="..." />
  <FeatureCard title="Feature 4" description="..." />
</StaggeredList>
```

## Framer Motion Alternative

```tsx
import { motion } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

export function StaggeredListFM({ children }: { children: React.ReactNode[] }) {
  return (
    <motion.ul
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
    >
      {children.map((child, index) => (
        <motion.li key={index} variants={itemVariants}>
          {child}
        </motion.li>
      ))}
    </motion.ul>
  );
}
```

## Accessibility Notes

- Works with screen readers (no hidden content)
- Respects reduced motion preferences
- Use semantic list structure (ul/li)

## Related Patterns

- Scroll Reveal (for single-element reveals)
- Feature Grid (for card-based layouts)
