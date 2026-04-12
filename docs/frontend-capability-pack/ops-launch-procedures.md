# Ops: Launch Procedures

Step-by-step runbooks for launch day, rollback, and post-launch operations.

---

## Purpose

Concrete procedures for website launch, from DNS cutover to 72-hour post-launch checklist. Use with [Launch Handoff Checklist](launch-handoff-checklist.md) (pre-launch checks) and [Deployment Target Pack](deployment-target-pack.md) (platform configs).

---

## Pre-Launch Preparation

### 24 Hours Before Launch

**DNS Preparation:**
- [ ] Confirm DNS records ready (see [DNS Setup](ops-dns-domain-setup.md))
- [ ] Document current DNS configuration (screenshot or export)
- [ ] Prepare redirect strategy (www vs non-www)
- [ ] Confirm nameservers if changing

**Platform Preparation:**
- [ ] Production build successful (`npm run build`)
- [ ] All tests passing (`npm test`)
- [ ] Environment variables documented and set
- [ ] Deployment tested on staging/preview URL
- [ ] Rollback procedure documented

**Communication:**
- [ ] Stakeholders notified of launch window
- [ ] Support team briefed
- [ ] Monitoring/alerts configured
- [ ] Emergency contact list ready

### 1 Hour Before Launch

- [ ] Final build deployed to production
- [ ] Preview URL verified working
- [ ] DNS propagation check on multiple resolvers:
  ```bash
  dig @8.8.8.8 example.com
  dig @1.1.1.1 example.com
  dig @9.9.9.9 example.com
  ```
- [ ] SSL certificate status confirmed
- [ ] All team members available

---

## Launch Day: DNS Cutover Procedure

### Step 1: DNS Record Update

**For Vercel:**
```bash
# Update A record for apex
dig @ns.yourregistrar.com example.com +short
# Should show old IP if already configured

# Update to Vercel IP
# In DNS dashboard:
# A record: @ → 76.76.21.21
# CNAME: www → cname.vercel-dns.com
```

**For Netlify:**
```bash
# Update to Netlify IP
# A record: @ → 75.2.60.5
# CNAME: www → [site-name].netlify.app
```

**For Cloudflare Pages:**
```bash
# CNAME flattening (if using Cloudflare DNS)
# CNAME: @ → [site-name].pages.dev
# CNAME: www → [site-name].pages.dev
```

**For Self-Hosted:**
```bash
# A record: @ → YOUR_SERVER_IP
# A record: www → YOUR_SERVER_IP
```

### Step 2: Verify Propagation

```bash
#!/bin/bash
# check-propagation.sh
DOMAIN="example.com"

echo "Checking DNS propagation..."

echo "Google DNS (8.8.8.8):"
dig @8.8.8.8 $DOMAIN +short

echo "Cloudflare DNS (1.1.1.1):"
dig @1.1.1.1 $DOMAIN +short

echo "Quad9 DNS (9.9.9.9):"
dig @9.9.9.9 $DOMAIN +short

echo "Checking authoritative nameserver:"
dig NS $DOMAIN +short | head -1 | xargs -I{} dig @{} $DOMAIN +short

echo "Online tools:"
echo "https://dnschecker.org/#A/$DOMAIN"
echo "https://whatsmydns.net/#A/$DOMAIN"
```

### Step 3: SSL Verification

**Wait for DNS propagation (5-30 minutes typically), then:**

```bash
# Check SSL certificate
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -dates

# Check certificate issuer
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -issuer

# Verify HTTPS
curl -vI https://example.com 2>&1 | head -20
```

**Browser verification:**
- [ ] HTTPS shows green lock in browser
- [ ] Certificate is valid (not self-signed)
- [ ] Certificate issuer matches expected CA
- [ ] No mixed content warnings in console

### Step 4: HTTP to HTTPS Redirect

Verify HTTP redirects to HTTPS:
```bash
curl -I http://example.com
# Expected: 301 or 302 redirect to https://
```

### Step 5: WWW Redirect (if applicable)

```bash
# Check www redirects to non-www (or vice versa)
curl -I https://www.example.com
# Expected: 301 redirect to https://example.com

# Or for www-primary:
curl -I https://example.com
# Expected: 301 redirect to https://www.example.com
```

---

## Cache Purge Procedures

### Vercel

```bash
# Purge everything via CLI
vercel --prod --yes

# Purge specific path (not available via CLI, use dashboard)
# Settings → Data Cache → Purge
```

### Netlify

```bash
# Trigger new deploy
netlify deploy --prod

# Purge specific path
netlify api purgeCache --body '{"files":["/path/to/file"]}'
```

### Cloudflare

```bash
# Purge everything
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# Purge by URL
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://example.com/page1","https://example.com/page2"]}'
```

### Self-Hosted (nginx)

```bash
# If using FastCGI cache
sudo rm -rf /var/cache/nginx/fastcgi/*

# Reload nginx
sudo systemctl reload nginx

# If using proxy cache
sudo rm -rf /var/cache/nginx/proxy/*
sudo systemctl reload nginx
```

---

## Rollback Runbooks

### Vercel Rollback

```bash
# List deployments
vercel list

# View deployment history
vercel inspect [deployment-url]

# Rollback to previous deployment
vercel rollback

# Or promote specific deployment
vercel --prod [deployment-url]
```

**Via Dashboard:**
1. Go to project → Deployments
2. Find last successful deployment
3. Click "..." → "Promote to Production"

### Netlify Rollback

```bash
# List deploys
netlify deploy:list

# Rollback to specific deploy
netlify deploy:restore --id [deploy-id]

# Via dashboard:
# Deploys → Click "..." on desired deploy → "Restore to production"
```

### Cloudflare Pages Rollback

```bash
# Via dashboard:
# Pages project → View deployments → Rollback to specific deployment
```

### Self-Hosted Rollback (Git-Based)

```bash
# Option 1: Revert git commit
git revert [commit-hash]
git push origin main

# Rebuild and restart
npm run build
pm2 restart app

# Option 2: Checkout previous commit
git checkout [previous-commit]
npm run build
pm2 restart app
# Return to main branch when done debugging
git checkout main

# Option 3: Keep previous build
# Before deploy:
cp -r dist dist.backup-$(date +%Y%m%d)

# Rollback:
rm -rf dist
mv dist.backup-YYYYMMDD dist
pm2 restart app
```

### Database Migration Rollback

If using migrations:
```bash
# Prisma
npx prisma migrate rollback

# Django
python manage.py migrate [app] [previous_migration]

# Rails
rails db:rollback
```

---

## 72-Hour Post-Launch Checklist

### First Hour

- [ ] **Uptime**: Verify site accessible from multiple locations
- [ ] **HTTP>S**: Confirm HTTPS redirect working
- [ ] **Certificates**: SSL valid and not expiring soon
- [ ] **Analytics**: GA4 tracking verified (real-time data visible)
- [ ] **Forms**: Test all form submissions
- [ ] **Error tracking**: Sentry or similar receiving errors
- [ ] **Core pages**: Manually test: Homepage, Contact, About, main CTAs
- [ ] **Mobile**: Test on iOS Safari and Android Chrome
- [ ] **Social**: Verify OG tags in Facebook Debugger and Twitter Card Validator

### First 6 Hours

- [ ] **DNS propagated**: Check multiple DNS resolvers
- [ ] **Search Console**: Submit sitemap to Google
- [ ] **Robots.txt**: Confirm `Disallow: /` removed (if applicable)
- [ ] **Error logs**: Check for 4xx/5xx errors in platform dashboard
- [ ] **Performance**: Run Lighthouse on production URL
- [ ] **Third-party integrations**: Test embeds, maps, forms, chat widgets

### First 24 Hours

- [ ] **Traffic monitoring**: Verify expected traffic in analytics
- [ ] **Error rate**: Confirm < 0.1% error rate
- [ ] **Performance**: Core Web Vitals within thresholds
- [ ] **Search Console**: No crawl errors
- [ ] **Mobile usability**: No issues in Search Console
- [ ] **Form submissions**: All received (check spam folder)
- [ ] **Email deliverability**: Contact forms reaching intended recipients

### First 72 Hours

- [ ] **Search indexing**: Site appearing in Google search
- [ ] **Performance stable**: Lighthouse scores maintained
- [ ] **Error tracking**: No recurring errors
- [ ] **Analytics trends**: Data flowing correctly
- [ ] **SSL renewal**: Certificate auto-renewal working (future check)
- [ ] **Documentation**: Update runbook with any lessons learned
- [ ] **Team handoff**: Notify support team of stability

---

## Incident Escalation Runbook

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| **P0 - Critical** | Site completely down, data loss | Immediate | DNS failure, SSL expired |
| **P1 - High** | Major functionality broken | 15 minutes | Forms not submitting, 500 errors |
| **P2 - Medium** | Degraded experience | 1 hour | Sluggish performance, broken images |
| **P3 - Low** | Minor issues | 24 hours | Typos, minor styling issues |

### P0 Procedure (Site Down)

**Diagnosis (5 minutes):**
```bash
# Check DNS
dig @8.8.8.8 example.com +short
# Expected: IP address

# Check site up
curl -I https://example.com
# Expected: HTTP 200

# Check SSL
openssl s_client -connect example.com:443 -servername example.com </dev/null
# Expected: certificate info

# Check platform status
# Vercel: https://www.vercel-status.com/
# Netlify: https://status.netlify.com/
# Cloudflare: https://www.cloudflarestatus.com/
```

**Immediate Actions:**
1. Document start time
2. Notify stakeholders (Slack/email)
3. Check platform status page
4. If DNS issue: Update DNS records
5. If SSL issue: See [TLS Provisioning](ops-tls-ssl-provisioning.md)
6. If platform issue: Monitor platform status, prepare rollback
7. If application error: Check logs, rollback if needed

**Resolution:**
```bash
# If rollback needed
vercel rollback  # or netlify deploy:restore
# Document what was done
# Notify stakeholders of resolution
```

### P1 Procedure (Broken Functionality)

**Diagnosis (15 minutes):**
```bash
# Check logs
vercel logs --prod  # Vercel
netlify logs:prod   # Netlify

# Check specific URLs
curl -I https://example.com/broken-page

# Check browser console for JS errors
# Open DevTools → Console
```

**Actions:**
1. Identify affected functionality
2. Check if issue is code, config, or infrastructure
3. Hotfix if possible
4. Rollback if hotfix not feasible
5. Document incident

### Communication Template

**Incident Start:**
```
🚨 INCIDENT: [Severity] - [Brief description]

Status: Investigating
Impact: [Who/what is affected]
Started: [Time]
Owner: [Person to contact]

Next update: [Time + 15min]

Link to runbook: [URL]
Link to logs: [URL]
```

**Incident Update:**
```
📊 UPDATE: [Status] - [Brief description]

Status: [Investigating/Identified/Monitoring/Resolved]
Root cause: [If known]
Current actions: [What's being done]
ETA: [If known]

Next update: [Time]
```

**Incident Resolution:**
```
✅ RESOLVED: [Brief description]

Duration: [Start time] to [End time]
Root cause: [Explanation]
Resolution: [What fixed it]
Prevention: [How to avoid in future]

Post-incident review scheduled: [Date]
```

---

## Maintenance Window Procedure

### Announcement Template

```
SCHEDULED MAINTENANCE

What: [Component being maintained]
When: [Date] [Start time] - [End time] UTC
Duration: [Expected duration]
Impact: [What users will experience]
Reason: [Why maintenance is needed]

No action required from users.
```

### Execution Steps

1. **30 minutes before:**
   - Post announcement
   - Enable maintenance mode (if applicable)
   - Verify monitoring alerts reduced

2. **During maintenance:**
   - Perform maintenance work
   - Monitor errors/logs
   - Update status page

3. **After completion:**
   - Verify site functionality
   - Run smoke tests
   - Disable maintenance mode
   - Verify monitoring back to normal

4. **Post-maintenance:**
   - Announce completion
   - Monitor for 1 hour
   - Document what was done

### Maintenance Mode (Optional)

**Simple HTML maintenance page:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Maintenance - Example.com</title>
    <meta name="robots" content="noindex">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 50px; }
    </style>
</head>
<body>
    <h1>We're currently performing maintenance</h1>
    <p>We'll be back shortly. Thank you for your patience.</p>
</body>
</html>
```

**nginx config:**
```nginx
server {
    listen 443 ssl;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    root /var/www/maintenance;
    index maintenance.html;
    
    location / {
        try_files /maintenance.html =503;
    }
}
```

---

## References

- [Ops: DNS & Domain Setup](ops-dns-domain-setup.md) — DNS cutover details
- [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md) — SSL verification
- [Launch Handoff Checklist](launch-handoff-checklist.md) — Pre-launch checks
- [Deployment Target Pack](deployment-target-pack.md) — Platform comparison
- [Ops: Troubleshooting Playbook](ops-troubleshooting-playbook.md) — Incident response