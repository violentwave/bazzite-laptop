# Ops: Monitoring & Alerting

Uptime monitoring, error tracking, and alerting for launched websites.

---

## Purpose

This runbook covers monitoring setup, error tracking configuration, and on-call procedures. It's the "eyes" on your production site after launch.

For incident response, see [Ops: Launch Procedures](ops-launch-procedures.md).

---

## Monitoring Stack Options

| Category | Free Tier | Paid/Enterprise |
|----------|-----------|-----------------|
| **Uptime** | UptimeRobot, BetterUptime free tier | BetterUptime, Pingdom, StatusCake |
| **Error Tracking** | Sentry free tier, platform-native | Sentry paid, Rollbar, Bugsnag |
| **APM** | Platform-native, basic metrics | Datadog, New Relic, Honeycomb |
| **Logs** | Platform-native | Logtail, LogDNA, Papertrail |
| **Synthetic** | Lighthouse CI, Checkly free tier | Checkly, Pingdom checks |

---

## Uptime Monitoring Setup

### UptimeRobot (Free)

**Account setup:**
1. Create account at uptimerobot.com
2. Add new monitor

**Monitor configuration:**
```
Monitor Type: HTTPS
Friendly Name: example.com homepage
URL: https://example.com
Monitoring Interval: 5 minutes
Monitor Timeout: 30 seconds

Alert Contacts:
  - Email: on-call@company.com
  - Slack: #alerts (requires Slack integration)
```

**Key pages to monitor:**
- Homepage: `https://example.com/`
- Key conversion page: `https://example.com/contact`
- API health: `https://api.example.com/health` (if applicable)

**UptimeRobot keyword monitoring:**
- Enable "Ping Keyword" to verify specific text on page
- Example: "Welcome" must appear on homepage

### BetterUptime (Recommended)

**Free tier:**
- 10 monitors
- 3 minute intervals
- Email + Slack alerts

**Setup:**
```bash
# Create monitor via API (if using paid)
curl -X POST "https://api.betteruptime.com/api/v2/monitors" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "monitor": {
      "url": "https://example.com",
      "monitor_type": "http",
      "expected_status": "200"
    }
  }'
```

### Platform-Native Monitoring

**Vercel:**
- Dashboard → Analytics → Real-time visitors
- Dashboard → Deployments → Logs per deployment
- Enable Vercel Analytics for detailed metrics

**Netlify:**
- Dashboard → Analytics tab
- Forms → Submissions (for form monitoring)
- Deployments → Deploy logs

**Cloudflare:**
- Dashboard → Analytics
- Dashboard → Logs (Enterprise)
- Status Page: status.cloudflare.com

### Health Check Endpoints

**Create a dedicated health check endpoint:**

```typescript
// pages/api/health.ts (Next.js)
import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV,
  };
  
  // Add database check if applicable
  // const dbHealthy = await checkDatabase();
  // if (!dbHealthy) health.status = 'degraded';
  
  res.status(200).json(health);
}

// Access at: /api/health
```

**Monitor the health endpoint:**
```
URL: https://example.com/api/health
Expected status: 200
Expected response: {"status":"ok"}
Interval: Every 1 minute
```

---

## Error Tracking Setup

### Sentry (Recommended)

**Installation:**

```bash
npm install @sentry/nextjs
# or
npm install @sentry/react @sentry/tracing
```

**Configuration (Next.js):**

```javascript
// sentry.client.config.js
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1, // 10% of transactions
  
  // Performance monitoring
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  
  // Filter noise
  ignoreErrors: [
    'ResizeObserver loop limit exceeded',
    'Network request failed',
  ],
});
```

**Environment variables:**
```bash
# .env.production
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_AUTH_TOKEN=xxx  # For source maps
```

**Capture custom errors:**

```javascript
import * as Sentry from '@sentry/nextjs';

try {
  await riskyOperation();
} catch (error) {
  Sentry.captureException(error, {
    tags: { feature: 'checkout' },
    user: { id: user.id, email: user.email },
  });
  throw error;
}
```

**Sentry Dashboard Setup:**
1. Create project in Sentry
2. Copy DSN to environment variables
3. Configure alerts: Errors → Create Alert
4. Alert when: "Any issue" > "Count" > ">= 10" in "1 hour"
5. Notify: Email + Slack integration

### Platform-Native Error Tracking

**Vercel:**
- Dashboard → Project → Logs
- Enable "Log Drains" for external logging (Enterprise)

**Netlify:**
- Dashboard → Functions → Logs
- Forms → Spam filtering (built-in)

**Cloudflare:**
- Dashboard → Analytics → Logs (Enterprise feature)

---

## Performance Monitoring

### Lighthouse CI

**Install:**
```bash
npm install -g @lhci/cli
```

**Configuration:**
```javascript
// lighthouserc.js
module.exports = {
  ci: {
    collect: {
      url: ['https://example.com/', 'https://example.com/contact'],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo': ['warn', { minScore: 0.9 }],
      },
    },
    upload: {
      target: 'lhci',
      serverBaseUrl: 'https://your-lhci-server.com',
    },
  },
};
```

**Run on schedule (cron):**
```cron
# Every 6 hours
0 */6 * * * lhci autorun --upload
```

### Web Vitals Monitoring

**Collect Core Web Vitals:**

```javascript
// lib/webVitals.js
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics(metric) {
  const body = JSON.stringify({
    name: metric.name,
    value: metric.value,
    id: metric.id,
    page: window.location.pathname,
  });
  
  // Use sendBeacon for reliability
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/vitals', body);
  } else {
    fetch('/api/vitals', { body, method: 'POST', keepalive: true });
  }
}

export function reportWebVitals() {
  getCLS(sendToAnalytics);
  getFID(sendToAnalytics);
  getFCP(sendToAnalytics);
  getLCP(sendToAnalytics);
  getTTFB(sendToAnalytics);
}
```

**API endpoint to collect:**

```javascript
// pages/api/vitals.ts
import type { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).end();
  }
  
  const metric = req.body;
  
  // Store in your preferred backend
  // await storeMetric(metric);
  
  console.log('Web Vital:', metric.name, metric.value);
  
  res.status(200).end();
}
```

---

## Alerting Rules

### Critical Alerts (Wake someone up)

| Alert | Condition | Channel |
|-------|-----------|---------|
| Site Down | HTTP 5xx or timeout | PagerDuty, Phone call |
| SSL Expiring | < 14 days to expiry | Email, Slack |
| Error Spike | Error rate > 1% of requests | PagerDuty |
| Form Failure | No submissions in 24h (if expected) | Slack |

### Warning Alerts (Check during business hours)

| Alert | Condition | Channel |
|-------|-----------|---------|
| Performance Degraded | Lighthouse performance < 80 | Slack |
| Error Rate Elevated | Error rate > 0.1% | Slack |
| Slow Response | TTFB > 1s | Slack |
| Certificate Renewal | < 30 days to expiry | Email |

### Info Alerts (Weekly digest)

| Alert | Condition | Channel |
|-------|-----------|---------|
| Traffic Anomaly | Traffic ± 50% from baseline | Email |
| Performance Trend | Lighthouse score change > 5 | Email |
| New Error Type | First occurrence of error type | Sentry |

### Sentry Alert Rules

```yaml
# .sentryclirc
[alerts]
# High priority: any new error
[[alerts.notification]]
level = "warning"
notifications = ["slack:alerts"]

# Critical: more than 10 occurrences
[[alerts.threshold]]
threshold = 10
timeWindow = "1h"
level = "error"
```

### UptimeRobot Alert Rules

```
Alert Settings:
1. Down for 1 check → Email
2. Down for 2 checks → Email + Slack
3. Down for 3+ checks → Email + Slack + SMS (if configured)

Recovery:
- Send "Up" notification when recovered
```

---

## Log Aggregation

### Platform Logs (Built-in)

**Vercel:**
```bash
# View logs
vercel logs --prod

# Stream logs
vercel logs --follow --prod
```

**Netlify:**
```bash
# Netlify CLI
netlify deploy:log

# Dashboard → Deploys → [Deployment] → Log
```

### Structured Logging Best Practices

```javascript
// Use structured logging
import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
});

// Good: structured
logger.info({ userId: user.id, action: 'login' }, 'User logged in');

// Bad: unstructured
// logger.info(`User ${user.id} logged in`);

// Include context
logger.error({
  err: error,
  userId: user.id,
  requestId: req.headers['x-request-id'],
}, 'Request failed');
```

### Log Retention

| Log Type | Free Tier Retention | Recommended |
|----------|---------------------|-------------|
| Platform logs | 1-7 days | Not suitable for audit |
| Sentry errors | 30 days (free) | 90 days (paid) |
| Application logs | 1-3 days (free) | Configurable with external service |
| Access logs | Often not available | Cloudflare Enterprise, self-hosted nginx |

---

## Synthetic Monitoring

### Key Routes to Monitor

```yaml
# routes-to-monitor.yaml
routes:
  - name: Homepage
    url: /
    expected_status: 200
    expected_keyword: Welcome
    
  - name: Contact Page
    url: /contact
    expected_status: 200
    expected_keyword: Contact Us
    
  - name: API Health
    url: /api/health
    expected_status: 200
    expected_json:
      status: ok
      
  - name: Static Asset
    url: /assets/logo.png
    expected_status: 200
    expected_content_type: image/png
```

### Checkly (Synthetic Checks)

**Installation:**
```bash
npm install @checkly/cli
```

**Configuration:**
```javascript
// checkly.config.js
const { Check } = require('@checkly/cli');

new Check({
  name: 'Homepage Smoke Test',
  url: 'https://example.com',
  assertions: [
    { type: 'statusCode', value: 200 },
    { type: 'body', value: /Welcome/ },
    { type: 'responseTime', value: '< 3000' },
  ],
  frequency: 5, // minutes
  locations: ['us-east-1', 'eu-west-1'],
});
```

---

## On-Call Procedures

### Rotation Template

**One-week rotation:**
- Week 1: Engineer A
- Week 2: Engineer B
- Week 3: Engineer C
- Week 4: Engineer D
- Repeat

### Handoff Template

```markdown
## On-Call Handoff — [Week of Date]

**Outgoing Engineer:** [Name]
**Incoming Engineer:** [Name]

### Current Incidents
- [List any open or recent incidents]

### Ongoing Issues
- [List known issues being monitored]

### Recent Deploys
- [List deployments in last 7 days]

### Monitoring Status
- Uptime monitoring: [Any scheduled maintenance?]
- Error tracking: [Any noisy alerts to adjust?]
- Known issues: [List issues with workarounds]

### Emergency Contacts
- Platform support: [Vercel/Netlify/Cloudflare support links]
- DNS registrar: [Registrar support link]
- SSL provider: [Let's Encrypt / SSL provider]

### Notes
- [Any other context incoming engineer should know]
```

### Escalation Path

```
Level 1: On-Call Engineer (immediate, 15 min SLA)
    ↓ (if not resolved in 15 min)
Level 2: Secondary Engineer (15-30 min SLA)
    ↓ (if not resolved in 30 min)
Level 3: Engineering Manager (30-60 min SLA)
    ↓ (if not resolved in 60 min)
Level 4: VP Engineering (60+ min, business impact)
```

### Runbook for On-Call

**When receiving an alert:**

1. **Acknowledge** the alert in monitoring tool
2. **Diagnose** using [Troubleshooting Playbook](ops-troubleshooting-playbook.md)
3. **Communicate** to team (Slack #incidents)
4. **Mitigate** if fix not immediate (rollback, feature flag, disable)
5. **Fix** root cause
6. **Verify** site working
7. **Resolve** alert and update incident channel
8. **Document** in post-incident review

---

## Incident Response Communication Template

### Status Page Template

```markdown
# [Service Name] Status

## Current Status: [Operational / Degraded / Major Outage]

### Active Incidents
[#123] - [Short Description] - Investigating

## Incident Details

**Started:** [Time]
**Detected:** [Time]
**Impact:** [Description of user impact]
**Status:** [Investigating / Identified / Monitoring / Resolved]
**Updates:**

- [Time] We're investigating reports of [issue].
- [Time] We've identified the cause as [root cause].
- [Time] A fix is being rolled out.
- [Time] Service is restored. We're monitoring.
- [Time] Incident resolved. [Post-incident review link]
```

---

## Weekly Maintenance Checklist

### Weekly (During Business Hours)

```markdown
# Weekly Maintenance Checklist

**Date:** [YYYY-MM-DD]
**Engineer:** [Name]

## Uptime
- [ ] Check uptime for last 7 days (target: 99.9%+)
- [ ] Review any downtime incidents
- [ ] Verify all monitors active

## SSL Certificates
- [ ] Check certificate expiry (target: >30 days)
- [ ] Verify renewal automation working

## Error Tracking
- [ ] Review Sentry dashboard for new errors
- [ ] Triage unresolved issues
- [ ] Check error rate trends (target: <0.1%)

## Performance
- [ ] Review Lighthouse scores
- [ ] Check Core Web Vitals trends
- [ ] Review slow query logs (if applicable)

## Logs
- [ ] Review recent error logs
- [ ] Check for suspicious activity (security)
- [ ] Verify log retention policy

## Backups
- [ ] Verify backup completed successfully
- [ ] Test restore procedure (monthly)
```

---

## References

- [Ops: Launch Procedures](ops-launch-procedures.md) — Launch day runbooks
- [Ops: Troubleshooting Playbook](ops-troubleshooting-playbook.md) — Incident diagnosis
- [Launch Handoff Checklist](launch-handoff-checklist.md) — Post-launch monitoring setup