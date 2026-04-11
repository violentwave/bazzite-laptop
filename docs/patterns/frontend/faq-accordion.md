---
language: typescript
domain: frontend
type: pattern
title: FAQ Accordion Component
archetype: landing-page
pattern_scope: section
semantic_role: list
generation_priority: 5
tags: faq, accordion, react, typescript, tailwind, disclosure
---

# FAQ Accordion Component

An accessible FAQ accordion with smooth expand/collapse animations.

## Component Structure

```tsx
interface FAQItem {
  question: string;
  answer: string;
}

interface FAQAccordionProps {
  headline?: string;
  items: FAQItem[];
}

export function FAQAccordion({
  headline = "Frequently asked questions",
  items,
}: FAQAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="py-16 sm:py-24" aria-labelledby="faq-headline">
      <div className="container mx-auto px-4 max-w-3xl">
        <h2 id="faq-headline" className="text-3xl font-bold text-center mb-12">
          {headline}
        </h2>
        <div className="space-y-4">
          {items.map((item, index) => (
            <FAQItemComponent
              key={index}
              item={item}
              isOpen={openIndex === index}
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
              index={index}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQItemComponent({
  item,
  isOpen,
  onClick,
  index,
}: {
  item: FAQItem;
  isOpen: boolean;
  onClick: () => void;
  index: number;
}) {
  const answerId = `faq-answer-${index}`;
  const buttonId = `faq-button-${index}`;

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        id={buttonId}
        aria-expanded={isOpen}
        aria-controls={answerId}
        onClick={onClick}
        className="w-full flex items-center justify-between p-6 text-left hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset"
      >
        <span className="font-semibold">{item.question}</span>
        <ChevronDown
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>
      <div
        id={answerId}
        role="region"
        aria-labelledby={buttonId}
        className={`overflow-hidden transition-all duration-300 ${
          isOpen ? "max-h-96" : "max-h-0"
        }`}
      >
        <p className="px-6 pb-6 text-gray-600">{item.answer}</p>
      </div>
    </div>
  );
}
```

## Usage

```tsx
<FAQAccordion
  items={[
    {
      question: "How does billing work?",
      answer: "You are billed monthly or annually based on your plan...",
    },
    {
      question: "Can I change my plan?",
      answer: "Yes, you can upgrade or downgrade at any time...",
    },
  ]}
/>
```

## Accessibility Notes

- Uses button for keyboard accessibility
- aria-expanded indicates state
- aria-controls links button to content
- Chevron icon is aria-hidden

## Related Patterns

- Contact Section (for unresolved questions)
- Pricing Table (for plan-specific FAQs)
