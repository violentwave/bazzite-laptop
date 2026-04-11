---
language: typescript
domain: frontend
type: pattern
title: Footer Component
archetype: landing-page
pattern_scope: component
semantic_role: footer
generation_priority: 10
tags: footer, navigation, react, typescript, tailwind, newsletter
---

# Footer Component

A comprehensive footer with navigation columns, social links, and optional newsletter signup.

## Component Structure

```tsx
interface FooterColumn {
  title: string;
  links: { label: string; href: string; external?: boolean }[];
}

interface FooterProps {
  logo?: React.ReactNode;
  description?: string;
  columns: FooterColumn[];
  socialLinks?: { icon: React.ReactNode; href: string; label: string }[];
  newsletter?: {
    title: string;
    description: string;
    onSubmit: (email: string) => Promise<void>;
  };
  copyright?: string;
}

export function Footer({
  logo,
  description,
  columns,
  socialLinks,
  newsletter,
  copyright = "All rights reserved.",
}: FooterProps) {
  return (
    <footer className="bg-gray-900 text-white" role="contentinfo">
      <div className="container mx-auto px-4 py-12 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8">
          {/* Brand Column */}
          <div className="col-span-2">
            {logo && <div className="mb-4">{logo}</div>}
            {description && (
              <p className="text-gray-400 text-sm max-w-xs">{description}</p>
            )}
            {socialLinks && (
              <div className="mt-6 flex gap-4">
                {socialLinks.map((link, i) => (
                  <a
                    key={i}
                    href={link.href}
                    aria-label={link.label}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    {link.icon}
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Navigation Columns */}
          {columns.map((column, i) => (
            <div key={i}>
              <h3 className="text-sm font-semibold uppercase tracking-wider mb-4">
                {column.title}
              </h3>
              <ul className="space-y-3">
                {column.links.map((link, j) => (
                  <li key={j}>
                    <a
                      href={link.href}
                      className="text-gray-400 hover:text-white text-sm transition-colors"
                      {...(link.external
                        ? { target: "_blank", rel: "noopener noreferrer" }
                        : {})}
                    >
                      {link.label}
                      {link.external && (
                        <ExternalLink className="inline w-3 h-3 ml-1" aria-hidden="true" />
                      )}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {/* Newsletter */}
          {newsletter && (
            <div className="col-span-2 md:col-span-4 lg:col-span-1">
              <h3 className="text-sm font-semibold uppercase tracking-wider mb-4">
                {newsletter.title}
              </h3>
              <p className="text-gray-400 text-sm mb-4">{newsletter.description}</p>
              <NewsletterForm onSubmit={newsletter.onSubmit} />
            </div>
          )}
        </div>

        {/* Copyright */}
        <div className="mt-12 pt-8 border-t border-gray-800 text-center text-sm text-gray-400">
          <p>&copy; {new Date().getFullYear()} {copyright}</p>
        </div>
      </div>
    </footer>
  );
}

function NewsletterForm({ onSubmit }: { onSubmit: (email: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsSubmitting(true);
    try {
      await onSubmit(email);
      setIsSubmitted(true);
      setEmail("");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return <p className="text-green-400 text-sm">Thanks for subscribing!</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter your email"
        className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        required
      />
      <button
        type="submit"
        disabled={isSubmitting}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      >
        Subscribe
      </button>
    </form>
  );
}
```

## Accessibility Notes

- role="contentinfo" for footer landmark
- aria-label for icon-only social links
- External links have indicator and attributes
- Semantic heading hierarchy

## Related Patterns

- Navigation Header (for complementary navigation)
- Contact Form (for contact options)
