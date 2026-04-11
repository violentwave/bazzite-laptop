---
language: typescript
domain: frontend
type: pattern
title: Testimonials Section
archetype: landing-page
pattern_scope: section
semantic_role: testimonial
generation_priority: 3
tags: testimonial, social-proof, react, typescript, tailwind, carousel
---

# Testimonials Section

A testimonials section with carousel/grid options for displaying customer quotes.

## Component Structure

```tsx
interface Testimonial {
  quote: string;
  author: string;
  role: string;
  avatar?: string;
  rating?: number;
}

interface TestimonialsSectionProps {
  headline?: string;
  testimonials: Testimonial[];
  layout?: "grid" | "carousel";
}

export function TestimonialsSection({
  headline = "What our customers say",
  testimonials,
  layout = "grid",
}: TestimonialsSectionProps) {
  return (
    <section
      className="py-16 sm:py-24 bg-gray-50"
      aria-labelledby="testimonials-headline"
    >
      <div className="container mx-auto px-4">
        <h2
          id="testimonials-headline"
          className="text-3xl font-bold text-center mb-12"
        >
          {headline}
        </h2>
        {layout === "grid" ? (
          <TestimonialGrid testimonials={testimonials} />
        ) : (
          <TestimonialCarousel testimonials={testimonials} />
        )}
      </div>
    </section>
  );
}

function TestimonialGrid({ testimonials }: { testimonials: Testimonial[] }) {
  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
      {testimonials.map((t, i) => (
        <TestimonialCard key={i} testimonial={t} />
      ))}
    </div>
  );
}

function TestimonialCard({ testimonial }: { testimonial: Testimonial }) {
  return (
    <article className="p-6 bg-white rounded-xl shadow-sm">
      {testimonial.rating && (
        <div className="flex gap-1 mb-4" aria-label={`${testimonial.rating} out of 5 stars`}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Star
              key={i}
              className={`w-5 h-5 ${
                i < testimonial.rating! ? "text-yellow-400" : "text-gray-200"
              }`}
              fill={i < testimonial.rating! ? "currentColor" : "none"}
            />
          ))}
        </div>
      )}
      <blockquote>
        <p className="text-gray-700 italic">"{testimonial.quote}"</p>
        <footer className="mt-4 flex items-center gap-3">
          {testimonial.avatar && (
            <img
              src={testimonial.avatar}
              alt=""
              className="w-10 h-10 rounded-full"
            />
          )}
          <div>
            <cite className="not-italic font-semibold">{testimonial.author}</cite>
            <p className="text-sm text-gray-500">{testimonial.role}</p>
          </div>
        </footer>
      </blockquote>
    </article>
  );
}
```

## Accessibility Notes

- Uses semantic blockquote and cite elements
- Star ratings have aria-label for screen readers
- Carousel variant must have pause/play controls

## Related Patterns

- Hero Section (for conversion)
- CTA Section (for follow-up action)
