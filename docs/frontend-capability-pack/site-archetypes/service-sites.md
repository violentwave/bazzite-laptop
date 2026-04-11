# Service/Business Sites

Prompts and scaffold guidance for multi-page service business websites.

---

## Purpose

Service sites establish credibility and guide visitors to **contact or book**. Multiple pages allow deeper content: services, about, portfolio, and contact.

---

## Standard Pages

### 1. Home

**Purpose:** Overview + conversion

**Sections:**
- Hero (value prop + CTA)
- Services overview (3-4 cards)
- Social proof (logos/testimonials)
- Process (how you work)
- CTA section

**Prompt:**

```markdown
TASK: Create a service business homepage with multiple conversion paths.

CONTEXT:
- Business type: [consulting/agency/trade/etc.]
- Services: [list 3-4]
- Target clients: [description]
- CTA: [contact/book/quote]

FORMAT:
- index.tsx page
- Multiple section imports
- Navigation to other pages

CONSTRAINTS:
- Clear service differentiation
- Trust signals (testimonials, logos)
- Multiple CTAs (not competing)
- Load time < 3s
```

### 2. Services

**Purpose:** Detail offerings

**Structure:**
- Service overview
- Individual service cards/pages
- Pricing (if standardized)
- FAQs per service

**Prompt:**

```markdown
TASK: Build a services page with detailed offerings.

CONTEXT:
- Services: [list with descriptions]
- Pricing model: [hourly/fixed/quote]
- Differentiators: [what makes you unique]

FORMAT:
- services.tsx or services/
  - index.tsx
  - [service-name].tsx (if detailed pages)
- ServiceCard.tsx

CONSTRAINTS:
- Each service: problem → solution → outcome
- Clear next step (CTA) per service
- Cross-link related services
- Mobile: cards stack, desktop: grid
```

### 3. About

**Purpose:** Build trust through story

**Sections:**
- Company story/mission
- Team (optional)
- Values
- Process/approach
- Certifications/awards

**Prompt:**

```markdown
TASK: Create an about page that builds credibility.

CONTEXT:
- Company story: [2-3 paragraphs]
- Values: [list 3-4]
- Team size: [solo/small/large]
- Years in business: [number]

FORMAT:
- about.tsx
- StorySection.tsx
- ValuesGrid.tsx
- TeamSection.tsx (if applicable)

CONSTRAINTS:
- Authentic voice (not corporate-speak)
- Photos of real people (not stock if possible)
- Specific claims (not vague superlatives)
- Contact CTA at bottom
```

### 4. Portfolio/Case Studies

**Purpose:** Show work quality

See [portfolios.md](portfolios.md) for detailed guidance.

### 5. Contact

**Purpose:** Make it easy to reach you

**Elements:**
- Contact form (name, email, message)
- Alternative contact methods (phone, email)
- Address/location (if physical)
- Map (if relevant)
- Response time expectation

**Prompt:**

```markdown
TASK: Build a contact page with form and alternatives.

CONTEXT:
- Preferred contact: [form/email/phone]
- Response time: [hours/days]
- Location: [address/remote]
- Phone: [number or none]

FORMAT:
- contact.tsx
- ContactForm.tsx (with validation)
- ContactInfo.tsx
- Map.tsx (if applicable)

CONSTRAINTS:
- Form validation with error messages
- Loading state on submit
- Success confirmation
- Accessible labels on all fields
- Phone links use tel: protocol
```

---

## Navigation Structure

```
Header
├── Logo → Home
├── Services (dropdown or page)
│   ├── Service A
│   ├── Service B
│   └── Service C
├── About
├── Portfolio
├── Blog (optional)
└── Contact [CTA button]
```

### Mobile Navigation

- Hamburger menu
- Full-screen overlay or slide-out drawer
- Accordion for dropdown items
- Clear close button

---

## Trust-Building Elements

### Social Proof

- Client logos (grayscale)
- Testimonials (with photos)
- Case studies with results
- Reviews/ratings

### Credibility Signals

- Years in business
- Number of clients/projects
- Certifications/badges
- Industry memberships
- Press mentions

### Process Transparency

- Step-by-step workflow
- Timeline expectations
- Communication frequency
- Deliverable details

---

## Conversion Strategy

### Primary CTAs

| Page | Primary CTA | Secondary CTA |
|------|-------------|---------------|
| Home | Contact/Book | View Services |
| Services | Get Quote | View Portfolio |
| About | Contact | View Services |
| Portfolio | Start Project | Contact |
| Contact | Send Message | Call |

### Form Optimization

- Minimum fields (name, email, message)
- Progressive fields (only if needed)
- Auto-save draft
- Clear error messages
- Success state with next steps

---

## Example File Structure

```
src/
├── pages/
│   ├── index.tsx
│   ├── services/
│   │   ├── index.tsx
│   │   ├── consulting.tsx
│   │   └── design.tsx
│   ├── about.tsx
│   ├── portfolio/
│   │   ├── index.tsx
│   │   └── [slug].tsx
│   └── contact.tsx
├── sections/
│   ├── home/
│   │   ├── Hero.tsx
│   │   ├── ServicesPreview.tsx
│   │   └── Testimonials.tsx
│   ├── services/
│   │   ├── ServiceHero.tsx
│   │   └── ServiceList.tsx
│   └── about/
│       ├── Story.tsx
│       ├── Values.tsx
│       └── Team.tsx
└── components/
    ├── ContactForm.tsx
    ├── TestimonialCard.tsx
    └── CaseStudyCard.tsx
```

---

## SEO Considerations

### Page Meta

```tsx
// Each page
<Head>
  <title>Service Name | Company Name</title>
  <meta name="description" content="Clear value proposition in 155 chars" />
</Head>
```

### Local SEO (if applicable)

- NAP (Name, Address, Phone) consistent
- Local business schema
- Google Business Profile link
- Local keywords in content

### Service Schema

```json
{
  "@context": "https://schema.org",
  "@type": "ProfessionalService",
  "name": "Company Name",
  "description": "What you do",
  "url": "https://yoursite.com",
  "telephone": "+1-234-567-8900",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "City",
    "addressRegion": "State",
    "postalCode": "12345"
  }
}
```

---

## Validation Checklist

- [ ] Navigation clear on all pages
- [ ] Services differentiated clearly
- [ ] Contact methods prominent
- [ ] Trust signals throughout
- [ ] Mobile navigation functional
- [ ] Forms validated and accessible
- [ ] Page load times < 3s
- [ ] SEO meta on every page

---

## References

- [Service Business Website Guide](https://www.squarespace.com/resources/guides/service-business-website)
- [Local SEO Checklist](https://moz.com/local-seo-guide)
