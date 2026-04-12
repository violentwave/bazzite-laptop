# Page Map & CTA/Form Requirements

Standardized page structure, CTA specifications, and form requirements for frontend generation.

---

## Purpose

This document defines how to map pages to sections, specify CTAs, and document form requirements before code generation. It ensures every page has a complete structure and all conversion actions are documented.

---

## Page Map Template

### Page Map Overview

A page map connects each route to its sections, CTAs, and forms. This enables pattern retrieval by archetype and semantic role.

```yaml
page_map:
  version: "1.0.0"
  
  site:
    name: string
    base_url: string
    default_layout: enum                # root | nested | minimal

  pages:
    - route: string                      # URL path
      title: string                      # Page title
      page_type: enum                    # home | landing | content | pricing | contact | dashboard | portfolio-item | form
      archetype: enum                    # landing-page | service-site | dashboard | portfolio | lead-gen
      layout: enum                       # full-width | contained | sidebar | split
      navigation:
        main_nav: boolean               # Include in main navigation
        footer_nav: boolean              # Include in footer navigation
        mobile_nav: boolean              # Include in mobile navigation
        label: string                    # Navigation label (if different from page title)
      
      sections:
        - id: string                     # Unique section identifier
          pattern_id: string             # Reference to pattern corpus
          semantic_role: enum           # hero | cta | navigation | pricing | testimonial | feature | illustration | background | proof | visual-effect | form | footer
          position: number               # Order on page (1-N)
          visibility: enum              # all | desktop-only | mobile-only
          content:                       # Content overrides
            headline: string | null
            subheadline: string | null
            body: string | null
          configuration:                 # Pattern-specific config
            variant: string | null
            theme: enum | null           # light | dark | brand | neutral
      
      ctas: array                         # CTA references (see CTA Spec)
      forms: array                        # Form references (see Form Spec)
```

---

## Page Map by Archetype

### Landing Page Page Map

```yaml
page_map:
  pages:
    - route: "/"
      title: "Home"
      page_type: landing
      archetype: landing-page
      layout: full-width
      navigation:
        main_nav: true
        footer_nav: true
        mobile_nav: true
        label: "Home"
      
      sections:
        - id: hero-1
          pattern_id: hero-proof-driven
          semantic_role: hero
          position: 1
          visibility: all
          content:
            headline: "Ship Faster with Acme"
            subheadline: "Project management built for startups"
          
        - id: features-1
          pattern_id: feature-grid
          semantic_role: feature
          position: 2
          visibility: all
          configuration:
            variant: icons-left
          
        - id: social-proof-1
          pattern_id: testimonials-section
          semantic_role: testimonial
          position: 3
          visibility: all
          configuration:
            theme: neutral
          
        - id: pricing-1
          pattern_id: pricing-table
          semantic_role: pricing
          position: 4
          visibility: all
          configuration:
            variant: highlighted-recommended
          
        - id: cta-1
          pattern_id: cta-band
          semantic_role: cta
          position: 5
          visibility: all
      
      ctas: ["hero-cta-primary", "pricing-cta", "footer-cta"]
      forms: []
```

### Service Site Page Map

```yaml
page_map:
  pages:
    - route: "/services"
      title: "Services"
      page_type: content
      archetype: service-site
      layout: contained
      
      sections:
        - id: hero-1
          pattern_id: hero-split-media
          semantic_role: hero
          position: 1
          
        - id: services-1
          pattern_id: feature-grid
          semantic_role: feature
          position: 2
          configuration:
            variant: cards-alternating
          
        - id: process-1
          pattern_id: feature-grid
          semantic_role: feature
          position: 3
          configuration:
            variant: numbered
          
        - id: cta-1
          pattern_id: cta-inline-form
          semantic_role: cta
          position: 4
      
      ctas: ["hero-cta", "cta-contact"]
      forms: ["contact-quote"]
    
    - route: "/contact"
      title: "Contact"
      page_type: contact
      archetype: service-site
      layout: contained
      
      sections:
        - id: contact-1
          pattern_id: contact-form
          semantic_role: form
          position: 1
      
      ctas: ["submit-contact"]
      forms: ["contact-main"]
```

### Dashboard Page Map

```yaml
page_map:
  pages:
    - route: "/dashboard"
      title: "Dashboard"
      page_type: dashboard
      archetype: dashboard
      layout: sidebar
      
      sections:
        - id: metrics-1
          pattern_id: dashboard-kpi-strip
          semantic_role: kpi
          position: 1
          
        - id: charts-1
          pattern_id: dashboard-chart-panel
          semantic_role: data-viz
          position: 2
          
        - id: activity-1
          pattern_id: dashboard-activity-feed
          semantic_role: activity
          position: 3
      
      ctas: ["export-data", "create-new"]
      forms: []
```

### Portfolio Page Map

```yaml
page_map:
  pages:
    - route: "/work"
      title: "Portfolio"
      page_type: content
      archetype: portfolio
      layout: contained
      
      sections:
        - id: intro-1
          pattern_id: hero-minimal
          semantic_role: hero
          position: 1
          
        - id: gallery-1
          pattern_id: portfolio-gallery
          semantic_role: gallery
          position: 2
          configuration:
            variant: masonry
      
      ctas: ["view-project"]
      forms: []
    
    - route: "/work/{slug}"
      title: "{Project Name}"
      page_type: portfolio-item
      archetype: portfolio
      layout: full-width
      
      sections:
        - id: hero-1
          pattern_id: hero-full-media
          semantic_role: hero
          position: 1
          
        - id: details-1
          pattern_id: project-details
          semantic_role: content
          position: 2
          
        - id: next-1
          pattern_id: project-nav
          semantic_role: navigation
          position: 3
      
      ctas: ["view-live", "view-code"]
      forms: []
```

### Lead-Gen Page Map

```yaml
page_map:
  pages:
    - route: "/"
      title: "Get Started"
      page_type: landing
      archetype: lead-gen
      layout: split
      
      sections:
        - id: hero-1
          pattern_id: hero-split-form
          semantic_role: hero
          position: 1
          
        - id: benefits-1
          pattern_id: feature-grid
          semantic_role: feature
          position: 2
          
        - id: faq-1
          pattern_id: faq-accordion
          semantic_role: content
          position: 3
          
        - id: final-cta-1
          pattern_id: cta-band
          semantic_role: cta
          position: 4
      
      ctas: ["start-trial", "contact-sales"]
      forms: ["lead-capture"]
```

---

## CTA Specification Template

### CTA Definition Schema

```yaml
cta_specification:
  id: string                            # Unique CTA identifier
  text: string                          # Button/link text
  action_type: enum                     # link | form-submit | modal | scroll | external | download
  
  target: string                        # URL, form ID, or modal ID
  variant: enum                         # primary | secondary | tertiary | ghost | outline | link
  size: enum                            # sm | md | lg | xl
  
  icon:                                 # Optional icon
    name: string | null                 # Icon name from icon set
    position: enum                       # left | right
    
  analytics:                            # Tracking
    event_name: string                   # e.g., "cta_click", "trial_signup"
    event_category: string               # e.g., "conversion", "navigation"
    event_label: string | null           # e.g., "hero_cta", "footer_cta"
  
  a11y:                                 # Accessibility
    aria_label: string | null            # Override button text for screen readers
    aria_describedby: string | null      # Reference to description element
    
  conversion:                           # Conversion tracking
    goal: string                         # e.g., "trial_signup", "contact_form"
    funnel_step: number                  # Position in funnel
    priority: enum                       # primary | secondary | tertiary
```

### CTA Specification Examples

```yaml
cta_specifications:
  - id: hero-cta-primary
    text: "Start Free Trial"
    action_type: link
    target: "/signup"
    variant: primary
    size: lg
    icon:
      name: arrow-right
      position: right
    analytics:
      event_name: trial_start_click
      event_category: conversion
      event_label: hero_cta
    a11y: {}
    conversion:
      goal: trial_signup
      funnel_step: 1
      priority: primary

  - id: pricing-cta
    text: "Get Started"
    action_type: link
    target: "/signup?plan={plan_id}"
    variant: primary
    size: md
    analytics:
      event_name: pricing_select
      event_category: conversion
      event_label: pricing_card
    conversion:
      goal: trial_signup
      funnel_step: 1
      priority: primary

  - id: footer-cta
    text: "Contact Sales"
    action_type: link
    target: "/contact"
    variant: secondary
    size: md
    analytics:
      event_name: contact_sales_click
      event_category: navigation
      event_label: footer_cta
    conversion:
      goal: contact_form
      funnel_step: 1
      priority: secondary

  - id: submit-contact
    text: "Send Message"
    action_type: form-submit
    target: contact-main
    variant: primary
    size: md
    analytics:
      event_name: contact_form_submit
      event_category: conversion
      event_label: contact_page
    conversion:
      goal: contact_form
      funnel_step: 2
      priority: primary
```

### CTA Variant Guidelines

| Variant | Use Case | Example |
|---------|----------|---------|
| primary | Main conversion action | "Start Free Trial", "Sign Up" |
| secondary | Alternative action | "Learn More", "See Pricing" |
| tertiary | Tertiary action | "View Docs", "Watch Demo" |
| ghost | Low-emphasis link | "Skip for now", "Maybe later" |
| outline | Secondary action with emphasis | "Compare Plans" |
| link | Inline text link | "Read more about this feature" |

---

## Form Requirements Template

### Form Definition Schema

```yaml
form_specification:
  id: string                            # Unique form identifier
  page_route: string                    # Where the form appears
  
  type: enum                            # contact | signup | newsletter | lead-capture | quote-request | login | feedback | support
  
  fields:
    - name: string                      # Field name (programming identifier)
      label: string                     # User-visible label
      type: enum                        # text | email | phone | number | select | radio | checkbox | textarea | file | hidden | password
      placeholder: string | null
      required: boolean
      validation:
        type: enum | null               # email | phone | url | min-length | max-length | pattern | file-size | file-type
        value: string | number | null   # Validation value (e.g., min-length: 3)
        message: string                 # Error message for validation failure
      
      options: array | null              # For select/radio/checkbox: [{label, value}]
      default_value: string | null
      autocomplete: string | null        # Autocomplete attribute value
      aria_describedby: string | null    # Reference to help text
  
  submit:
    text: string                         # Submit button text
    loading_text: string                 # Text while submitting
    success_text: string                 # Success message
    error_text: string                   # Generic error message
  
  endpoint:
    url: string | null                   # API endpoint (null = client-side only)
    method: enum                          # POST | GET | PUT
    headers: object | null               # Additional headers
  
  analytics:
    event_name: string                    # Form submission event
    event_category: string
    success_event: string                 # Success event name
    error_event: string                   # Error event name
  
  success:
    action: enum                          # message | redirect | modal | download
    message: string | null                # Success message display
    redirect_url: string | null           # Redirect on success
    modal_id: string | null               # Modal to show
  
  error_handling:
    inline: boolean                       # Show errors inline per field
    summary: boolean                      # Show error summary at top
    retry_button: boolean                  # Show retry button
  
  accessibility:
    announce_errors: boolean               # Screen reader error announcement
    focus_first_error: boolean            # Focus first error field
    submit_on_enter: boolean              # Allow Enter key submission
```

### Form Specification Examples

```yaml
form_specifications:
  - id: contact-main
    page_route: "/contact"
    type: contact
    
    fields:
      - name: name
        label: "Your Name"
        type: text
        placeholder: "John Smith"
        required: true
        validation:
          type: min-length
          value: 2
          message: "Name must be at least 2 characters"
        autocomplete: name
      
      - name: email
        label: "Email Address"
        type: email
        placeholder: "john@example.com"
        required: true
        validation:
          type: email
          message: "Please enter a valid email"
        autocomplete: email
      
      - name: phone
        label: "Phone Number"
        type: phone
        placeholder: "+1 (555) 123-4567"
        required: false
        validation:
          type: phone
          message: "Please enter a valid phone number"
        autocomplete: tel
      
      - name: message
        label: "Message"
        type: textarea
        placeholder: "Tell us about your project..."
        required: true
        validation:
          type: min-length
          value: 10
          message: "Message must be at least 10 characters"
      
      - name: consent
        label: "I agree to receive communications"
        type: checkbox
        required: true
        validation:
          type: pattern
          message: "Consent is required"
    
    submit:
      text: "Send Message"
      loading_text: "Sending..."
      success_text: "Message sent! We'll get back to you within 24 hours."
      error_text: "Something went wrong. Please try again."
    
    endpoint:
      url: "/api/contact"
      method: POST
    
    analytics:
      event_name: contact_form_submit
      event_category: conversion
      success_event: contact_form_success
      error_event: contact_form_error
    
    success:
      action: message
    
    error_handling:
      inline: true
      summary: true
      retry_button: true
    
    accessibility:
      announce_errors: true
      focus_first_error: true
      submit_on_enter: true

  - id: lead-capture
    page_route: "/"
    type: lead-capture
    
    fields:
      - name: email
        label: "Work Email"
        type: email
        placeholder: "you@company.com"
        required: true
        validation:
          type: email
          message: "Please enter a valid work email"
        autocomplete: email
      
      - name: company
        label: "Company Name"
        type: text
        placeholder: "Acme Inc."
        required: true
        autocomplete: organization
    
    submit:
      text: "Get Started Free"
      loading_text: "Creating account..."
      success_text: "Check your email for next steps!"
      error_text: "Email already registered or invalid."
    
    endpoint:
      url: "/api/leads"
      method: POST
    
    analytics:
      event_name: lead_capture_submit
      event_category: conversion
      success_event: lead_capture_success
    
    success:
      action: redirect
      redirect_url: "/welcome"
    
    error_handling:
      inline: true
      summary: false
    
    accessibility:
      announce_errors: true
      submit_on_enter: true
```

---

## Maps to Pattern Retrieval

Page maps connect to pattern retrieval for each section:

```
knowledge.pattern_search({
  query: "{page.sections[].semantic_role} {archetype}",
  archetype: "{page.archetype}",
  pattern_scope: "section",
  semantic_role: "{page.sections[].semantic_role}",
  top_k: 3
})
```

### Page Module → Pattern Match Table

| Page Module | Semantic Role | Recommended Patterns |
|-------------|---------------|---------------------|
| Hero section | hero | `hero-proof-driven`, `hero-split-media`, `hero-minimal` |
| Features | feature | `feature-grid`, `feature-alternating` |
| Testimonials | testimonial | `testimonials-section`, `testimonials-carousel` |
| Pricing | pricing | `pricing-table`, `pricing-comparison` |
| FAQ | content | `faq-accordion` |
| CTA | cta | `cta-band`, `cta-inline-form`, `cta-proof-stack` |
| Contact | form | `contact-form` |
| Footer | footer | `footer-component` |

---

## Validation Checklist

### Page Map Validation

- [ ] All routes defined with correct page_type
- [ ] Each page has sections array with positions
- [ ] Each section has semantic_role matching pattern
- [ ] Navigation labels defined for all main pages
- [ ] Layout specified for each page
- [ ] Archetype matches site type

### CTA Validation

- [ ] Every CTA has unique id
- [ ] Action types defined correctly
- [ ] Targets resolve to URLs or form IDs
- [ ] Variants follow convention (primary for main actions)
- [ ] Analytics events named consistently
- [ ] Conversion goals mapped to business objectives

### Form Validation

- [ ] All fields have valid types
- [ ] Required fields marked
- [ ] Validation messages user-friendly
- [ ] Success/error states defined
- [ ] Endpoint URL and method specified
- [ ] Accessibility options configured
- [ ] Analytics events defined

---

## References

- [Website Brief Schema](website-brief-schema.md) — Full project brief
- [Content & SEO Intake](content-seo-intake.md) — SEO metadata
- [Brand & Asset Intake](brand-asset-intake.md) — Visual assets
- [Prompt Pack](prompt-pack.md) — Using page maps in prompts
- [Site Archetypes](site-archetypes/) — Archetype-specific guidance