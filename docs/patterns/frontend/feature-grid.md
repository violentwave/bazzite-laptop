---
language: typescript
domain: frontend
type: pattern
title: Feature Grid Component
archetype: landing-page
pattern_scope: section
semantic_role: feature
generation_priority: 2
tags: feature, grid, react, typescript, tailwind, icons
---

# Feature Grid Component

A responsive feature grid with icons, titles, and descriptions for showcasing product capabilities.

## Component Structure

```tsx
interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

interface FeatureGridProps {
  headline?: string;
  subheadline?: string;
  features: Feature[];
  columns?: 2 | 3 | 4;
}

export function FeatureGrid({
  headline,
  subheadline,
  features,
  columns = 3,
}: FeatureGridProps) {
  const gridCols = {
    2: "sm:grid-cols-2",
    3: "sm:grid-cols-2 lg:grid-cols-3",
    4: "sm:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <section className="py-16 sm:py-24" aria-labelledby="features-headline">
      <div className="container mx-auto px-4">
        {(headline || subheadline) && (
          <div className="max-w-2xl mx-auto text-center mb-12">
            {headline && (
              <h2 id="features-headline" className="text-3xl font-bold">
                {headline}
              </h2>
            )}
            {subheadline && (
              <p className="mt-4 text-lg text-gray-600">{subheadline}</p>
            )}
          </div>
        )}
        <div className={`grid gap-8 ${gridCols[columns]}`}>
          {features.map((feature, index) => (
            <FeatureCard key={index} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ icon, title, description }: Feature) {
  return (
    <div className="flex flex-col items-start p-6 rounded-xl bg-gray-50">
      <div className="p-3 rounded-lg bg-blue-100 text-blue-600" aria-hidden="true">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-gray-600">{description}</p>
    </div>
  );
}
```

## Usage

```tsx
<FeatureGrid
  headline="Everything you need"
  subheadline="All the features for modern development"
  features={[
    {
      icon: <Zap className="w-6 h-6" />,
      title: "Lightning Fast",
      description: "Optimized performance for any workload.",
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "Secure by Default",
      description: "Enterprise-grade security built-in.",
    },
  ]}
/>
```

## Accessibility Notes

- Section has aria-labelledby linking to headline
- Icons are aria-hidden (decorative)
- Grid uses semantic heading hierarchy

## Related Patterns

- Alternating Feature Section (for detailed features)
- Testimonial Section (for social proof)
