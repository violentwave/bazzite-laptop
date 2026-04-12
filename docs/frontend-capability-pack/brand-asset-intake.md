# Brand & Asset Intake Checklist

Structured intake for brand identity, visual assets, and media requirements.

---

## Purpose

This checklist captures brand guidelines and asset expectations before frontend generation. It ensures generated components reflect brand identity and assets are delivered in proper formats.

---

## Brand Identity Checklist

### Color Palette

#### Primary Colors

| Name | Hex | Usage | Tailwind Token |
|------|-----|-------|----------------|
| Primary | `#xxxxxx` | Buttons, links, emphasis | `--color-primary` |
| Primary Hover | `#xxxxxx` | Primary button hover | `--color-primary-hover` |
| Primary Light | `#xxxxxx` | Backgrounds, highlights | `--color-primary-light` |
| Secondary | `#xxxxxx` | Accent elements | `--color-secondary` |
| Secondary Hover | `#xxxxxx` | Secondary button hover | `--color-secondary-hover` |

#### Neutral Scale

| Shade | Hex | Usage | Tailwind Token |
|-------|-----|-------|----------------|
| 50 | `#xxxxxx` | Light backgrounds | `--color-neutral-50` |
| 100 | `#xxxxxx` | Borders, dividers | `--color-neutral-100` |
| 200 | `#xxxxxx` | Disabled states | `--color-neutral-200` |
| 300 | `#xxxxxx` | Placeholder text | `--color-neutral-300` |
| 400 | `#xxxxxx` | Secondary text | `--color-neutral-400` |
| 500 | `#xxxxxx` | Body text | `--color-neutral-500` |
| 600 | `#xxxxxx` | Headings | `--color-neutral-600` |
| 700 | `#xxxxxx` | Emphasized text | `--color-neutral-700` |
| 800 | `#xxxxxx` | Dark backgrounds | `--color-neutral-800` |
| 900 | `#xxxxxx` | Darkest elements | `--color-neutral-900` |

#### Semantic Colors

| Purpose | Hex | Usage | Tailwind Token |
|---------|-----|-------|----------------|
| Success | `#xxxxxx` | Confirmations, positive states | `--color-success` |
| Warning | `#xxxxxx` | Alerts, caution states | `--color-warning` |
| Error | `#xxxxxx` | Errors, destructive actions | `--color-error` |
| Info | `#xxxxxx` | Information, neutral alerts | `--color-info` |

#### Accent Colors (Optional)

| Name | Hex | Usage | Tailwind Token |
|------|-----|-------|----------------|
| Accent 1 | `#xxxxxx` | Highlight, focus | `--color-accent-1` |
| Accent 2 | `#xxxxxx` | Secondary accent | `--color-accent-2` |
| Gradient Start | `#xxxxxx` | Gradient backgrounds | `--color-gradient-start` |
| Gradient End | `#xxxxxx` | Gradient endpoints | `--color-gradient-end` |

---

### Typography System

#### Font Families

| Type | Font Name | Fallbacks | Usage |
|------|-----------|-----------|-------|
| Heading | `Font Name` | `system-ui, sans-serif` | h1-h6, display text |
| Body | `Font Name` | `system-ui, sans-serif` | Paragraphs, lists |
| Mono | `Font Name` | `monospace` | Code, technical text |

#### Type Scale

| Level | Size | Line Height | Weight | Letter Spacing | Usage |
|-------|------|-------------|--------|----------------|-------|
| Display | `4rem` | `1.1` | `700` | `-0.02em` | Hero headlines |
| H1 | `3rem` | `1.2` | `700` | `-0.01em` | Page titles |
| H2 | `2.25rem` | `1.3` | `600` | `0` | Section headings |
| H3 | `1.5rem` | `1.4` | `600` | `0` | Sub-sections |
| H4 | `1.25rem` | `1.4` | `500` | `0` | Card titles |
| H5 | `1.125rem` | `1.5` | `500` | `0` | Minor headings |
| H6 | `1rem` | `1.5` | `500` | `0` | Labels |
| Body Large | `1.125rem` | `1.6` | `400` | `0` | Lead paragraphs |
| Body | `1rem` | `1.6` | `400` | `0` | Default text |
| Body Small | `0.875rem` | `1.5` | `400` | `0` | Captions, meta |
| Caption | `0.75rem` | `1.4` | `400` | `0` | Small text |

#### Typography Checklist

- [ ] Heading font selected (Google Fonts / Adobe Fonts / Custom)
- [ ] Body font selected
- [ ] Mono font selected (if technical content)
- [ ] Font weights defined (regular, medium, semibold, bold)
- [ ] Line heights set for readability
- [ ] Letter spacing adjusted for headings
- [ ] Font loading strategy defined (swap / optional / fallback)
- [ ] Fallback fonts specified

---

### Voice & Tone

| Attribute | Value | Examples |
|-----------|-------|----------|
| Tone | `professional \| friendly \| playful \| authoritative \| minimal` | Professional: "We deliver results." Friendly: "Let's build something great together." |
| Point of View | `first-person \| second-person \| third-person` | Second-person: "You'll love how easy it is." |
| Content Length | `concise \| moderate \| detailed` | Concise: 3-5 word CTAs, short paragraphs |
| Contractions | `yes \| no` | "You will" vs "You'll" |
| Jargon Level | `minimal \| moderate \| technical` | Avoid unless audience is technical |
| Humor | `none \| subtle \| playful` | Keep professional unless brand permits |

#### Voice Examples

| Scenario | Professional | Friendly | Playful |
|----------|-------------|----------|---------|
| Error message | "An error occurred. Please try again." | "Oops! Something went wrong. Let's try that again." | "Well, that's awkward. Give it another go?" |
| Success message | "Operation completed successfully." | "Great! You're all set." | "Nailed it! You're welcome." |
| CTA | "Submit Request" | "Get Started" | "Let's Do This!" |

---

### Logo System

#### Logo Variants

| Variant | Format | Usage | Max Width |
|---------|--------|-------|-----------|
| Primary | `SVG / PNG` | Light backgrounds | `200px` |
| Inverse | `SVG / PNG` | Dark backgrounds | `200px` |
| Icon Only | `SVG / PNG` | Favicons, small spaces | `48px` |
| Wordmark | `SVG / PNG` | Narrow contexts | `150px` |

#### Logo Usage Rules

1. **Clear space**: Minimum X units around logo
2. **Minimum size**: Never smaller than X pixels wide
3. **Background contrast**: Primary on light, inverse on dark
4. **No distortion**: Always maintain aspect ratio
5. **No effects**: No shadows, outlines, or gradients unless specified
6. **No rotation**: Logo always horizontal

#### Logo Checklist

- [ ] Primary logo file received (SVG preferred)
- [ ] Inverse/dark variant received
- [ ] Icon/mark version received
- [ ] Wordmark version received (if different)
- [ ] Favicon files received (16x16, 32x32, 180x180, 512x512)
- [ ] Logo usage guidelines documented
- [ ] Clear space requirements defined

---

## Asset Intake Checklist

### Imagery Style

| Attribute | Value | Notes |
|-----------|-------|-------|
| Type | `photography \| illustration \| mixed \| abstract \| minimal` | Primary visual style |
| Tone | `bright \| moody \| minimal \| energetic \| corporate \| warm` | Emotional feel |
| Subject Focus | `people \| products \| abstract \| nature \| architecture \| technology` | What to emphasize |
| Cropping | `tight \| medium \| wide` | How subjects are framed |
| Background | `clean \| contextual \| gradient \| texture` | Setting for subjects |
| People | `yes \| no \| illustrated` | Should photos include people? |

#### Imagery Guidelines

- **Photography**: Style reference (e.g., "Apple product photography", "Airbnb lifestyle shots")
- **Illustration**: Style reference (e.g., "Duolingo playful", "Linear technical")
- **Mixed**: When to use photos vs illustrations
- **Treatments**: Overlays, filters, color treatments

#### Imagery Checklist

- [ ] Imagery style defined
- [ ] Reference examples provided (3-5 URLs)
- [ ] Stock photo sources identified or originals received
- [ ] Treatments/filters specified
- [ ] People/inclusion guidelines documented

---

### Icon System

| Attribute | Value | Notes |
|-----------|-------|-------|
| Style | `outlined \| filled \| duo-tone \| custom` | Visual style |
| Set | `heroicons \| lucide \| feather \| phosphor \| custom` | Icon library |
| Sizes | `[16, 20, 24, 32, 48]` | Required sizes |
| Stroke Width | `1 \| 1.5 \| 2` | Line weight |
| Color | `current \| brand \| custom` | Color approach |

#### Icon Usage Rules

1. **Consistent set**: Use one icon family throughout
2. **Size context**: 16-20 for inline, 24 for UI, 32-48 for features
3. **Color**: Inherit from parent (currentColor) or use brand colors
4. **Alignment**: Vertically center with text
5. **Labeling**: Always provide aria-label for icon-only buttons

#### Icon Checklist

- [ ] Icon set selected
- [ ] Required icons identified (navigation, actions, status, social)
- [ ] Custom icons documented (if needed)
- [ ] Sizes defined for each use case
- [ ] Color rules established

---

### Illustration System

| Attribute | Value | Notes |
|-----------|-------|-------|
| Style | `flat \| 3d \| hand-drawn \| abstract \| isometric \| minimal` | Visual style |
| Color Approach | `brand-matching \| complementary \| monochrome \` duotone` | Color palette |
| Complexity | `simple \| moderate \| detailed` | Level of detail |
| Animation | `static \| micro-interactions \| full-motion` | Movement level |

#### Illustration Checklist

- [ ] Illustration style defined
- [ ] Reference examples provided
- [ ] Illustration files received or source identified
- [ ] Color approach documented
- [ ] Animation requirements specified

---

## Asset Delivery Requirements

### Image Formats

| Asset Type | Preferred | Acceptable | Max Size |
|------------|-----------|------------|----------|
| Hero images | WebP/AVIF | PNG/JPG | 200 KB |
| Content images | WebP/AVIF | PNG/JPG | 100 KB |
| Thumbnails | WebP | PNG/JPG | 30 KB |
| Icons | SVG | PNG | 10 KB |
| Illustrations | SVG | WebP/PNG | 150 KB |
| Logos | SVG | PNG | 50 KB |

### Naming Conventions

Follow `docs/patterns/frontend/asset-naming-conventions.md`:

```
{type}-{descriptor}-{variant}-{size}.{ext}
```

Examples:
- `hero-homepage-desktop.webp`
- `icon-arrow-right-24.svg`
- `logo-primary-horizontal.svg`
- `illustration-onboarding-step1.svg`
- `testimonial-avatar-sarah.png`

### File Structure

```
/assets
  /images
    /heroes
    /content
    /backgrounds
  /icons
    /ui
    /social
    /status
  /illustrations
  /logos
  /favicons
```

---

## Maps to Pattern Retrieval

Brand and asset data connects to pattern retrieval:

```
knowledge.pattern_search({
  query: "hero section {imagery_style.type} {brand_rules.colors.primary}",
  archetype: "{project_type}",
  pattern_scope: "media",
  top_k: 3
})
```

### Brand-Driven Pattern Selection

| Brand Element | Pattern Match | Example |
|---------------|---------------|---------|
| `imagery_style.type: illustration` | `svg-illustration-system` pattern | Illustrated hero background |
| `typography.heading_font: Inter` | Tailwind Inter font config | `font-family: 'Inter', sans-serif` |
| `colors.primary: #3B82F6` | Button/CTA patterns | Primary blue CTAs |
| `icon_system.style: outlined` | `motion-hover-depth` pattern | Outlined icon hover effects |
| `illustrations.style: 3d` | `hero-split-media` pattern | 3D illustration in hero |

---

## Brand Checklist Summary

### Before Code Generation

- [ ] Color palette defined (primary, secondary, neutral, semantic)
- [ ] Typography system specified (fonts, sizes, weights)
- [ ] Voice and tone documented
- [ ] Logo variants received (primary, inverse, icon, favicon)
- [ ] Logo usage rules understood
- [ ] Imagery style selected (photography, illustration, mixed)
- [ ] Icon system chosen (set, style, sizes)
- [ ] Illustration style defined (if applicable)
- [ ] Asset naming convention confirmed
- [ ] File size limits established
- [ ] Asset delivery schedule confirmed

### During Generation

- [ ] All colors use design tokens
- [ ] Typography follows type scale
- [ ] Icons from specified set only
- [ ] Images follow style guidelines
- [ ] Illustrations match defined style
- [ ] Logo usage rules respected

### After Generation

- [ ] All brand elements present and correct
- [ ] No off-brand colors or fonts
- [ ] Logo clear space respected
- [ ] Imagery matches style guide
- [ ] Icons from correct set
- [ ] Asset naming convention followed

---

## References

- [Website Brief Schema](website-brief-schema.md) — Full project brief
- [Asset Naming Conventions](../patterns/frontend/asset-naming-conventions.md) — File naming standards
- [SVG Illustration System](../patterns/frontend/svg-illustration-system.md) — SVG pattern
- [Hero Split Media](../patterns/frontend/hero-split-media.md) — Media in hero
- [Motion Guidance](motion-guidance.md) — Animation standards