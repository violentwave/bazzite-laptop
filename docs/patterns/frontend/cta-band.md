---
language: typescript
domain: frontend
type: pattern
title: CTA Band Component
archetype: landing-page
pattern_scope: section
semantic_role: cta
generation_priority: 6
tags: cta, conversion, react, typescript, tailwind, banner
---

# CTA Band Component

A high-contrast call-to-action band for bottom-of-page conversion.

## Component Structure

```tsx
interface CTABandProps {
  headline: string;
  description?: string;
  primaryCTA: {
    text: string;
    href: string;
  };
  secondaryCTA?: {
    text: string;
    href: string;
  };
  variant?: "default" | "dark";
}

export function CTABand({
  headline,
  description,
  primaryCTA,
  secondaryCTA,
  variant = "default",
}: CTABandProps) {
  const bgClass =
    variant === "dark"
      ? "bg-gray-900 text-white"
      : "bg-blue-600 text-white";

  return (
    <section className={`py-16 sm:py-24 ${bgClass}`} aria-labelledby="cta-headline">
      <div className="container mx-auto px-4 text-center">
        <h2 id="cta-headline" className="text-3xl sm:text-4xl font-bold">
          {headline}
        </h2>
        {description && (
          <p className="mt-4 text-lg text-blue-100 max-w-2xl mx-auto">
            {description}
          </p>
        )}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href={primaryCTA.href}
            className="inline-flex items-center px-8 py-4 text-lg font-semibold text-blue-600 bg-white rounded-lg hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2"
          >
            {primaryCTA.text}
          </a>
          {secondaryCTA && (
            <a
              href={secondaryCTA.href}
              className="inline-flex items-center px-8 py-4 text-lg font-semibold text-white border-2 border-white rounded-lg hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2"
            >
              {secondaryCTA.text}
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
```

## Usage

```tsx
<CTABand
  headline="Ready to get started?"
  description="Join thousands of teams already using our platform."
  primaryCTA={{ text: "Start Free Trial", href: "/signup" }}
  secondaryCTA={{ text: "Contact Sales", href: "/contact" }}
/>
```

## Accessibility Notes

- High contrast (white on blue or dark)
- Focus visible on all buttons
- aria-labelledby links section to headline

## Related Patterns

- Hero Section (for top-of-page conversion)
- Pricing Table (for plan-specific CTAs)
