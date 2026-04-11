---
language: typescript
domain: frontend
type: pattern
title: Navigation Header Component
archetype: landing-page
pattern_scope: component
semantic_role: navigation
generation_priority: 1
tags: navigation, header, react, typescript, tailwind, mobile-menu
---

# Navigation Header Component

A responsive navigation header with mobile hamburger menu and accessible keyboard navigation.

## Component Structure

```tsx
interface NavItem {
  label: string;
  href: string;
  isActive?: boolean;
}

interface HeaderProps {
  logo: React.ReactNode;
  navItems: NavItem[];
  cta?: {
    text: string;
    href: string;
  };
}

export function Header({ logo, navItems, cta }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="container mx-auto px-4">
        <nav className="flex items-center justify-between h-16" aria-label="Main navigation">
          {/* Logo */}
          <a href="/" className="flex items-center" aria-label="Home">
            {logo}
          </a>

          {/* Desktop Navigation */}
          <ul className="hidden md:flex items-center gap-8" role="menubar">
            {navItems.map((item, i) => (
              <li key={i} role="none">
                <a
                  href={item.href}
                  role="menuitem"
                  aria-current={item.isActive ? "page" : undefined}
                  className={`text-sm font-medium transition-colors hover:text-blue-600 ${
                    item.isActive ? "text-blue-600" : "text-gray-700"
                  }`}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>

          {/* CTA Button */}
          {cta && (
            <div className="hidden md:block">
              <a
                href={cta.href}
                className="inline-flex items-center px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {cta.text}
              </a>
            </div>
          )}

          {/* Mobile Menu Button */}
          <button
            type="button"
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" aria-hidden="true" />
            ) : (
              <Menu className="w-6 h-6" aria-hidden="true" />
            )}
          </button>
        </nav>

        {/* Mobile Menu */}
        <div
          id="mobile-menu"
          className={`md:hidden overflow-hidden transition-all duration-300 ${
            mobileMenuOpen ? "max-h-96 py-4" : "max-h-0"
          }`}
        >
          <ul className="space-y-4" role="menu">
            {navItems.map((item, i) => (
              <li key={i} role="none">
                <a
                  href={item.href}
                  role="menuitem"
                  aria-current={item.isActive ? "page" : undefined}
                  className={`block text-base font-medium ${
                    item.isActive ? "text-blue-600" : "text-gray-700"
                  }`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item.label}
                </a>
              </li>
            ))}
            {cta && (
              <li role="none">
                <a
                  href={cta.href}
                  role="menuitem"
                  className="block text-base font-semibold text-blue-600"
                >
                  {cta.text}
                </a>
              </li>
            )}
          </ul>
        </div>
      </div>
    </header>
  );
}
```

## Usage

```tsx
<Header
  logo={<img src="/logo.svg" alt="Company Logo" className="h-8" />}
  navItems={[
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing", isActive: true },
    { label: "About", href: "#about" },
  ]}
  cta={{ text: "Get Started", href: "/signup" }}
/>
```

## Accessibility Notes

- role="menubar" and role="menuitem" for desktop nav
- aria-current for active page
- aria-expanded for mobile menu state
- aria-label for menu toggle button

## Related Patterns

- Footer (for complementary navigation)
- Hero Section (for header integration)
