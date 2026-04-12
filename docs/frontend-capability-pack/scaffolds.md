# Scaffold Guidance — File Organization

Recommended file structures for React/Tailwind projects.

---

## Core Principles

1. **Component-first** — Atomic sections, composed into pages
2. **Route-based pages** — One file per URL route
3. **Shared layouts** — Common wrappers extracted
4. **Utility colocation** — Helpers live near their consumers

---

## Recommended Project Structure

```
src/
├── components/           # Reusable UI pieces
│   ├── ui/              # Primitive components (Button, Card, Input)
│   ├── layout/          # Layout components (Header, Footer, Sidebar)
│   └── sections/        # Page sections (Hero, Features, CTA)
│   └── illustrations/    # SVG/media illustration components
├── layouts/             # Page-level layout wrappers
│   ├── MainLayout.tsx   # Standard page layout
│   ├── AuthLayout.tsx   # Auth-specific layout
│   └── DashboardLayout.tsx # Dashboard layout
├── pages/               # Route files
│   ├── index.tsx        # Home/landing
│   ├── about.tsx        # About page
│   ├── contact.tsx      # Contact page
│   └── dashboard/
│       ├── index.tsx    # Dashboard home
│       └── settings.tsx # Dashboard settings
├── hooks/               # Custom React hooks
│   ├── useReducedMotion.ts
│   ├── useInView.ts
│   └── useMediaQuery.ts
├── lib/                 # Utilities and helpers
│   ├── utils.ts         # General utilities (cn, etc.)
│   ├── constants.ts     # App constants
│   └── validations.ts   # Zod schemas
├── styles/              # Global styles
│   ├── globals.css      # Tailwind imports + global styles
│   └── tokens.css       # Design tokens (if not using Tailwind config)
└── types/               # TypeScript types
    ├── index.ts         # Main exports
    └── components.ts    # Component prop types
public/
├── images/              # Static images
│   ├── logo.svg
│   └── hero/
├── illustrations/        # Decorative SVG backgrounds/illustrations
├── textures/             # Optional subtle overlays (noise/grain)
├── fonts/               # Self-hosted fonts (if needed)
└── favicon.ico
```

---

## Component Organization

### UI Primitives

Low-level reusable components:

```
components/ui/
├── Button.tsx           # Primary, secondary, ghost variants
├── Card.tsx             # Container with consistent padding/shadow
├── Input.tsx            # Form input with label integration
├── Select.tsx           # Dropdown select
├── Badge.tsx            # Status/chip indicators
└── Icon.tsx             # SVG icon wrapper
```

**Rules:**
- No business logic
- Pure presentational
- Forward refs
- Full TypeScript props

### Layout Components

Structural components:

```
components/layout/
├── Header.tsx           # Navigation header
├── Footer.tsx           # Page footer
├── Sidebar.tsx          # Dashboard sidebar
├── Container.tsx        # Max-width wrapper
└── Grid.tsx             # Custom grid helpers
```

### Section Components

Page-specific sections:

```
components/sections/
├── Hero.tsx             # Hero section
├── Features.tsx         # Feature grid/list
├── Testimonials.tsx     # Social proof
├── Pricing.tsx          # Pricing table
├── CTA.tsx              # Call-to-action
└── FAQ.tsx              # FAQ accordion
```

**Rules:**
- One section per file
- Accept content via props
- Self-contained styling
- Export typed props interface

---

## Layout Patterns

### Main Layout

Standard website layout:

```tsx
// layouts/MainLayout.tsx
interface MainLayoutProps {
  children: React.ReactNode;
  showHeader?: boolean;
  showFooter?: boolean;
}

export function MainLayout({ 
  children, 
  showHeader = true, 
  showFooter = true 
}: MainLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      {showHeader && <Header />}
      <main id="main-content" className="flex-1">
        {children}
      </main>
      {showFooter && <Footer />}
    </div>
  );
}
```

### Dashboard Layout

Admin/dashboard layout:

```tsx
// layouts/DashboardLayout.tsx
interface DashboardLayoutProps {
  children: React.ReactNode;
  pageTitle: string;
}

export function DashboardLayout({ children, pageTitle }: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardHeader title={pageTitle} />
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

---

## Page Patterns

### Landing Page

```tsx
// pages/index.tsx
import { MainLayout } from '@/layouts/MainLayout';
import { Hero } from '@/components/sections/Hero';
import { Features } from '@/components/sections/Features';
import { Testimonials } from '@/components/sections/Testimonials';
import { CTA } from '@/components/sections/CTA';

export default function LandingPage() {
  return (
    <MainLayout>
      <Hero
        headline="Your Product Tagline"
        subheadline="Description of value proposition"
        cta={{ text: "Get Started", href: "/signup" }}
      />
      <Features features={featureData} />
      <Testimonials testimonials={testimonialData} />
      <CTA 
        headline="Ready to start?"
        description="Join thousands of satisfied customers"
        cta={{ text: "Sign Up Now", href: "/signup" }}
      />
    </MainLayout>
  );
}
```

### Dashboard Page

```tsx
// pages/dashboard/index.tsx
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { KpiWidget } from '@/components/KpiWidget';
import { ChartWidget } from '@/components/ChartWidget';
import { RecentActivity } from '@/components/RecentActivity';

export default function DashboardPage() {
  return (
    <DashboardLayout pageTitle="Dashboard">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <KpiWidget title="Revenue" value={125000} change={12.5} format="currency" />
        <KpiWidget title="Users" value={2847} change={8.2} format="number" />
        <KpiWidget title="Conversion" value={3.24} change={-2.1} format="percent" />
        <KpiWidget title="Churn" value={5.1} change={-0.5} format="percent" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <ChartWidget title="Revenue Over Time" data={revenueData} />
        <RecentActivity activities={activityData} />
      </div>
    </DashboardLayout>
  );
}
```

---

## Design Tokens Structure

### CSS Custom Properties

```css
/* styles/tokens.css */
@theme {
  /* Colors */
  --color-primary: #3b82f6;
  --color-primary-dark: #2563eb;
  --color-secondary: #8b5cf6;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-neutral-50: #f9fafb;
  --color-neutral-100: #f3f4f6;
  --color-neutral-200: #e5e7eb;
  --color-neutral-800: #1f2937;
  --color-neutral-900: #111827;

  /* Typography */
  --font-sans: ui-sans-serif, system-ui, sans-serif;
  --font-heading: ui-sans-serif, system-ui, sans-serif;
  --font-mono: ui-monospace, monospace;

  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-4: 1rem;
  --space-8: 2rem;
  --space-16: 4rem;

  /* Motion */
  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --duration-slow: 500ms;
  --ease-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```

### Tailwind Config (if needed)

```ts
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          dark: 'var(--color-primary-dark)',
        },
        secondary: 'var(--color-secondary)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        heading: ['var(--font-heading)'],
      },
      animation: {
        'fade-in': 'fadeIn var(--duration-normal) var(--ease-out)',
        'slide-up': 'slideUp var(--duration-normal) var(--ease-out)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};

export default config;
```

---

## Utility Patterns

### Class Name Utilities

```ts
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind classes with conflict resolution
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Format Utilities

```ts
// lib/format.ts
export function formatCurrency(value: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(value);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}
```

---

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Components | PascalCase | `Button.tsx`, `HeroSection.tsx` |
| Utilities | camelCase | `utils.ts`, `formatCurrency.ts` |
| Constants | UPPER_SNAKE | `API_ENDPOINTS.ts` |
| Hooks | use + PascalCase | `useReducedMotion.ts` |
| Types | PascalCase | `types.ts`, `ComponentProps.ts` |
| Pages | lowercase | `index.tsx`, `about.tsx` |
| Layouts | PascalCase + Layout | `MainLayout.tsx` |

---

## Import Organization

```tsx
// 1. React/Next imports
import React, { useState, useEffect } from 'react';
import Head from 'next/head';

// 2. Third-party libraries
import { motion } from 'framer-motion';
import { z } from 'zod';

// 3. Absolute imports (@/)
import { Button } from '@/components/ui/Button';
import { MainLayout } from '@/layouts/MainLayout';
import { cn } from '@/lib/utils';

// 4. Relative imports (./)
import { Hero } from './Hero';
import styles from './Page.module.css';
```

---

## References

- [Site Archetypes](site-archetypes/) — Per-type scaffold specifics
- [Accessibility Guardrails](accessibility-guardrails.md) — Constraint details
- [Motion Guidance](motion-guidance.md) — Animation patterns
- [Validation Flow](validation-flow.md) — Post-generation checks
