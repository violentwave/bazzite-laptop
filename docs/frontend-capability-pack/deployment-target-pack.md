# Deployment Target Pack

Guidance for deploying generated websites to common hosting platforms.

---

## Purpose

This document provides deployment guidance for external website projects. It covers platform selection, configuration requirements, and deployment procedures without embedding a site runtime in this repo.

---

## Platform Selection Guide

### Quick Selection Matrix

| Project Type | Recommended Platform | Alternative |
|--------------|---------------------|-------------|
| Next.js App | Vercel | Netlify |
| Static Marketing Site | Cloudflare Pages | Netlify |
| JAMstack Blog | Netlify | Cloudflare Pages |
| SaaS Dashboard | Vercel | AWS Amplify |
| E-commerce (Next.js) | Vercel | Shopify Hydrogen |
| Portfolio | Cloudflare Pages | Netlify |
| Lead Gen Funnel | Netlify | Vercel |

### Platform Comparison

| Feature | Vercel | Netlify | Cloudflare Pages |
|----------|--------|---------|-------------------|
| **Best For** | Next.js, React apps | JAMstack, static sites | Static sites, edge |
| **Free Tier** | 100GB bandwidth | 100GB bandwidth | Unlimited bandwidth |
| **Edge Functions** | Edge Functions | Netlify Functions | Cloudflare Workers |
| **ISR Support** | Native | Limited | No |
| **Forms** | Requires integration | Built-in Forms | Requires integration |
| **Auth** | Via Auth0/etc. | Built-in Identity | Via Auth0/etc. |
| **Analytics** | Vercel Analytics | Netlify Analytics | Cloudflare Analytics |
| **Preview Deployments** | Automatic | Automatic | Automatic |
| **Custom Domains** | Included | Included | Included |
| **SSL** | Automatic | Automatic | Automatic |

---

## Vercel Deployment

### When to Choose Vercel

- Building Next.js applications
- Need ISR (Incremental Static Regeneration)
- Want best-in-class preview deployments
- React-focused team
- Budget allows for scaling costs

### Vercel Configuration Checklist

- [ ] Project created and connected to Git repository
- [ ] Build command configured (`npm run build` or equivalent)
- [ ] Output directory set (`.next` for Next.js, `dist` for Vite)
- [ ] Environment variables configured in Vercel dashboard
- [ ] Custom domain added and DNS configured
- [ ] Deployment protection enabled for previews
- [ ] Vercel Analytics enabled (optional)
- [ ] Edge functions configured if needed
- [ ] Redirects and rewrites in `vercel.json` or `next.config.js`

### Vercel Project Configuration

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" }
      ]
    }
  ],
  "redirects": [
    { "source": "/old-page", "destination": "/new-page", "permanent": true }
  ]
}
```

### Environment Variables (Vercel)

```bash
# Set via Vercel Dashboard or CLI
vercel env add NEXT_PUBLIC_API_URL production
vercel env add DATABASE_URL production
vercel env add NEXT_PUBLIC_ANALYTICS_ID production

# Pull to local
vercel env pull .env.local
```

### Vercel Security Headers

```javascript
// next.config.js
const securityHeaders = [
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin'
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()'
  }
];

module.exports = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders
      }
    ];
  }
};
```

---

## Netlify Deployment

### When to Choose Netlify

- Building JAMstack sites (Astro, Hugo, Gatsby)
- Need built-in form handling
- Want Netlify Identity for auth
- Simplicity is priority
- Budget-conscious projects

### Netlify Configuration Checklist

- [ ] Site created and connected to Git repository
- [ ] Build command configured
- [ ] Publish directory set (`dist`, `public`, `_site`)
- [ ] Environment variables in Netlify dashboard
- [ ] Custom domain configured
- [ ] HTTPS enforced
- [ ] Netlify Forms configured (if needed)
- [ ] Netlify Functions configured (if needed)
- [ ] Redirects in `_redirects` file
- [ ] Headers in `_headers` file
- [ ] Netlify Analytics enabled (optional)

### Netlify Configuration File

```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"

[[redirects]]
  from = "/old-page"
  to = "/new-page"
  status = 301

[[redirects]]
  from = "/api/*"
  to = "/.netlify/functions/:splat"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    Referrer-Policy = "origin-when-cross-origin"

[functions]
  directory = "netlify/functions"
```

### Netlify Forms

```html
<!-- Add data-netlify="true" to any form -->
<form name="contact" method="POST" data-netlify="true">
  <input type="hidden" name="form-name" value="contact" />
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <textarea name="message"></textarea>
  <button type="submit">Send</button>
</form>
```

---

## Cloudflare Pages Deployment

### When to Choose Cloudflare Pages

- Maximum free tier (unlimited bandwidth)
- Global edge network priority
- Building static sites
- Performance is critical
- Using Cloudflare Workers for edge logic

### Cloudflare Pages Configuration Checklist

- [ ] Pages project created and connected to Git
- [ ] Build command configured
- [ ] Build output directory set (`dist`, `build`, `_site`)
- [ ] Environment variables in Cloudflare dashboard
- [ ] Custom domain configured
- [ ] SSL/TLS mode set (Full Strict recommended)
- [ ] Cloudflare Workers configured for dynamic routes (optional)
- [ ] Redirects in `_redirects` file
- [ ] Headers in `_headers` file

### Cloudflare Configuration

```toml
# wrangler.toml (for Workers)
name = "my-project"
compatibility_date = "2024-01-01"
pages_build_output_dir = "dist"

[vars]
ENVIRONMENT = "production"

[[kv_namespaces]]
binding = "CACHE"
id = "your-kv-namespace-id"
```

### Cloudflare Redirects and Headers

```
# _redirects
/old-page    /new-page    301
/api/*       /.workers/:splat    200

# _headers
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: origin-when-cross-origin
```

---

## AWS Amplify Deployment

### When to Choose AWS Amplify

- Already using AWS ecosystem
- Need AWS services integration (Cognito, DynamoDB, S3)
- Building full-stack apps with Amplify backend
- Enterprise-scale deployments

### AWS Amplify Configuration Checklist

- [ ] Amplify app created and connected to Git
- [ ] Build settings configured in `amplify.yml`
- [ ] Environment variables in Amplify console
- [ ] Custom domain with Route 53 or external DNS
- [ ] Backend resources configured (if needed)
- [ ] Amplify CLI initialized in project
- [ ] Auth, API, Storage configured (if needed)

### Amplify Build Settings

```yaml
# amplify.yml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

---

## GitHub Pages Deployment

### When to Choose GitHub Pages

- Open-source projects
- Documentation sites
- Simple static sites
- No commercial requirements
- Free hosting priority

### GitHub Pages Configuration

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

---

## Platform-Specific Considerations

### Platform Lock-In Analysis

| Platform | Lock-In Risk | Portability |
|----------|--------------|-------------|
| Static Sites | None | Deploy anywhere |
| Vercel (Next.js features) | High | Some features Vercel-only |
| Netlify Functions | Medium | Portable (standard JS) |
| Netlify Identity/Forms | High | Migration required |
| Cloudflare Workers | Medium | Workers API is standard |
| Cloudflare KV/R2 | High | Proprietary storage |

### Migration Paths

**From Vercel to Netlify:**
1. Convert `vercel.json` to `netlify.toml`
2. Move API routes from Edge Functions to Netlify Functions
3. Replace Vercel Analytics with Netlify Analytics

**From Netlify to Cloudflare:**
1. Convert `netlify.toml` to `_headers` and `_redirects`
2. Move functions to Workers format
3. Replace Netlify Forms with custom form handling

**From Any to Self-Hosted:**
1. Export static build output
2. Configure reverse proxy (nginx, Caddy)
3. Set up SSL certificates
4. Configure CDN for static assets

---

## Deployment Checklist

### Pre-Deployment

- [ ] All environment variables documented
- [ ] `.env.example` updated with required variables
- [ ] Build succeeds locally (`npm run build`)
- [ ] All tests pass (`npm test`)
- [ ] Lint passes (`npm run lint`)
- [ ] Bundle size acceptable (<500KB JS)
- [ ] No hardcoded development URLs
- [ ] CSP and security headers configured
- [ ] `robots.txt` configured
- [ ] `sitemap.xml` generated

### Deployment Day

- [ ] Create deployment branch/tag
- [ ] Push to platform's connected branch
- [ ] Monitor build logs
- [ ] Verify preview deployment
- [ ] Test all critical paths
- [ ] Promote to production

### Post-Deployment

- [ ] Verify production domain resolves
- [ ] Test SSL certificate
- [ ] Verify analytics firing
- [ ] Test form submissions
- [ ] Check all CTAs routing correctly
- [ ] Verify OG images displaying
- [ ] Test on mobile devices
- [ ] Create deployment backup

---

## References

- [Environment Config Checklist](environment-config-checklist.md) — Environment variables
- [Analytics & Forms Integration](analytics-forms-integration.md) — Analytics and form setup
- [Launch Handoff Checklist](launch-handoff-checklist.md) — Go-live procedures
- [Website Brief Schema](website-brief-schema.md) — Project brief
- [Runtime Harness](runtime-harness.md) — Preview workflow