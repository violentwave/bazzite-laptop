# Website Brief Schema

Canonical schema for structured project briefs that feed frontend generation.

---

## Purpose

This schema defines a structured intake format for all website generation projects. It ensures OpenCode agents have complete project context before beginning code generation, enabling retrieval-first pattern matching and consistent output quality.

---

## Schema Overview

The brief schema consists of eight sections:

| Section | Purpose | Required |
|---------|---------|----------|
| Project Metadata | Identity, goals, success metrics | Yes |
| Target Audience | Personas, demographics, needs | Yes |
| Sitemap | Pages, routes, navigation | Yes |
| Page Modules | Patterns per page/section | Yes |
| CTA Specifications | Conversion actions per page | Conditional |
| Form Requirements | Data collection needs | Conditional |
| SEO Inputs | Metadata, structured data | Yes |
| Brand Rules | Visual identity constraints | Yes |
| Asset Expectations | Imagery, icons, media | Yes |
| Technical Constraints | Performance, accessibility, browsers | Yes |

---

## YAML Schema

```yaml
website_brief:
  version: "1.0.0"
  created: "YYYY-MM-DD"
  last_updated: "YYYY-MM-DD"

  project_metadata:
    name: string                    # Project name
    description: string             # One-line description
    client: string | null          # Client name (if different)
    project_type: enum             # landing-page | service-site | dashboard | portfolio | lead-gen
    primary_goal: string           # Main conversion/business goal
    success_metrics:                # How success is measured
      - metric: string
        target: string | number
    timeline:
      start_date: date | null
      launch_date: date | null
      milestones: array | null

  target_audience:
    primary_persona:
      name: string                  # Persona name
      demographics: string          # Age, location, profession
      goals: array                  # What they want to achieve
      pain_points: array           # Problems they face
      technical_comfort: enum       # low | medium | high
    secondary_personas: array | null
    accessibility_needs:
      wcag_level: enum              # A | AA | AAA
      screen_reader_support: boolean
      keyboard_navigation: boolean
      reduced_motion: boolean

  sitemap:
    pages:
      - route: string               # URL path (e.g., "/", "/pricing")
        title: string                # Page title
        page_type: enum             # home | landing | content | pricing | contact | dashboard | portfolio-item | form
        navigation_label: string    # Menu text
        parent_route: string | null # For nested pages
        is_primary: boolean         # Main navigation item
    navigation_structure:
      main_nav: array               # List of route strings
      footer_nav: array             # List of route strings
      mobile_nav: array | null      # Different mobile order

  page_modules:
    - route: string                 # Matches sitemap route
      sections:
        - pattern_id: string        # References pattern corpus
          archetype: enum           # landing-page | service-site | dashboard | portfolio | lead-gen
          pattern_scope: enum       # section | component | layout | motion | asset | token | workflow | media | effect
          semantic_role: enum       # hero | cta | navigation | pricing | testimonial | feature | illustration | background | proof | visual-effect
          customization:
            content_overrides: object | null
            variant: string | null
          position: number           # Section order on page

  cta_specifications:
    - page_route: string
      ctas:
        - id: string                # Unique CTA identifier
          text: string              # Button/link text
          action_type: enum         # link | form-submit | modal | scroll | external
          target: string            # URL or form ID
          variant: enum              # primary | secondary | tertiary | ghost
          priority: number          # 1 = primary, 2 = secondary
          conversion_goal: string   # What conversions to track

  form_requirements:
    - form_id: string
      page_route: string
      form_type: enum               # contact | signup | newsletter | lead-capture | quote-request | login
      fields:
        - name: string
          type: enum                # text | email | phone | select | radio | checkbox | textarea | file
          label: string
          placeholder: string | null
          required: boolean
          validation: string | null # Regex or rule description
      submit_endpoint: string | null
      success_message: string
      error_handling: string        # Description of error UX
      analytics_event: string | null

  seo_inputs:
    page_metadata:
      - route: string
        title_template: string      # {site_name} | {page_title}
        title: string               # Specific page title
        meta_description: string    # 150-160 chars
        canonical_url: string | null
        og_image: string | null     # Path to OG image
        og_title: string | null     # Override for social
        og_description: string | null
        structured_data_type: enum | null  # Article | Product | Service | LocalBusiness | FAQ | Breadcrumb
        structured_data: object | null     # JSON-LD object
    site_wide:
      site_name: string
      default_og_image: string
      twitter_card_type: enum       # summary | summary_large_image
      robots_txt_rules: array | null

  brand_rules:
    colors:
      primary: string               # Hex value
      secondary: string
      neutral:                      # Full neutral scale
        50: string
        100: string
        200: string
        300: string
        400: string
        500: string
        600: string
        700: string
        800: string
        900: string
      accent: string | null
      semantic:
        success: string
        warning: string
        error: string
        info: string
    typography:
      heading_font: string
      body_font: string
      mono_font: string | null
      heading_scale: array         # [h1-size, h2-size, ...]
      body_size: string             # Base body size
    voice:
      tone: enum                    # professional | friendly | playful | authoritative | minimal
      point_of_view: enum           # first-person | second-person | third-person
      content_length: enum          # concise | moderate | detailed
    logo:
      primary: string               # Path to primary logo
      secondary: string | null      # Alternative logo
      icon: string | null           # Icon/mark only
      usage_rules: string           # When to use which

  asset_expectations:
    imagery_style:
      type: enum                    # photography | illustration | mixed | abstract
      tone: string                   # bright | moody | minimal | energetic
      subject_focus: array          # people | products | abstract | nature | architecture
      cropping: enum                 # tight | medium | wide
    icon_system:
      style: enum                    # outlined | filled | duo-tone | custom
      set: string | null            # heroicons | lucide | feather | custom
      sizes: array                   # [16, 20, 24, 32, 48]
    illustrations:
      style: enum | null            # flat | 3d | hand-drawn | abstract | null
      color_approach: enum          # brand-matching | complementary | monochrome
    naming_convention: string       # Reference asset-naming-conventions.md pattern
    delivery_formats:
      images: array                  # [webp, avif, png, jpg]
      icons: array                   # [svg, png]
      max_file_sizes:
        hero_image_kb: number
        icon_kb: number
        illustration_kb: number

  technical_constraints:
    accessibility:
      wcag_level: enum               # A | AA | AAA
      focus_visible: boolean
      screen_reader_announcements: boolean
      reduced_motion_respect: boolean
      color_contrast_minimum: enum  # AA | AAA
    performance:
      lighthouse_target: number      # Score out of 100
      max_bundle_size_kb: number
      image_lazy_loading: boolean
      font_display: enum            # swap | optional | fallback
    browser_support:
      modern: array                  # chrome, firefox, safari, edge
      legacy: array | null           # IE11, old Safari
      mobile: array                  # ios-safari, android-chrome
    framework_constraints:
      react_version: string | null
      tailwind_version: string | null
      typescript_required: boolean
      testing_required: boolean
```

---

## JSON Schema Alternative

For projects preferring JSON:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://bazzite.ai/schemas/website-brief-v1.json",
  "title": "Website Brief Schema",
  "type": "object",
  "required": ["project_metadata", "target_audience", "sitemap", "page_modules", "seo_inputs", "brand_rules", "asset_expectations", "technical_constraints"],
  "properties": {
    "website_brief": {
      "type": "object",
      "properties": {
        "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
        "created": { "type": "string", "format": "date" },
        "last_updated": { "type": "string", "format": "date" },
        "project_metadata": { "$ref": "#/$defs/project_metadata" },
        "target_audience": { "$ref": "#/$defs/target_audience" },
        "sitemap": { "$ref": "#/$defs/sitemap" },
        "page_modules": { "$ref": "#/$defs/page_modules" },
        "cta_specifications": { "$ref": "#/$defs/cta_specifications" },
        "form_requirements": { "$ref": "#/$defs/form_requirements" },
        "seo_inputs": { "$ref": "#/$defs/seo_inputs" },
        "brand_rules": { "$ref": "#/$defs/brand_rules" },
        "asset_expectations": { "$ref": "#/$defs/asset_expectations" },
        "technical_constraints": { "$ref": "#/$defs/technical_constraints" }
      }
    }
  }
}
```

---

## Brief-First Workflow Integration

This schema integrates with the retrieval-first workflow as follows:

### Step 0: Brief Completion (NEW)

Before retrieving patterns, thebrief must be populated:

1. **Gather** project requirements via intake form or client interview
2. **Populate** schema fields with gathered data
3. **Validate** required fields are complete
4. **Reference** pattern corpus via `page_modules[].pattern_id` and archetype filters

### Step 1: Retrieve Proven Patterns

```markdown
Use `knowledge.pattern_search` with brief data:

- archetype: {project_metadata.project_type}
- semantic_role: {page_modules[].sections[].semantic_role}
- pattern_scope: {page_modules[].sections[].pattern_scope}
```

### Step 2: Retrieve Similar Workflows

```markdown
Use `knowledge.task_patterns` with:

- query: "{project_type} generation with {form_requirements[].form_type} form"
- top_k: 3
```

---

## Field Mapping to Pattern Corpus

| Brief Field | Pattern Metadata | Search Example |
|-------------|------------------|----------------|
| `page_modules[].sections[].pattern_id` | Direct reference | "hero-proof-driven" |
| `project_metadata.project_type` | `archetype` filter | "landing-page" |
| `page_modules[].sections[].semantic_role` | `semantic_role` filter | "hero", "cta" |
| `page_modules[].sections[].pattern_scope` | `pattern_scope` filter | "section", "component" |
| `brand_rules.colors.primary` | Design tokens | Token file generation |
| `asset_expectations.imagery_style` | `media` scope patterns | SVG background, hero split |

---

## Minimal Brief Example

```yaml
website_brief:
  version: "1.0.0"
  created: "2026-04-12"

  project_metadata:
    name: "Acme SaaS Landing"
    description: "Conversion-focused landing page for Acme project management tool"
    project_type: landing-page
    primary_goal: "Drive trial signups"
    success_metrics:
      - metric: trial_signups
        target: "500/month"

  target_audience:
    primary_persona:
      name: "Startup Founder"
      demographics: "25-45, urban, tech-savvy"
      goals: ["Ship faster", "Scale team efficiently"]
      pain_points: ["Manual tracking", "Communication silos"]
      technical_comfort: high
    accessibility_needs:
      wcag_level: AA
      screen_reader_support: true
      keyboard_navigation: true
      reduced_motion: true

  sitemap:
    pages:
      - route: "/"
        title: "Home"
        page_type: landing
        navigation_label: "Home"
        is_primary: true
      - route: "/pricing"
        title: "Pricing"
        page_type: pricing
        navigation_label: "Pricing"
        is_primary: true
      - route: "/contact"
        title: "Contact"
        page_type: contact
        navigation_label: "Contact"
        is_primary: true

  page_modules:
    - route: "/"
      sections:
        - pattern_id: hero-proof-driven
          archetype: landing-page
          pattern_scope: section
          semantic_role: hero
          position: 1
        - pattern_id: feature-grid
          archetype: landing-page
          pattern_scope: section
          semantic_role: feature
          position: 2
        - pattern_id: testimonials-section
          archetype: landing-page
          pattern_scope: section
          semantic_role: testimonial
          position: 3
        - pattern_id: cta-band
          archetype: landing-page
          pattern_scope: section
          semantic_role: cta
          position: 4

  cta_specifications:
    - page_route: "/"
      ctas:
        - id: hero-cta
          text: "Start Free Trial"
          action_type: link
          target: "/signup"
          variant: primary
          priority: 1
          conversion_goal: trial_signup

  seo_inputs:
    page_metadata:
      - route: "/"
        title: "Acme - Project Management for Startups"
        meta_description: "Ship faster with Acme's intuitive project management. Free trial, no credit card required."
        structured_data_type: Organization

  brand_rules:
    colors:
      primary: "#3B82F6"
      secondary: "#1E40AF"
      neutral: { 50: "#F9FAFB", 500: "#6B7280", 900: "#111827" }
    typography:
      heading_font: "Inter"
      body_font: "Inter"
    voice:
      tone: friendly
      point_of_view: second-person
      content_length: concise

  asset_expectations:
    imagery_style:
      type: illustration
      tone: bright
      subject_focus: [abstract]
      cropping: medium
    icon_system:
      style: outlined
      set: heroicons
      sizes: [20, 24]

  technical_constraints:
    accessibility:
      wcag_level: AA
      focus_visible: true
      reduced_motion_respect: true
    performance:
      lighthouse_target: 95
      max_bundle_size_kb: 200
```

---

## References

- [Prompt Pack](prompt-pack.md) — How to use brief data in prompts
- [Site Archetypes](site-archetypes/) — Archetype-specific guidance
- [Validation Flow](validation-flow.md) — Post-generation checklist
- [Asset Naming Conventions](../patterns/frontend/asset-naming-conventions.md) — File naming standards