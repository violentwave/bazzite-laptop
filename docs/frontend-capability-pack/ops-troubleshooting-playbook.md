# Ops: Troubleshooting Playbook

Symptom→diagnosis→fix decision trees for common website deployment issues.

---

## Purpose

Rapid diagnosis and resolution for the most common failure modes in website deployment. Use this when something is broken and you need to find the fix quickly.

For DNS specifics, see [Ops: DNS & Domain Setup](ops-dns-domain-setup.md).
For SSL issues, see [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md).
For proxy config, see [Ops: Reverse Proxy Config](ops-reverse-proxy-config.md).

---

## Quick Diagnosis Flow

```
Issue?
  │
  ├── Site not loading at all ────────► DNS, SSL, Server
  │
  ├── Loading but errors ────────────► Application, Logs
  │
  ├── Loading but slow ──────────────► Performance, CDN
  │
  ├── Forms not working ─────────────► Integration, Backend
  │
  └── Analytics not tracking ────────► Analytics, Events
```

---

## Symptom: Site Not Resolving

**"I see 'This site can't be reached' or 'DNS_PROBE_POSSIBLE'"**

### Diagnosis Steps

```bash
# Step 1: Check DNS resolution
dig @8.8.8.8 example.com +short
# Expected: IP address
# If blank or error: DNS record missing or propagation pending

# Step 2: Check authoritative nameserver
dig NS example.com +short | head -1
# Then query that nameserver directly
dig @auth-nameserver.example.com example.com +short

# Step 3: Check if domain expired
whois example.com | grep -i "expiry\|status"

# Step 4: Check multiple resolvers (propagation issue)
dig @8.8.8.8 example.com +short   # Google
dig @1.1.1.1 example.com +short   # Cloudflare
dig @9.9.9.9 example.com +short   # Quad9
```

### Fix by Cause

| Finding | Cause | Fix |
|---------|-------|-----|
| No A/CNAME record | Records not added | Add DNS records in registrar/platform |
| Different IP on different resolvers | DNS propagation pending | Wait TTL (up to 48h), use dnschecker.org |
| Nameserver mismatch | Wrong nameservers configured | Update nameservers at registrar |
| Domain status: clientHold/renewalRequired | Domain expired | Renew domain at registrar |
| SERVFAIL | DNSSEC misconfiguration or DS record conflict | Disable DNSSEC temporarily, check DS records |

---

## Symptom: SSL Certificate Error

**"Your connection is not private" / "Certificate not valid" / NET::ERR_CERT_...**

### Diagnosis Steps

```bash
# Step 1: Check certificate validity
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -dates -issuer

# Step 2: Check certificate chain
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"

# Step 3: Check if certificate matches domain
echo | openssl s_client -connect example.com:443 -servername example.com 2>&1 | openssl x509 -noout -subject -issuer

# Step 4: Check for mixed content (https site with http resources)
curl -I https://example.com 2>&1 | head -20
```

### Fix by Cause

| Finding | Cause | Fix |
|---------|-------|-----|
| "certificate is not yet valid" or "expired" | Certificate expired | For Let's Encrypt: `sudo certbot renew`<br>For platforms: Usually auto - contact support |
| "certificate is not valid for example.com" | Domain mismatch (www vs non-www) | Re-provision certificate with correct domains<br>`certbot --nginx -d example.com -d www.example.com` |
| "unable to get local issuer certificate" | Incomplete certificate chain | Use `fullchain.pem` not `cert.pem`<br>Re-download/reinstall certificate |
| "self-signed certificate" | Development cert or missing issuer | For production: use Let's Encrypt or platform-managed TLS |
| Mixed content errors in console | HTTP resources on HTTPS page | Update all asset URLs to https:// or protocol-relative // |

### Platform-Specific Fixes

**Vercel/Netlify:**
- Usually automatic — if certificate stuck in "pending" 30+ minutes:
  1. Remove domain and re-add
  2. Trigger manual verification in dashboard
  3. Check `.well-known/acme-challenge/` accessibility

**Cloudflare:**
- Set SSL/TLS mode to "Full (Strict)"
- If using origin certificate: ensure correct cert/key on origin
- Disable "Always Use HTTPS" temporarily during provisioning

**Self-hosted:**
- Run `certbot renew --dry-run` to test renewal
- Check certificate locations in nginx/Caddy config
- Verify port 80 accessible for HTTP-01 challenge

---

## Symptom: 502/503/504 Errors

**"502 Bad Gateway" / "503 Service Unavailable" / "504 Gateway Timeout"**

### Diagnosis Steps

```bash
# Step 1: Is the backend running?
curl http://localhost:3000
# Expected: 200 OK

# Step 2: Check backend process
pm2 list          # If using PM2
systemctl status app  # Systemd service
ps aux | grep node    # Generic check

# Step 3: Check reverse proxy logs
sudo tail -f /var/log/nginx/error.log
sudo journalctl -u caddy -f  # Caddy logs

# Step 4: Check platform logs
vercel logs --prod   # Vercel
netlify logs:prod    # Netlify
# Cloudflare: dashboard → Analytics → Logs
```

### Fix by Cause

| Error Code | Common Causes | Fix |
|------------|---------------|-----|
| **502 Bad Gateway** | Backend not running, wrong upstream port | Start backend: `pm2 start app` or `systemctl start app`<br>Check port matches proxy_pass |
| **503 Service Unavailable** | Backend overloaded, maintenance mode, no healthy backends | Scale horizontally, fix memory leaks<br>Disable maintenance mode |
| **504 Gateway Timeout** | Backend too slow, database lock, external API timeout | Increase timeout in proxy config<br>Optimize slow queries<br>Add timeout handling in code |

### Platform-Specific

**Vercel:**
- Check deployment logs for build/runtime errors
- Increase function timeout in `vercel.json`:
  ```json
  { "functions": { "api/**/*.js": { "maxDuration": 30 } } }
  ```

**Netlify:**
- Check function logs in dashboard
- Increase function timeout (max 26s on free tier)

**Self-hosted:**

nginx timeout increase:
```nginx
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

Caddy timeout:
```caddyfile
reverse_proxy localhost:3000 {
    transport http {
        read_timeout 60s
        write_timeout 60s
    }
}
```

---

## Symptom: Slow Page Load

**"Site loads slowly" / Lighthouse performance score < 90**

### Diagnosis Steps

```bash
# Step 1: Lighthouse
lighthouse https://example.com --view

# Step 2: Check server response time (TTFB)
curl -w "TTFB: %{time_starttransfer}s\n" -o /dev/null -s https://example.com
# Target: < 0.5s

# Step 3: Check network timing
curl -w "DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" -o /dev/null -s https://example.com

# Step 4: Analyze bundle size
npm run build
du -sh dist/  # Or .next/, build/

# Step 5: Check database queries (if applicable)
# Look for slow query logs
```

### Fix by Cause

| Finding | Cause | Fix |
|---------|-------|-----|
| TTFB > 500ms + high server CPU | Backend code slow | Profile code, optimize queries<br>Add caching (Redis, LRU) |
| Large JS bundle > 300KB | No code splitting | Add route-based code splitting<br>Lazy load components |
| Images not optimized | Missing compression | Convert to WebP/AVIF<br>Use `loading="lazy"`<br>Serve responsive sizes |
| No caching headers | Assets re-downloaded | Add cache headers<br>Use CDN |
| External scripts | Blocking render | Use `async` or `defer`<br>Load on interaction |
| No CDN | Origin serves all | Enable platform CDN<br>Add Cloudflare in front |

### Performance Quick Wins

```bash
# Enable compression in Caddy
encode gzip zstd

# Enable compression in nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# Add caching headers (Caddy)
@static {
    path *.js *.css *.png *.jpg *.jpeg *.gif *.ico *.svg *.woff *.woff2
}
header @static Cache-Control "public, max-age=31536000, immutable"
```

---

## Symptom: Forms Not Submitting

**"Contact form/spam protection/signup not working"**

### Diagnosis Steps

```bash
# Step 1: Check form action URL
curl -I https://api.example.com/contact

# Step 2: Test form submission manually
curl -X POST https://api.example.com/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","message":"Test"}'

# Step 3: Check for CORS errors
# Open browser DevTools → Console → Look for CORS errors

# Step 4: Check spam protection
# If using reCAPTCHA, hCaptcha, honeypot — test with valid token
```

### Fix by Cause

| Finding | Cause | Fix |
|---------|-------|-----|
| 404 on form action | Wrong endpoint URL | Fix action URL in form |
| CORS error | API blocking cross-origin requests | Add CORS headers on backend<br>`Access-Control-Allow-Origin: https://example.com` |
| 4xx validation error | Missing required fields | Check API expects<br>Add validation feedback |
| reCAPTCHA/hCaptcha failure | Missing/invalid token | Verify site key matches domain<br>Ensure token submitted with form |
| Netlify Forms not receiving | Missing Netlify attributes | Add `data-netlify="true"`<br>Add hidden form-name input |
| Emails not sending | Email service fails | Check SendGrid/Mailgun logs<br>Verify API keys |
| Spam submissions | No spam protection | Add honeypot field<br>Add CAPTCHA<br>Rate limit submissions |

### Netlify Forms Config

```html
<form name="contact" method="POST" data-netlify="true">
  <input type="hidden" name="form-name" value="contact" />
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <textarea name="message"></textarea>
  <button type="submit">Send</button>
</form>
```

---

## Symptom: Analytics Not Tracking

**"GA4 shows zero events" / "No data in analytics"**

### Diagnosis Steps

```bash
# Step 1: Check GA4 script present
curl -s https://example.com | grep -i "gtag\|GA_MEASUREMENT_ID"

# Step 2: Check measurement ID
curl -s https://example.com | grep -o "G-[A-Z0-9]*"

# Step 3: Test event firing (browser)
# Open DevTools → Console
# window.dataLayer should exist if GTM installed
# gtag() should be defined if GA4 installed

# Step 4: Real-time verification
# Open GA4 → Reports → Realtime
# Visit site, verify session appears
```

### Fix by Cause

| Finding | Cause | Fix |
|---------|-------|-----|
| No gtag.js included | Missing GA4 script | Add GA4 script in `<head>` |
| Wrong measurement ID | ID doesn't match GA4 property | Verify ID in GA4 Admin → Data Streams |
| gtag() not defined | Script not loaded or blocked | Check CSP allows Google domains<br>Check ad blocker not blocking |
| Events not firing | Event code not called | Add `gtag('event', 'event_name')` calls |
| No real-time data | GA4 not receiving hits | Check network tab for `google-analytics.com/g/collect` requests |
| Self-referral traffic | Missing referral exclusion | Add domain to referral exclusion list in GA4 |

### GA4 Debug Mode

```javascript
// Enable debug mode in browser console
window.gtag('config', 'G-XXXXXXXXXX', { debug_mode: true });
// Then check GA4 DebugView (Admin → DebugView)
```

---

## Symptom: Build Failures

**"Deployment failed" / "Build error" / "Command exited with code 1"**

### Diagnosis Steps

```bash
# Step 1: Reproduce locally
npm run build

# Step 2: Check Node version
node -v
# Compare with platform: Vercel uses Node 18.x by default

# Step 3: Check dependencies
npm list
npm outdated

# Step 4: Check for env var issues
# Compare local .env with platform env vars

# Step 5: Platform-specific logs
vercel logs --prod    # Vercel
netlify deploy:日志   # Netlify (check deploy log in dashboard)
```

### Fix by Cause

| Finding | Cause | Fix |
|---------|-------|-----|
| TypeScript errors | Type mismatches | Fix TypeScript errors<br>Or add `// @ts-ignore` (not recommended) |
| Module not found | Missing dependency | `npm install <package>`<br>Add to package.json |
| Out of memory | Build too large for platform | Increase memory limit<br>Split build into parts<br>Optimize bundle |
| Node version mismatch | Local vs platform Node version | Set Node version in platform config<br>Vercel: `"engines": { "node": "20.x" }`<br>Netlify: `NODE_VERSION` env var |
| Env var missing | Required env var not set | Add in platform dashboard<br>Ensure `NEXT_PUBLIC_` prefix for client vars |
| ESM/CJS mismatch | Import style conflict | Use `.mjs` / `.cjs` extensions appropriately<br>Add `"type": "module"` to package.json |

### Build Timeout Fixes

```javascript
// vercel.json
{
  "functions": {
    "api/**/*.js": {
      "memory": 1024,
      "maxDuration": 30
    }
  }
}

// netlify.toml
[build]
  command = "npm run build"
  environment = { NODE_VERSION = "20" }
```

---

## Platform-Specific Error Reference

### Vercel

| Error | Cause | Fix |
|-------|-------|-----|
| `VERCEL_BUILDER_NOT_FOUND` | Framework not detected | Add `"framework": "nextjs"` to vercel.json |
| `FUNCTION_INVOCATION_TIMEOUT` | Function > timeout limit | Increase maxDuration in vercel.json |
| `EDGE_FUNCTION_INVOCATION_TIMEOUT` | Edge fn > 30s | Reduce logic, use standard function |
| `INVALID_CONFIG` | vercel.json invalid | Validate JSON, check docs for valid keys |
| `DEPLOYMENT_NOT_FOUND` | Deployment deleted | Re-deploy |

### Netlify

| Error | Cause | Fix |
|-------|-------|-----|
| `Build script returned non-zero exit code` | Build command failed | Check build output, fix errors |
| `Page not found` | No matching route | Add `public/_redirects` for SPA |
| `Function invocation failed` | Function threw error | Check function logs in dashboard |
| `Deploy timed out` | Build > 15 min | Optimize build, reduce dependencies |
| `Invalid netlify.toml` | Config syntax error | Validate TOML, check docs |

### Cloudflare Pages

| Error | Cause | Fix |
|-------|-------|-----|
| `Functions restart limit exceeded` | Too many restarts | Fix function errors |
| `KV binding not found` | KV namespace missing | Add in dashboard → Functions → KV namespace |
| `Worker exceeded CPU limit` | Worker too slow | Optimize code |
| `Invalid wrangler.toml` | Config syntax error | Validate TOML |

---

## Decision Tree: What Tool to Use

```
What type of issue?
│
├── DNS/Domain → dig, whois, DNSChecker.org
├── SSL/TLS → openssl, browser DevTools
├── Server/Proxy → nginx logs, Caddy logs, pm2 logs
├── Application → platform logs, Sentry, application logs
├── Performance → Lighthouse, WebPageTest, curl -w
├── Forms/Integrations → network tab, backend logs
└── Analytics → GA4 DebugView, network tab
```

---

## Contact Support Escalation

| Platform | Support Channel | Response Time |
|----------|-----------------|---------------|
| Vercel | support@vercel.com / Dashboard | 24-48h (Pro), faster (Enterprise) |
| Netlify | support@netlify.com / Dashboard | 24-48h (Pro), faster (Enterprise) |
| Cloudflare | Community forum, then paid support | Forum: community, Paid: Priority |
| Self-hosted | Internal team | Per SLA |

---

## References

- [Ops: DNS & Domain Setup](ops-dns-domain-setup.md) — DNS diagnosis
- [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md) — Certificate issues
- [Ops: Reverse Proxy Config](ops-reverse-proxy-config.md) — nginx/Caddy config
- [Ops: Launch Procedures](ops-launch-procedures.md) — Rollback procedures
- [Launch Handoff Checklist](launch-handoff-checklist.md) — Pre-launch verification