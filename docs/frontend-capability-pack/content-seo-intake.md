# Content & SEO Intake Template

Structured intake for content inventory, SEO metadata, and search optimization strategy.

---

## Purpose

This template captures all content and SEO inputs needed before frontend generation begins. It ensures generated pages have complete metadata, proper structured data, and align with search visibility requirements.

---

## Content Audit Worksheet

### Existing Content Inventory

Before generating new content, inventory what exists:

| Content Type | Source | Status | Action Needed |
|--------------|--------|--------|---------------|
| Homepage copy | [client docs / brand guide / new] | [exists / outdated / missing] | [revise / create / migrate] |
| Service descriptions | [source] | [status] | [action] |
| About/company story | [source] | [status] | [action] |
| Team bios | [source] | [status] | [action] |
| Case studies | [source] | [status] | [action] |
| Blog posts | [source] | [status] | [action] |
| FAQ content | [source] | [status] | [action] |
| Legal pages | [source] | [status] | [action] |

### Content Gap Analysis

| Page | Required Content | Current State | Gap | Priority |
|------|-----------------|---------------|-----|----------|
| Home | Hero headline, features, CTA copy | [exists/partial/missing] | [description] | [H/M/L] |
| About | Company story, team, values | [state] | [gap] | [priority] |
| Services | Service descriptions, benefits | [state] | [gap] | [priority] |
| Pricing | Tier descriptions, feature lists | [state] | [gap] | [priority] |
| Contact | Contact info, form labels | [state] | [gap] | [priority] |

### Content Ownership & Approval

| Content Area | Owner | Reviewer | Approval Status |
|--------------|-------|----------|-----------------|
| [area] | [name/role] | [name/role] | [pending / approved / needs-revision] |

---

## SEO Metadata Template

### Per-Page SEO Template

```yaml
page_seo:
  route: string                    # URL path (e.g., "/pricing")
  
  title:
    template: string               # Pattern: "{Page Name} | {Site Name}"
    max_length: 60                # Google display limit
    value: string                  # Specific title for this page
  
  meta_description:
    max_length: 160               # Google display limit
    value: string                  # 150-160 chars, include primary keyword
  
  canonical_url: string | null    # Override canonical if needed
  
  robots:
    index: boolean                 # Allow indexing
    follow: boolean                # Follow links on page
    noarchive: boolean            # Don't show cached version
  
  open_graph:
    title: string | null          # Override for social (max 60 chars)
    description: string | null     # Override for social (max 200 chars)
    image: string                  # Path to OG image (1200x630 recommended)
    image_alt: string              # Alt text for OG image
  
  twitter_card:
    type: enum                     # summary | summary_large_image
    creator: string | null         # @username
  
  structured_data:
    type: enum | null              # Organization | LocalBusiness | Product | Service | Article | FAQ | Breadcrumb | Person
    schema: object | null          # Full JSON-LD object
```

### Complete Page SEO Example

```yaml
page_seo:
  route: "/pricing"
  
  title:
    template: "{Page Name} | Acme - Project Management for Startups"
    max_length: 60
    value: "Pricing Plans | Acme - Project Management for Startups"
  
  meta_description:
    max_length: 160
    value: "Simple, transparent pricing for teams of all sizes. Start free, upgrade as you grow. No hidden fees, cancel anytime."
  
  canonical_url: null
  
  robots:
    index: true
    follow: true
    noarchive: false
  
  open_graph:
    title: "Acme Pricing - Plans for Every Team"
    description: "Choose the right plan for your team. Free trial available."
    image: "/assets/og-pricing.png"
    image_alt: "Acme pricing tiers comparison"
  
  twitter_card:
    type: summary_large_image
    creator: "@acme_app"
  
  structured_data:
    type: Product
    schema:
      "@context": "https://schema.org"
      "@type": "Product"
      name: "Acme Project Management"
      description: "Project management software for startups"
      offers:
        "@type": "AggregateOffer"
        lowPrice: "0"
        highPrice: "49"
        priceCurrency: "USD"
        offerCount: "3"
```

---

## Site-Wide SEO Settings

### Global SEO Configuration

```yaml
site_seo:
  site_name: string               # Used in title templates
  site_tagline: string            # Used in homepage title
  default_og_image: string        # Fallback OG image
  site_url: string                # Production URL for canonicals
  
  twitter:
    site: string | null           # @siteusername
    creator: string | null        # @creatorusername
  
  robots_txt:
    rules:
      - "User-agent: *"
      - "Allow: /"
      - "Disallow: /admin/"
      - "Disallow: /api/"
      - "Sitemap: https://{site_url}/sitemap.xml"
  
  sitemap:
    include: array                # Routes to include
    exclude: array                # Routes to exclude
    changefreq_default: enum      # always | hourly | daily | weekly | monthly | yearly | never
    priority_default: number      # 0.0 -1.0
  
  analytics:
    google_analytics_id: string | null
    google_tag_manager_id: string | null
    plausible_domain: string | null
    mixpanel_token: string | null
```

---

## Structured Data Requirements

### Common Structured Data Types by Archetype

| Archetype | Recommended Structured Data |
|-----------|----------------------------|
| **Landing Page** | Organization, BreadcrumbList |
| **Service Site** | LocalBusiness, Service, BreadcrumbList |
| **Dashboard** | SoftwareApplication, Organization |
| **Portfolio** | CreativeWork, Person, BreadcrumbList |
| **Lead-Gen** | Organization, FAQ (if FAQ section), BreadcrumbList |

### Organization Schema Template

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Company Name",
  "url": "https://company.com",
  "logo": "https://company.com/logo.png",
  "description": "Brief company description",
  "sameAs": [
    "https://twitter.com/company",
    "https://linkedin.com/company/company",
    "https://github.com/company"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+1-XXX-XXX-XXXX",
    "contactType": "sales",
    "availableLanguage": ["English"]
  }
}
```

### LocalBusiness Schema Template

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Business Name",
  "image": "https://business.com/storefront.jpg",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "City",
    "addressRegion": "ST",
    "postalCode": "12345",
    "addressCountry": "US"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 0.0,
    "longitude": 0.0
  },
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "opens": "09:00",
      "closes": "17:00"
    }
  ],
  "telephone": "+1-XXX-XXX-XXXX",
  "priceRange": "$$"
}
```

### Product Schema Template

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Product Name",
  "description": "Detailed product description",
  "brand": {
    "@type": "Brand",
    "name": "Company Name"
  },
  "offers": {
    "@type": "Offer",
    "url": "https://company.com/product",
    "priceCurrency": "USD",
    "price": "99.00",
    "priceValidUntil": "2026-12-31",
    "availability": "https://schema.org/InStock"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "127"
  }
}
```

### FAQ Schema Template

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is your pricing?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Our pricing starts at..."
      }
    },
    {
      "@type": "Question",
      "name": "How do I get started?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "You can start by..."
      }
    }
  ]
}
```

---

## Keyword Strategy

### Primary Keywords Per Page

| Page | Primary Keyword | Secondary Keywords | Search Intent |
|------|----------------|-------------------|---------------|
| Home | [keyword] | [keyword2, keyword3] | informational / navigational / transactional |
| Services | [keyword] | [keywords] | [intent] |
| Pricing | [keyword] | [keywords] | [intent] |

### Keyword Difficulty & Volume

| Keyword | Monthly Volume | Difficulty | Competition | Priority |
|---------|---------------|------------|-------------|----------|
| [keyword] | [number] | [low/med/high] | [low/med/high] | [H/M/L] |

---

## Content Generation Guidelines

### Headline Writing Rules

1. **Include primary keyword** naturally
2. **Front-load important words** (first 3-5 words)
3. **Match search intent** (question, guide, comparison)
4. **Length**: 50-60 characters for display, up to 70 for schema
5. **Avoid**: All caps, excessive punctuation, clickbait

### Meta Description Rules

1. **Include primary keyword** naturally
2. **Write in active voice**
3. **Include a call-to-action** when appropriate
4. **Length**: 150-160 characters
5. **Match page content** accurately
6. **Avoid**: Duplicate descriptions across pages

### Heading Structure (H1-H6)

| Level | Purpose | Rules |
|-------|---------|-------|
| H1 | Page title | One per page, includes primary keyword |
| H2 | Major sections | 2-6 per page, includes secondary keywords |
| H3 | Sub-sections | Under H2s, organize content |
| H4 | Sub-sub-sections | Rare, for complex content |
| H5-H6 | Detail levels | Use sparingly |

---

## Maps to Pattern Retrieval

Content and SEO data connects to pattern retrieval:

```
knowledge.pattern_search({
  query: "{page_seo.meta_description} OR {page_seo.title}",
  archetype: "{project_type}",
  semantic_role: "hero",
  top_k: 3
})
```

### SEO-Driven Pattern Selection

| SEO Element | Pattern Match | Example |
|-------------|---------------|---------|
| `structured_data.type: FAQ` | `faq-accordion` pattern | FAQ schema needs FAQ accordion section |
| `page_seo.twitter_card.type: summary_large_image` | Hero with strong visual | Large OG image → hero visual focus |
| `meta_description length` | Content density | Short descriptions → concise hero |
| `keyword in title` | Semantic placement | Keyword placement in hero headline |

---

## Intake Checklist

Before proceeding to code generation:

- [ ] All page routes defined with titles and meta descriptions
- [ ] Primary keyword per page identified
- [ ] Structured data type selected per page
- [ ] Site-wide SEO settings configured
- [ ] Analytics integration IDs collected
- [ ] Content gap analysis completed
- [ ] Content ownership and approval chain documented
- [ ] OG images specified or placeholder accepted
- [ ] Robots.txt rules defined
- [ ] Sitemap include/exclude lists created

---

## References

- [Website Brief Schema](website-brief-schema.md) — Full project brief
- [Page Map & CTA Requirements](page-map-cta-requirements.md) — Page structure
- [Prompt Pack](prompt-pack.md) — Using SEO data in prompts
- [Asset Naming Conventions](../patterns/frontend/asset-naming-conventions.md) — File naming