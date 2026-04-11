# Landing Pages

Prompts and scaffold guidance for single-page conversion sites.

---

## Purpose

Landing pages focus on **single-action conversion**: sign up, download, purchase, or contact. They minimize navigation and maximize persuasion.

---

## Standard Sections

### 1. Hero

**Content:**
- Headline (clear value proposition)
- Subheadline (supporting explanation)
- Primary CTA button
- Optional: secondary CTA (watch demo, learn more)
- Optional: hero image/video or social proof

**Prompt Template:**

```markdown
TASK: Create a high-converting hero section for a SaaS landing page.

CONTEXT:
- Target audience: [describe]
- Primary value prop: [one sentence]
- CTA action: [sign up, download, etc.]
- Visual style: [modern/corporate/playful]

FORMAT:
- Hero.tsx component
- Props interface for customization
- Responsive: stacked mobile, side-by-side desktop

STYLE:
- Tailwind v4, semantic HTML
- Large typography (text-4xl to text-6xl)
- High contrast CTA button

CONSTRAINTS:
- Single primary CTA (no competing actions)
- Headline ≤ 10 words
- Subheadline ≤ 25 words
- WCAG AA contrast on all text
- Load hero image lazily if below fold
```

### 2. Social Proof

**Content:**
- Logos of trusted companies
- Testimonial quotes
- User/customer counts
- Star ratings

**Prompt:**

```markdown
TASK: Build a social proof section with logo bar and testimonial.

CONTEXT:
- Number of customers: [count]
- Notable clients: [company names]
- Quote: [testimonial text]
- Author: [name, title, company]

FORMAT:
- SocialProof.tsx
- LogoBar subcomponent
- TestimonialCard subcomponent

CONSTRAINTS:
- Grayscale logos, color on hover
- Quote in <blockquote> with <cite>
- Author photo with alt text
- Responsive: 2-3 logos per row mobile
```

### 3. Features/Benefits

**Content:**
- 3-6 key features
- Icon + title + description per feature
- Visual alternation (image left/right)

**Prompt:**

```markdown
TASK: Create a features section with 3 benefit cards.

CONTEXT:
- Features: [list 3 with descriptions]
- Icons: [icon names or descriptions]
- Style: [cards/list/alternating]

FORMAT:
- FeaturesSection.tsx
- FeatureCard.tsx

CONSTRAINTS:
- Each feature ≤ 15 words
- Icons have aria-hidden
- Cards equal height
- Grid layout: 1 col mobile, 3 col desktop
```

### 4. How It Works

**Content:**
- 3-4 step process
- Visual timeline or numbered steps
- Brief description per step

**Prompt:**

```markdown
TASK: Build a "how it works" section with numbered steps.

CONTEXT:
- Steps: [3-4 steps with descriptions]
- Visual: [timeline/numbered cards]

FORMAT:
- HowItWorks.tsx
- Step.tsx subcomponent

CONSTRAINTS:
- Step titles ≤ 5 words
- Numbered with visual indicator
- Connected timeline on desktop
- Stacked on mobile
```

### 5. Pricing (if applicable)

**Content:**
- 2-3 pricing tiers
- Feature comparison
- Recommended tier highlighted

See [lead-gen.md](lead-gen.md) for detailed pricing page guidance.

### 6. FAQ

**Content:**
- 4-6 common questions
- Expandable answers

**Prompt:**

```markdown
TASK: Create an FAQ accordion section.

CONTEXT:
- Questions: [list 4-6]
- Style: [accordion/expandable cards]

FORMAT:
- FAQ.tsx
- AccordionItem.tsx

CONSTRAINTS:
- Keyboard accessible (Enter/Space to toggle)
- aria-expanded on trigger
- aria-controls linking to content
- Only one open at a time (optional)
```

### 7. Final CTA

**Content:**
- Reinforced value proposition
- Primary CTA repeated
- Minimal distractions

---

## Layout Patterns

### Single-Column Flow

```
[Hero]
  ↓
[Social Proof]
  ↓
[Features]
  ↓
[How It Works]
  ↓
[Pricing]
  ↓
[FAQ]
  ↓
[CTA]
  ↓
[Footer]
```

### Anatomy Diagram

```
┌─────────────────────────────────────┐
│  Header (logo + nav + CTA)          │
├─────────────────────────────────────┤
│                                     │
│  HERO                               │
│  Headline                           │
│  Subheadline                        │
│  [Primary CTA]                      │
│  *hero image*                       │
│                                     │
├─────────────────────────────────────┤
│  [Logo] [Logo] [Logo] [Logo]        │
│  "Quote" — Author                   │
├─────────────────────────────────────┤
│                                     │
│  FEATURES                           │
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │ Icon   │ │ Icon   │ │ Icon   │  │
│  │ Title  │ │ Title  │ │ Title  │  │
│  │ Desc   │ │ Desc   │ │ Desc   │  │
│  └────────┘ └────────┘ └────────┘  │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  HOW IT WORKS                       │
│  1 → 2 → 3                          │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  [FINAL CTA]                        │
│  Headline                           │
│  [Get Started]                      │
│                                     │
├─────────────────────────────────────┤
│  Footer                             │
└─────────────────────────────────────┘
```

---

## Best Practices

### CTA Strategy

- **One primary action** per section
- Repeat primary CTA every 2-3 sections
- Use progressive disclosure (secondary CTAs for info)

### Copy Guidelines

| Element | Length | Focus |
|---------|--------|-------|
| Headline | ≤ 10 words | Customer outcome |
| Subheadline | ≤ 25 words | How it works |
| Feature title | ≤ 5 words | Benefit, not feature |
| Feature desc | ≤ 15 words | Specific value |
| CTA text | 2-4 words | Action + outcome |

### Visual Hierarchy

1. Hero: Largest text, highest contrast
2. Section headings: Clear but subordinate
3. Body text: Readable, comfortable line length
4. CTAs: High contrast, prominent placement

---

## Responsive Considerations

### Mobile-First Approach

- Single column layout
- Stacked sections
- Touch-friendly CTAs (min 44px height)
- Collapsible navigation

### Desktop Enhancements

- Side-by-side hero
- Multi-column feature grids
- Persistent navigation
- Larger typography scale

---

## Example File Structure

```
src/
├── sections/
│   ├── Hero.tsx
│   ├── SocialProof.tsx
│   ├── Features.tsx
│   ├── HowItWorks.tsx
│   ├── Pricing.tsx
│   ├── FAQ.tsx
│   └── FinalCTA.tsx
├── components/
│   ├── LogoBar.tsx
│   ├── FeatureCard.tsx
│   ├── Step.tsx
│   ├── PricingTier.tsx
│   └── AccordionItem.tsx
└── pages/
    └── index.tsx
```

---

## Validation Checklist

- [ ] Single clear CTA throughout
- [ ] No navigation distractions (minimal header)
- [ ] Social proof above the fold
- [ ] Feature benefits (not just features)
- [ ] Mobile-optimized layout
- [ ] Fast load time (optimize images)
- [ ] Form validation (if capturing leads)

---

## References

- [Landing Page Best Practices](https://unbounce.com/landing-page-articles/best-practices/)
- [Conversion Copywriting](https://copyhackers.com/)
- [CRO Fundamentals](https://www.crazyegg.com/blog/conversion-rate-optimization/)
