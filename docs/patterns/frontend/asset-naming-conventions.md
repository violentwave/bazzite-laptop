---
language: typescript
domain: frontend
type: pattern
title: Asset Naming and Sizing Conventions
archetype: landing-page
pattern_scope: asset
semantic_role: token
generation_priority: 1
tags: assets, images, naming, conventions, workflow
---

# Asset Naming and Sizing Conventions

Standard naming and sizing conventions for frontend assets to ensure consistency and performance.

## Image Naming Convention

```
{component}-{variant}-{size}.{ext}

Examples:
  hero-background-desktop.jpg
  hero-background-mobile.jpg
  feature-icon-analytics.svg
  testimonial-avatar-01.jpg
  logo-primary.svg
  logo-white.svg
```

## Directory Structure

```
public/
├── images/
│   ├── hero/
│   │   ├── hero-bg-desktop.jpg
│   │   ├── hero-bg-mobile.jpg
│   │   └── hero-product-screenshot.png
│   ├── features/
│   │   ├── feature-analytics.svg
│   │   ├── feature-security.svg
│   │   └── feature-speed.svg
│   ├── testimonials/
│   │   ├── avatar-sarah.jpg
│   │   ├── avatar-michael.jpg
│   │   └── avatar-emily.jpg
│   └── logos/
│       ├── client-acme.svg
│       ├── client-globex.svg
│       └── client-initech.svg
├── icons/
│   ├── icon-check.svg
│   ├── icon-arrow-right.svg
│   └── icon-star.svg
└── fonts/
    ├── Inter-Regular.woff2
    └── Inter-Bold.woff2
```

## Image Sizes

| Type | Width | Format | Notes |
|------|-------|--------|-------|
| Hero Background | 1920px | WebP/JPG | With mobile variant at 768px |
| Hero Product | 800px | PNG | Transparent background |
| Feature Icons | 64px | SVG | Scalable, single color |
| Testimonial Avatars | 200px | WebP/JPG | Square, 1:1 ratio |
| Client Logos | 200px | SVG | Monochrome for flexibility |
| Gallery Thumbnails | 400px | WebP | 4:3 ratio |
| Gallery Full | 1600px | WebP | 4:3 ratio, lazy loaded |

## Responsive Images

```tsx
// Using srcset for responsive images
<img
  src="hero-bg-mobile.jpg"
  srcSet="
    hero-bg-mobile.jpg 768w,
    hero-bg-tablet.jpg 1024w,
    hero-bg-desktop.jpg 1920w
  "
  sizes="100vw"
  alt="Hero background"
  loading="eager"
/>
```

## Performance Guidelines

1. **Use WebP** for photos with JPG fallback
2. **Lazy load** images below the fold
3. **Eager load** hero/above-fold images
4. **Width/height attributes** prevent layout shift
5. **Compress SVGs** with svgo
6. **Use CDN** for production assets

## Related Patterns

- Hero Section (for hero image strategy)
- Portfolio Gallery (for gallery images)
