# Environment & Configuration Checklist

Structured checklist for environment variables, configuration management, and deployment environments.

---

## Purpose

This checklist ensures consistent configuration management across development, staging, and production environments. It covers environment variables, build configurations, and deployment-specific settings.

---

## Environment Types Overview

| Environment | Purpose | URL Pattern | Config File |
|-------------|---------|-------------|-------------|
| Development | Local development | `localhost:*` | `.env.development` |
| Staging | Pre-production testing | `staging.*.com` | `.env.staging` |
| Production | Live site | `*.com` | `.env.production` |

---

## Environment Variables Schema

### Variable Categories

| Category | Prefix | Examples | Exposure |
|----------|--------|----------|----------|
| Public | `NEXT_PUBLIC_`, `VITE_` | `NEXT_PUBLIC_API_URL` | Client-side OK |
| Private | None | `DATABASE_URL`, `API_SECRET` | Server-only |
| Feature Flags | `FEATURE_` | `FEATURE_NEW_CHECKOUT` | Server/Client as needed |
| Analytics | `ANALYTICS_`, `NEXT_PUBLIC_GA_` | `NEXT_PUBLIC_GA_ID` | Client-side |
| Integration | `*_KEY`, `*_SECRET` | `STRIPE_SECRET_KEY` | Server-only |

### Complete Variable Template

```bash
# .env.example - Template for all required variables

# ===========================================
# PUBLIC VARIABLES (exposed to client)
# ===========================================

# Application
NEXT_PUBLIC_APP_NAME=YourApp
NEXT_PUBLIC_APP_URL=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Analytics (client-side)
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
NEXT_PUBLIC_GTM_ID=GTM-XXXXXXX

# Feature Flags
NEXT_PUBLIC_FEATURE_NEW_FEATURE=false

# External Services (public keys only)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxx

# ===========================================
# PRIVATE VARIABLES (server-only)
# ===========================================

# Authentication
AUTH_SECRET=your-auth-secret
AUTH_URL=https://yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# API Keys (never expose to client!)
API_SECRET_KEY=your-api-secret
STRIPE_SECRET_KEY=sk_live_xxx

# Integration Secrets
SENDGRID_API_KEY=SG.xxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/xxx

# ===========================================
# DEPLOYMENT PLATFORM VARIABLES
# ===========================================

# Set by platform automatically
# VERCEL_URL
# NETLIFY_URL
# CF_PAGES_URL
```

---

## Environment Checklist

### Development Environment

- [ ] `.env.development` created from `.env.example`
- [ ] All `NEXT_PUBLIC_` variables set
- [ ] Mock/stub values for production-only services
- [ ] Local API endpoints configured
- [ ] Feature flags default to `false` for new features
- [ ] Development database configured (if needed)
- [ ] `.env.development.local` for personal overrides (gitignored)

### Staging Environment

- [ ] `.env.staging` created from `.env.example`
- [ ] Staging API endpoints configured
- [ ] Test analytics IDs (if using test property)
- [ ] Staging database connection
- [ ] Email testing service configured
- [ ] Payment gateway test mode enabled
- [ ] Preview deployment URL resolves correctly

### Production Environment

- [ ] `.env.production` variables set in platform dashboard
- [ ] `.env.example` updated and committed
- [ ] Secrets stored securely (not in code)
- [ ] Production database credentials rotated
- [ ] Analytics production IDs configured
- [ ] Payment gateway live mode enabled
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Rate limiting configured

---

## Platform Environment Setup

### Vercel

```bash
# Via Vercel CLI
vercel env add NEXT_PUBLIC_API_URL production
vercel env add DATABASE_URL production

# Pull to local
vercel env pull .env.local

# List environments
vercel env ls
```

**Environment Priority (Vercel):**
1. System Environment Variables
2. `.env.production.local`
3. `.env.production`
4. `.env.local`
5. `.env`

### Netlify

```bash
# Via Netlify CLI
netlify env:set NEXT_PUBLIC_API_URL "https://api.example.com"
netlify env:set DATABASE_URL "postgresql://..."

# Import from file
netlify env:import .env.production

# List variables
netlify env:list
```

**Environment Priority (Netlify):**
1. Netlify Dashboard Environment Variables
2. `netlify.toml` [context.production.environment]
3. `.env.production`
4. `.env`

### Cloudflare Pages

```bash
# Via Wrangler CLI
wrangler pages secret put DATABASE_URL
# Enter secret when prompted

# Via Dashboard:
# Settings > Environment variables > Add variable
```

### AWS Amplify

Via AWS Console:
1. App settings > Environment variables
2. Add key-value pairs
3. Ensure `AMPLIFY_*` prefix for Amplify-specific variables

---

## Configuration Files

### Framework Configurations

#### Next.js

```javascript
// next.config.js
const nextConfig = {
  env: {
    // Only use for build-time constants
    // Prefer NEXT_PUBLIC_ prefix for runtime vars
    CUSTOM_BUILD_VAR: process.env.CUSTOM_BUILD_VAR,
  },
  publicRuntimeConfig: {
    // Available on both server and client
    staticFolder: '/static',
  },
  serverRuntimeConfig: {
    // Server-only
    mySecret: process.env.MY_SECRET,
  },
};
```

#### Vite

```javascript
// vite.config.js
export default defineConfig({
  define: {
    // Inject at build time
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
});

// Access in code
// vite handles VITE_ prefix automatically
const apiUrl = import.meta.env.VITE_API_URL;
```

#### Create React App

```javascript
// CRA only exposes REACT_APP_ prefixed variables
const apiUrl = process.env.REACT_APP_API_URL;

// In code
if (process.env.NODE_ENV === 'production') {
  // Production-specific logic
}
```

---

## Secrets Management

### Secret Storage Locations

| Secret Type | Storage | Notes |
|-------------|---------|-------|
| API Keys | Platform dashboard | Encrypted at rest |
| Database URLs | Platform dashboard | Use connection pooling |
| Auth Secrets | Secret manager | Rotate regularly |
| Payment Keys | Platform dashboard | Test/Live mode toggle |
| Webhook Secrets | Platform dashboard | Verify signatures |

### Secret Rotation Checklist

- [ ] Generate new secret value
- [ ] Update in secret manager/platform
- [ ] Update environment variables (rolling deployment)
- [ ] Verify application still works
- [ ] Revoke old secret after grace period
- [ ] Document rotation date

### Never Commit

```gitignore
# .gitignore
.env
.env.local
.env.*.local
.env.production
.env.staging

# Platform-specific
.vercel/
.netlify/

# Secrets
*.pem
*.key
secrets.*
credentials.json
```

---

## Build-Time vs Runtime Variables

### Build-Time Variables (Static)

Embedded during build. Changing requires rebuild.

```bash
# Set during build
NEXT_PUBLIC_APP_VERSION=$npm_package_version

# Use in code
const version = process.env.NEXT_PUBLIC_APP_VERSION;
```

### Runtime Variables (Dynamic)

Read at request time. Can change without rebuild.

```javascript
// Vercel: Middleware to inject runtime config
export function middleware(request) {
  const config = {
    apiUrl: process.env.API_URL,
    featureFlags: {
      newFeature: process.env.FEATURE_NEW_FEATURE === 'true',
    },
  };
  // Attach to request/response
}
```

### Platform-Specific Runtime Config

| Platform | Mechanism | Use Case |
|----------|-----------|----------|
| Vercel | `process.env` in Edge Runtime | Dynamic feature flags |
| Netlify | Netlify Functions | API proxy, auth |
| Cloudflare | Workers KV + Environment | Global config, A/B testing |
| Amplify | Lambda environment | Backend integration |

---

## Environment Validation

### Runtime Validation

```typescript
// lib/env.ts
const requiredEnvVars = [
  'NEXT_PUBLIC_API_URL',
  'DATABASE_URL',
  'AUTH_SECRET',
] as const;

function validateEnv() {
  const missing = requiredEnvVars.filter(
    (key) => !process.env[key]
  );
  
  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}`
    );
  }
}

// Call at app startup
validateEnv();
```

### Type-Safe Environment Access

```typescript
// lib/env.ts
type Env = {
  NEXT_PUBLIC_API_URL: string;
  NEXT_PUBLIC_GA_ID: string;
  DATABASE_URL?: string;
};

function getEnv(): Env {
  return {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL!,
    NEXT_PUBLIC_GA_ID: process.env.NEXT_PUBLIC_GA_ID!,
    DATABASE_URL: process.env.DATABASE_URL,
  };
}

export const env = getEnv();
```

---

## Platform Configuration

### vercel.json

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "env": {
    NEXT_PUBLIC_APP_NAME": "MyApp"
  }
}
```

### netlify.toml

```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"

[context.production.environment]
  NEXT_PUBLIC_ENV = "production"

[context.deploy-preview.environment]
  NEXT_PUBLIC_ENV = "staging"
```

### wrangler.toml

```toml
name = "my-project"
compatibility_date = "2024-01-01"
pages_build_output_dir = "dist"

[vars]
NEXT_PUBLIC_ENV = "production"

[[kv_namespaces]]
binding = "CACHE"
id = "your-kv-id"
```

---

## Pre-Deployment Environment Audit

- [ ] All required variables documented in `.env.example`
- [ ] No hardcoded URLs or API keys in code
- [ ] `.env.*` files in `.gitignore`
- [ ] Secrets stored in platform dashboard (not code)
- [ ] Test database uses different credentials
- [ ] Production database has connection pooling
- [ ] Analytics test vs production IDs separated
- [ ] Error tracking configured for each environment
- [ ] Rate limiting values appropriate per environment
- [ ] Feature flags default to safe state

---

## References

- [Website Brief Schema](website-brief-schema.md) — Project brief
- [Deployment Target Pack](deployment-target-pack.md) — Platform guides
- [Analytics & Forms Integration](analytics-forms-integration.md) — Analytics setup
- [Launch Handoff Checklist](launch-handoff-checklist.md) — Go-live procedures