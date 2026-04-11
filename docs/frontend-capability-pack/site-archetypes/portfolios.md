# Portfolios

Prompts and scaffold guidance for creative work showcases.

---

## Purpose

Portfolio sites demonstrate **creative skill and style** through curated work examples. They balance visual impact with usability, prioritizing the work itself.

---

## Key Principles

1. **Work first:** Projects are the hero
2. **Show, don't tell:** Visuals over text
3. **Simple navigation:** Easy to browse
4. **Fast loading:** Optimized images
5. **Mobile-optimized:** Many view on phones

---

## Standard Pages

### 1. Home/Landing

**Sections:**
- Minimal hero (name + tagline)
- Featured projects grid
- About teaser
- Contact CTA

**Prompt:**

```markdown
TASK: Create a portfolio homepage focused on work showcase.

CONTEXT:
- Creator: [name/title]
- Tagline: [one-liner]
- Featured projects: [3-6 best pieces]
- Style: [minimal/bold/playful]

FORMAT:
- index.tsx
- ProjectGrid.tsx
- FeaturedProject.tsx (for hero project)

CONSTRAINTS:
- Project thumbnails load fast (WebP, lazy)
- Grid: masonry or uniform
- Hover reveals project title
- Click to project detail
```

### 2. Project Gallery

**Purpose:** Browse all work

**Layouts:**
- Grid (uniform or masonry)
- List with thumbnails
- Filterable by category

**Prompt:**

```markdown
TASK: Build a filterable project gallery.

CONTEXT:
- Projects: [list with categories]
- Categories: [branding/web/photography/etc.]
- Layout preference: [grid/masonry]

FORMAT:
- projects/index.tsx
- ProjectCard.tsx
- FilterBar.tsx

CONSTRAINTS:
- Filter with smooth animation
- Lazy load images below fold
- Each card: image + title + category
- Click opens project detail
- Responsive: 1-3 columns
```

### 3. Project Detail

**Purpose:** Deep dive into one project

**Content:**
- Hero image/video
- Project overview
- Challenge + solution
- Process/steps
- Results/outcomes
- Multiple images
- Next/previous project nav

**Prompt:**

```markdown
TASK: Create a detailed project case study page.

CONTEXT:
- Project: [name]
- Client: [name/type]
- Role: [your contribution]
- Challenge: [problem]
- Solution: [approach]
- Results: [outcomes]
- Images: [list assets needed]

FORMAT:
- projects/[slug].tsx
- ProjectHero.tsx
- ProjectContent.tsx
- ImageGallery.tsx
- ProjectNav.tsx (next/prev)

CONSTRAINTS:
- Large images optimized (max 200KB each)
- Image gallery with lightbox
- Process shown visually
- Credits/team acknowledged
- Related projects at bottom
```

### 4. About

**Purpose:** Humanize the creator

**Content:**
- Photo/bio
- Skills/tools
- Process/approach
- Experience/clients
- Contact/social links

**Prompt:**

```markdown
TASK: Build an about page for a creative professional.

CONTEXT:
- Bio: [2-3 paragraphs]
- Photo: [professional/casual]
- Skills: [list 6-10]
- Tools: [software/hardware]
- Experience: [years/clients]

FORMAT:
- about.tsx
- BioSection.tsx
- SkillsGrid.tsx
- ClientsList.tsx

CONSTRAINTS:
- Authentic voice (not resume-speak)
- Photo with personality
- Skills visual (icons or progress)
- Download resume link (optional)
```

### 5. Contact

**Purpose:** Make it easy to hire

**Elements:**
- Simple contact form
- Email (with copy button)
- Social links
- Availability status (optional)

---

## Project Card Pattern

```tsx
// ProjectCard.tsx
interface ProjectCardProps {
  title: string;
  category: string;
  thumbnail: string;
  slug: string;
}

function ProjectCard({ title, category, thumbnail, slug }: ProjectCardProps) {
  return (
    <a href={`/projects/${slug}`} className="group block">
      <div className="relative aspect-[4/3] overflow-hidden">
        <img
          src={thumbnail}
          alt={`${title} project thumbnail`}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/20" />
      </div>
      <div className="mt-3">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600">{category}</p>
      </div>
    </a>
  );
}
```

---

## Image Optimization

### Requirements

- **Format:** WebP with JPEG fallback
- **Sizing:** Multiple sizes (thumbnail, full, hero)
- **Loading:** Lazy below fold, eager for hero
- **Compression:** 80-85% quality
- **Max size:** 200KB per image

### Implementation

```tsx
// Responsive image with art direction
<picture>
  <source
    srcSet="/images/project-hero.webp"
    type="image/webp"
  />
  <img
    src="/images/project-hero.jpg"
    alt="Project hero image"
    width="1200"
    height="800"
    loading="lazy"
  />
</picture>
```

---

## Gallery Patterns

### Masonry Grid

```tsx
// Using CSS columns
<div className="columns-1 gap-4 sm:columns-2 lg:columns-3">
  {projects.map(project => (
    <div key={project.id} className="mb-4 break-inside-avoid">
      <ProjectCard {...project} />
    </div>
  ))}
</div>
```

### Uniform Grid

```tsx
<div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
  {projects.map(project => (
    <ProjectCard key={project.id} {...project} />
  ))}
</div>
```

### Lightbox

```tsx
// Lightbox for full-size images
<AnimatePresence>
  {selectedImage && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/90"
      onClick={closeLightbox}
    >
      <button
        className="absolute right-4 top-4 text-white"
        onClick={closeLightbox}
      >
        Close
      </button>
      <img
        src={selectedImage}
        alt=""
        className="max-h-screen max-w-full object-contain"
      />
    </motion.div>
  )}
</AnimatePresence>
```

---

## Navigation Patterns

### Minimal Header

- Logo/name (left)
- Simple nav: Work, About, Contact
- Mobile: hamburger

### Footer

- Social links
- Email
- Copyright
- Back to top

---

## Example File Structure

```
src/
├── pages/
│   ├── index.tsx
│   ├── projects/
│   │   ├── index.tsx
│   │   └── [slug].tsx
│   ├── about.tsx
│   └── contact.tsx
├── components/
│   ├── portfolio/
│   │   ├── ProjectCard.tsx
│   │   ├── ProjectGrid.tsx
│   │   ├── ProjectHero.tsx
│   │   ├── ProjectGallery.tsx
│   │   ├── Lightbox.tsx
│   │   └── FilterBar.tsx
│   └── layout/
│       ├── Header.tsx
│       └── Footer.tsx
├── lib/
│   └── projects.ts (project data)
└── public/
    └── images/
        └── projects/
            ├── project-1/
            │   ├── thumb.webp
            │   ├── hero.webp
            │   └── gallery/
```

---

## Performance Priorities

1. **Image optimization** — Largest impact
2. **Lazy loading** — Below-fold content
3. **Code splitting** — Route-based
4. **Font loading** — Font-display: swap
5. **Minimize animations** — Respect reduced motion

---

## Validation Checklist

- [ ] Images optimized (WebP, <200KB)
- [ ] Lazy loading for galleries
- [ ] Lightbox keyboard accessible
- [ ] Project navigation clear
- [ ] Mobile layout tested
- [ ] Image alt text descriptive
- [ ] Fast load on 3G
- [ ] Contact easy to find

---

## References

- [Portfolio Design Tips](https://www.nngroup.com/articles/portfolio-design/)
- [Image Optimization Guide](https://web.dev/fast/#optimize-your-images)
