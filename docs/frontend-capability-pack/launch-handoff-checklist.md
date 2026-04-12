# Launch Handoff Checklist

Comprehensive go-live checklist and client delivery documentation template.

---

## Purpose

This checklist ensures all pre-launch, launch-day, and post-launch tasks are completed before handoff to the client. It covers technical, content, and operational readiness.

---

## Pre-Launch Checklist

### Technical Readiness

- [ ] **Build succeeds** — `npm run build` completes without errors
- [ ] **TypeScript compiles** — No type errors
- [ ] **Lint passes** — ESLint/Prettier rules satisfied
- [ ] **Tests pass** — Unit and integration tests green
- [ ] **Bundle size acceptable** — Total JS < 500KB (gzipped)
- [ ] **No console errors** — Browser console clean in production build
- [ ] **No hardcoded localhost URLs** — All URLs configurable
- [ ] **No test/demo data** — Production content only
- [ ] **No debug code** — `console.log`, `debugger`, TODO comments removed

### Performance

- [ ] **Lighthouse score** — Performance ≥ 90
- [ ] **Core Web Vitals** — LCP < 2.5s, FID < 100ms, CLS < 0.1
- [ ] **Images optimized** — WebP/AVIF with fallbacks, lazy loading
- [ ] **Fonts optimized** — Subset, preloaded, font-display: swap
- [ ] **Code split** — Route-based code splitting implemented
- [ ] **Third-party scripts** — Deferred or loaded on interaction

### Accessibility

- [ ] **Heading hierarchy** — Single H1, logical H2-H6 order
- [ ] **Alt text** — All images have descriptive alt text
- [ ] **Focus states** — Visible focus indicators on all interactive elements
- [ ] **Color contrast** — WCAG AA minimum (4.5:1 for text)
- [ ] **Keyboard navigation** — All features accessible via keyboard
- [ ] **Screen reader tested** — Tested with VoiceOver/NVDA
- [ ] **Reduced motion** — Respects `prefers-reduced-motion`
- [ ] **Form labels** — All form inputs have associated labels

### Security

- [ ] **HTTPS enforced** — SSL certificate valid
- [ ] **Security headers** — CSP, X-Frame-Options, X-Content-Type-Options
- [ ] **No exposed secrets** — No API keys in client code
- [ ] **Dependencies audited** — `npm audit` clean
- [ ] **CSRF protection** — Forms protected (if applicable)
- [ ] **XSS prevention** — User input sanitized/escaped
- [ ] **Content Security Policy** — Implemented and tested

### SEO & Metadata

- [ ] **Unique titles** — Each page has unique `<title>`
- [ ] **Meta descriptions** — Each page has unique meta description (150-160 chars)
- [ ] **OG tags** — Open Graph images and descriptions set
- [ ] **Twitter cards** — Twitter meta tags configured
- [ ] **Canonical URLs** — Self-referencing canonical tags
- [ ] **Robots.txt** — Properly configured for environment
- [ ] **Sitemap.xml** — Generated and accessible
- [ ] **Structured data** — JSON-LD implemented (if applicable)
- [ ] **Favicon** — All sizes (16, 32, 180, 512) generated

### Content

- [ ] **All pages populated** — No placeholder text
- [ ] **Spelling/grammar checked** — Content proofread
- [ ] **Links verified** — All internal/external links work
- [ ] **Images licensed** — All images properly licensed
- [ ] **Contact info verified** — Email addresses, phone numbers correct
- [ ] **Legal pages** — Privacy, Terms, Cookie policy (if required)
- [ ] **Social links** — Verified and correct

### Forms & Integrations

- [ ] **Form submissions work** — All forms submit successfully
- [ ] **Request validation** — Server-side validation implemented
- [ ] **Success messages** — User receives confirmation
- [ ] **Error handling** — Errors displayed gracefully
- [ ] **Spam protection** — Honeypot or CAPTCHA implemented
- [ ] **Email notifications** — Team receives submissions (if applicable)
- [ ] **CRM sync** — Leads exported to CRM (if applicable)
- [ ] **Analytics events** — Form events tracked in GA4

### Analytics & Tracking

- [ ] **GA4 installed** — Google Analytics 4 script live
- [ ] **Page views tracked** — Virtual page views working
- [ ] **Custom events** — All key events firing
- [ ] **Conversions marked** — Key events marked as conversions
- [ ] **Goal funnels** — Funnel steps configured (if applicable)
- [ ] **Test Traffic excluded** — Internal IPs filtered
- [ ] **Consent flow** — Cookie consent working

### Cross-Browser & Device

- [ ] **Chrome** — Tested and working
- [ ] **Firefox** — Tested and working
- [ ] **Safari** — Tested and working
- [ ] **Edge** — Tested and working
- [ ] **Mobile Safari** — Tested on iOS
- [ ] **Mobile Chrome** — Tested on Android
- [ ] **Tablet** — Tested on tablet viewport
- [ ] **360px minimum** — Site usable at small viewport

---

## Launch Day Checklist

### DNS & Domain

- [ ] **Domain resolves** — Production domain resolves to host
- [ ] **WWW redirect** — www redirects to non-www (or vice versa)
- [ ] **SSL valid** — Certificate valid and not expiring soon
- [ ] **SSL redirect** — HTTP redirects to HTTPS
- [ ] **DNS propagated** — Changes visible globally (use dnschecker.org)

### Deployment

- [ ] **Production build** — Latest code deployed
- [ ] **Environment variables** — Production values set
- [ ] **CDN configured** — Static assets served via CDN
- [ ] **Cache headers** — Proper caching configured
- [ ] **Rollback plan** — Know how to revert if needed

### Pre-Launch Verification

- [ ] **Homepage loads** — Homepage renders correctly
- [ ] **All pages accessible** — Navigation works
- [ ] **Forms submit** — Test submission succeeds
- [ ] **Analytics firing** — Real-time data visible
- [ ] **404 page** — Custom 404 displays
- [ ] **Favicon visible** — Tab shows correct icon
- [ ] **Social preview** — OG tags render correctly in social debuggers

### Final Steps

- [ ] **Remove password protection** — Site publicly accessible
- [ ] **Remove robots.txt disallow** — Allow search indexing
- [ ] **Submit sitemap** — Submit to Google Search Console
- [ ] **Notify stakeholders** — Team informed of launch

---

## Post-Launch Checklist

### Immediate (First 24 Hours)

- [ ] **Uptime monitoring** — Ping checks active
- [ ] **Error tracking** — Sentry or similar receiving errors
- [ ] **Analytics data** — Page views appearing in GA4
- [ ] **Form submissions** — Test form received
- [ ] **Search Console** — Property verified
- [ ] **Social sharing** — OG tags verified in Facebook/Twitter debuggers

### First Week

- [ ] **Core Web Vitals** — Check PageSpeed Insights
- [ ] **Search Console** — No crawl errors
- [ ] **Error logs** — No recurring errors
- [ ] **Mobile usability** — No issues in Search Console
- [ ] **Analytics review** — Initial traffic patterns visible
- [ ] **Form validation** — All submissions processed

### First Month

- [ ] **SEO indexing** — Pages appearing in search results
- [ ] **Performance report** — Lighthouse scores maintained
- [ ] **Analytics review** — Traffic patterns analyzed
- [ ] **Backup confirmed** — Backups working correctly
- [ ] **Client training** — Client comfortable with CMS

---

## Client Handoff Documentation

### Deliverables Package

| Item | Format | Location |
|------|--------|----------|
| Source Code | Git repository | GitHub/GitLab/Bitbucket |
| Design Assets | Figma/Sketch files | Shared drive |
| Documentation | Markdown/PDF | Project wiki |
| Credentials | 1Password/Secure file | Secure transfer |
| Deployment Access | Platform invite | Vercel/Netlify/etc. |

### Documentation Template

```markdown
# Project Handoff — [Project Name]

## Project Overview

**Launch Date:** [Date]
**Live URL:** https://[domain].com
**Repository:** https://github.com/[org]/[repo]

## Access Credentials

### Platform Accounts

| Service | Username/Email | Purpose |
|---------|----------------|---------|
| Vercel/Netlify | [email] | Deployment |
| Google Analytics | [email] | Analytics |
| [Domain registrar] | [account] | DNS management |

### Third-Party Services

| Service | Account | Purpose |
|---------|---------|---------|
| SendGrid | [account] | Email |
| HubSpot | [account] | CRM |
| Stripe | [account] | Payments |

## Architecture

### Tech Stack

- **Framework:** [Next.js/Vite/React/etc.]
- **Styling:** [Tailwind/CSS Modules/etc.]
- **CMS:** [Contentful/Strapi/etc.]
- **Deployment:** [Vercel/Netlify/etc.]

### Key Directories

```
/src
  /components    — Reusable UI components
  /pages         — Route pages
  /lib           — Utilities and helpers
  /styles        — Global styles
/public          — Static assets
```

## Maintenance

### Regular Tasks

- [ ] **Weekly:** Check error logs
- [ ] **Monthly:** Review analytics
- [ ] **Quarterly:** Update dependencies
- [ ] **Annually:** Renew SSL/Domain

### Update Procedure

1. Create a new branch: `git checkout -b update/[description]`
2. Update dependencies: `npm update`
3. Test locally: `npm run dev`
4. Run checks: `npm run lint && npm test`
5. Deploy: Push to main or merge PR

### Rollback Procedure

1. Go to deployment platform dashboard
2. Find the previous successful deployment
3. Click "Rollback" or "Promote"
4. Verify site functionality

## Support Contacts

### Development Team

| Role | Name | Email |
|------|------|-------|
| Lead Developer | [Name] | [email] |
| Designer | [Name] | [email] |

### Platform Support

- **Vercel:** https://vercel.com/support
- **Netlify:** https://www.netlify.com/support
- **Cloudflare:** https://support.cloudflare.com

## Known Issues

1. [Issue description and workaround]
2. [Issue description and workaround]

## Future Considerations

- [ ] Feature idea 1
- [ ] Feature idea 2
```

---

## Training Guide

### For Content Editors

1. **Logging In**
   - Access CMS at `/admin` or platform URL
   - Use provided credentials

2. **Editing Content**
   - Navigate to content type
   - Click "Edit" on desired item
   - Make changes
   - Click "Publish"

3. **Adding New Content**
   - Click "Add New"
   - Fill in required fields
   - Preview before publishing

4. **Uploading Media**
   - Go to Media Library
   - Click "Upload"
   - Select files
   - Add alt text

### For Technical Contacts

1. **Deployment**
   - Changes auto-deploy from main branch
   - Preview URLs for PRs
   - Production promotion via dashboard

2. **Monitoring**
   - Check error tracking dashboard weekly
   - Review analytics monthly
   - Check uptime alerts

3. **Updates**
   - Security updates: Apply immediately
   - Feature updates: Test in staging first

---

## Post-Handoff Support

### Warranty Period (30 Days)

- Bug fixes included
- Minor content adjustments
- Questions answered within 1 business day
- No new features

### Out of Scope

- New feature development
- Third-party integrations
- Content creation
- Marketing campaigns
- SEO optimization services

### Ongoing Support Options

| Tier | Included | Response Time |
|------|----------|---------------|
| Basic | Bug fixes, security updates | 48 hours |
| Standard | + Minor changes | 24 hours |
| Premium | + Feature development | 4 hours |

---

## References

- [Website Brief Schema](website-brief-schema.md) — Project brief
- [Deployment Target Pack](deployment-target-pack.md) — Platform guides
- [Environment Config Checklist](environment-config-checklist.md) — Environment variables
- [Analytics & Forms Integration](analytics-forms-integration.md) — Analytics setup
- [Runtime Harness](runtime-harness.md) — Preview workflow
- [Validation Flow](validation-flow.md) — Post-generation checks