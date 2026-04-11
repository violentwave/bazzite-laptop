---
language: typescript
domain: frontend
type: pattern
title: Hero Section Component
archetype: landing-page
pattern_scope: section
semantic_role: hero
generation_priority: 1
tags: hero, landing-page, react, typescript, tailwind, cta
---

# Hero Section Component

A responsive hero section for landing pages with headline, subheadline, primary CTA, and social proof.

## Component Structure

```tsx
interface HeroProps {
  headline: string;
  subheadline: string;
  primaryCTA: {
    text: string;
    href: string;
  };
  socialProof?: {
    avatars: string[];
    text: string;
  };
}

export function Hero({
  headline,
  subheadline,
  primaryCTA,
  socialProof,
}: HeroProps) {
  return (
    <section
      role="banner"
      aria-labelledby="hero-headline"
      className="relative overflow-hidden"
    >
      <div className="container mx-auto px-4 py-16 sm:py-24 lg:py-32">
        <div className="max-w-3xl mx-auto text-center">
          <h1
            id="hero-headline"
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight"
          >
            {headline}
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-gray-600">
            {subheadline}
          </p>
          <div className="mt-10">
            <a
              href={primaryCTA.href}
              className="inline-flex items-center px-8 py-4 text-lg font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {primaryCTA.text}
            </a>
          </div>
          {socialProof && (
            <div className="mt-8 flex items-center justify-center gap-4">
              <div className="flex -space-x-2">
                {socialProof.avatars.map((avatar, i) => (
                  <img
                    key={i}
                    src={avatar}
                    alt=""
                    className="w-10 h-10 rounded-full border-2 border-white"
                    loading="lazy"
                  />
                ))}
              </div>
              <p className="text-sm text-gray-500">{socialProof.text}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
```

## Usage

```tsx
<Hero
  headline="Build Better Software, Faster"
  subheadline="AI-powered code analysis and optimization for modern development teams."
  primaryCTA={{ text: "Start Free Trial", href: "/signup" }}
  socialProof={{
    avatars: ["/user1.jpg", "/user2.jpg", "/user3.jpg"],
    text: "Trusted by 10,000+ developers",
  }}
/>
```

## Accessibility Notes

- `role="banner"` identifies the hero landmark
- `aria-labelledby` associates headline with section
- All CTAs have visible focus states
- Images have empty alt (decorative) or descriptive alt

## Related Patterns

- CTA Section (for secondary conversion)
- Feature Grid (for value proposition)
