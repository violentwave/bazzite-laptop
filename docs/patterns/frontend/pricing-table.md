---
language: typescript
domain: frontend
type: pattern
title: Pricing Table Component
archetype: landing-page
pattern_scope: section
semantic_role: pricing
generation_priority: 4
tags: pricing, table, react, typescript, tailwind, comparison
---

# Pricing Table Component

A responsive pricing table with 2-4 tiers, feature comparison, and recommended tier highlighting.

## Component Structure

```tsx
interface PricingTier {
  name: string;
  price: {
    monthly: number;
    annually: number;
  };
  description: string;
  features: string[];
  recommended?: boolean;
  cta: {
    text: string;
    href: string;
  };
}

interface PricingTableProps {
  headline?: string;
  subheadline?: string;
  tiers: PricingTier[];
  showToggle?: boolean;
}

export function PricingTable({
  headline = "Simple, transparent pricing",
  subheadline,
  tiers,
  showToggle = true,
}: PricingTableProps) {
  const [isAnnual, setIsAnnual] = useState(false);

  return (
    <section className="py-16 sm:py-24" aria-labelledby="pricing-headline">
      <div className="container mx-auto px-4">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 id="pricing-headline" className="text-3xl font-bold">
            {headline}
          </h2>
          {subheadline && (
            <p className="mt-4 text-lg text-gray-600">{subheadline}</p>
          )}
          {showToggle && (
            <div className="mt-8 flex items-center justify-center gap-4">
              <span className={`${!isAnnual ? "font-semibold" : "text-gray-500"}`}>
                Monthly
              </span>
              <button
                role="switch"
                aria-checked={isAnnual}
                onClick={() => setIsAnnual(!isAnnual)}
                className="relative w-14 h-8 rounded-full bg-blue-600 transition-colors"
              >
                <span
                  className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-transform ${
                    isAnnual ? "translate-x-7" : "translate-x-1"
                  }`}
                />
              </button>
              <span className={`${isAnnual ? "font-semibold" : "text-gray-500"}`}>
                Annual
                <span className="ml-1 text-sm text-green-600">Save 20%</span>
              </span>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {tiers.map((tier, i) => (
            <PricingCard key={i} tier={tier} isAnnual={isAnnual} />
          ))}
        </div>
      </div>
    </section>
  );
}

function PricingCard({ tier, isAnnual }: { tier: PricingTier; isAnnual: boolean }) {
  const price = isAnnual ? tier.price.annually : tier.price.monthly;

  return (
    <div
      className={`relative p-8 rounded-2xl border-2 ${
        tier.recommended
          ? "border-blue-500 bg-blue-50"
          : "border-gray-200 bg-white"
      }`}
    >
      {tier.recommended && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 text-sm font-semibold text-white bg-blue-500 rounded-full">
          Recommended
        </span>
      )}
      <div aria-label={tier.recommended ? "Recommended plan" : undefined}>
        <h3 className="text-xl font-bold">{tier.name}</h3>
        <p className="mt-2 text-gray-600">{tier.description}</p>
        <div className="mt-6">
          <span className="text-4xl font-bold">${price}</span>
          <span className="text-gray-500">/month</span>
        </div>
        <ul className="mt-6 space-y-3">
          {tier.features.map((feature, i) => (
            <li key={i} className="flex items-start gap-3">
              <Check className="w-5 h-5 text-green-500 flex-shrink-0" aria-hidden="true" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
        <a
          href={tier.cta.href}
          className={`mt-8 block w-full py-3 px-4 text-center font-semibold rounded-lg ${
            tier.recommended
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-100 text-gray-900 hover:bg-gray-200"
          }`}
        >
          {tier.cta.text}
        </a>
      </div>
    </div>
  );
}
```

## Accessibility Notes

- Toggle uses role="switch" with aria-checked
- Recommended tier has aria-label
- Feature list uses semantic ul/li structure

## Related Patterns

- Feature Grid (for feature details)
- CTA Section (for alternative conversion)
