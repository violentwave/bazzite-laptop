# Ops: TLS/SSL Provisioning

Certificate provisioning and management for HTTPS deployments.

---

## Purpose

This runbook covers TLS certificate setup across platforms, Let's Encrypt automation, Caddy auto-TLS, and common certificate issues. For DNS configuration, see [Ops: DNS & Domain Setup](ops-dns-domain-setup.md).

---

## Platform-Managed TLS

### Vercel (Automatic)

Vercel provisions TLS certificates automatically when you add a domain:

1. Add domain in **Settings** → **Domains**
2. Configure DNS records (see [DNS Setup](ops-dns-domain-setup.md))
3. Certificate provisions automatically within minutes
4. Verify by visiting `https://yourdomain.com`

**Certificate renewal**: Automatic (handled by Vercel)

**Verification commands:**
```bash
# Check certificate
curl -vI https://example.com 2>&1 | grep -E "SSL|certificate|issuer"

# Detailed TLS check
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -dates
```

### Netlify (Automatic)

Netlify provisions certificates automatically for custom domains:

1. Add domain in **Site settings** → **Domain management**
2. Configure DNS records
3. Enable "HTTPS" (automatic)
4. Certificate provisions automatically

**Certificate renewal**: Automatic

**Force HTTPS**: Enable in **Domain management** → HTTPS

### Cloudflare Pages (Automatic with Cloudflare DNS)

When using Cloudflare DNS + Pages:

1. Set SSL/TLS mode to **Full (Strict)**
2. Certificates provision automatically
3. Edge certificates managed by Cloudflare

**Self-hosted with Cloudflare proxy:**
- Use Cloudflare Origin Certificates (15-year validity)
- See "Cloudflare Origin Certificates" section below

---

## Let's Encrypt with Certbot

For self-hosted servers without platform TLS.

### Install Certbot

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-nginx

# For nginx
sudo apt install python3-certbot-nginx

# For Apache
sudo apt install python3-certbot-apache

# macOS
brew install certbot
```

### Obtain Certificate (nginx)

```bash
# Interactive (Certbot modifies nginx config)
sudo certbot --nginx -d example.com -d www.example.com

# Certificate-only (manual config)
sudo certbot certonly --nginx -d example.com -d www.example.com

# Wildcard certificate (requires DNS challenge)
sudo certbot certonly --manual --preferred-challenges dns \
  -d '*.example.com' -d example.com
```

### Obtain Certificate (Apache)

```bash
sudo certbot --apache -d example.com -d www.example.com
```

### Certificate Locations

```
/etc/letsencrypt/live/example.com/
├── cert.pem        # Domain certificate
├── chain.pem       # CA chain
├── fullchain.pem   # Full chain (cert + chain)
└── privkey.pem     # Private key
```

### Auto-Renewal

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Enable systemd timer (most systems have this auto-configured)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Check timer status
sudo systemctl status certbot.timer

# Manual renewal
sudo certbot renew
```

**Renewal hooks** for nginx:
```bash
# /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh
#!/bin/bash
systemctl reload nginx

# Make executable
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh
```

---

## Caddy Auto-TLS

Caddy provisions and renews certificates automatically. No Certbot needed.

### Basic Configuration

```caddyfile
example.com {
    reverse_proxy localhost:3000
    # Caddy automatically provisions TLS certificate
}
```

That's it. Caddy handles:
- Certificate provisioning via Let's Encrypt/ZeroSSL
- Automatic renewal (30 days before expiry)
- HTTP-to-HTTPS redirect
- TLS 1.2+ by default

### Multiple Domains

```caddyfile
example.com, www.example.com {
    reverse_proxy localhost:3000
}

api.example.com {
    reverse_proxy localhost:4000
}
```

### Wildcard Certificates (DNS Challenge Required)

```caddyfile
*.example.com {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy localhost:3000
}
```

Install Cloudflare DNS provider:
```bash
caddy add-package github.com/caddy-dns/cloudflare
```

### On-Demand TLS (Multi-Tenant)

```caddyfile
{
    on_demand_tls {
        ask http://localhost:5555/allowed
        interval 2m
        burst 5
    }
}

https:// {
    tls {
        on_demand
    }
    reverse_proxy localhost:3000
}
```

The `ask` endpoint validates if domain is allowed before provisioning.

### Manual Certificate (Bring Your Own)

```caddyfile
example.com {
    tls /etc/ssl/certs/example.com.crt /etc/ssl/private/example.com.key
    reverse_proxy localhost:3000
}
```

---

## Cloudflare Origin Certificates

For self-hosted origins behind Cloudflare:

### Generate Certificate

1. Log into Cloudflare Dashboard
2. Go to **SSL/TLS** → **Origin Server**
3. Click **Create Certificate**
4. Select hostnames: `example.com`, `*.example.com`
5. Certificate validity: 15 years (recommended)
6. Key format: PEM (for nginx/Apache)
7. Click **Create**

### Install on Server

Save certificate and key:
```bash
# Create directory
sudo mkdir -p /etc/ssl/cloudflare

# Save certificate
sudo nano /etc/ssl/cloudflare/origin.pem
# Paste certificate content

# Save private key
sudo nano /etc/ssl/cloudflare/origin-key.pem
# Paste key content

# Set permissions
sudo chmod 600 /etc/ssl/cloudflare/origin-key.pem
```

### Configure nginx

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /etc/ssl/cloudflare/origin.pem;
    ssl_certificate_key /etc/ssl/cloudflare/origin-key.pem;

    # Recommended SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Cloudflare SSL Mode

Set SSL/TLS mode to **Full (Strict)**:
- **Off**: No encryption between Cloudflare and origin
- **Flexible**: Cloudflare→origin can be HTTP (not recommended)
- **Full**: Cloudflare→origin encrypted, but certificate not validated
- **Full (Strict)**: Certificate must be valid or Cloudflare Origin Certificate

---

## TLS Configuration Best Practices

### HSTS (HTTP Strict Transport Security)

**Header configuration:**
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

**For platform hosting:**

Vercel: HSTS is automatic.

Netlify: Add to `netlify.toml`:
```toml
[[headers]]
  for = "/*"
  [headers.values]
    Strict-Transport-Security = "max-age=31536000; includeSubDomains; preload"
```

Cloudflare: Enable in **SSL/TLS** → **Edge Certificates** → **HSTS**

### Security Headers

```nginx
# Recommended security headers
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

### TLS Protocol Version

```nginx
# Modern TLS only (TLS 1.2 and 1.3)
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
```

### OCSP Stapling

```nginx
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

---

## Mixed Content Resolution

### Detection

**Browser console:**
- Look for "Mixed Content" errors in DevTools → Console
- Blocked resources show "blocked:mixed-content"

**Command line check:**
```bash
# Find HTTP URLs in codebase
grep -r "http://" --include="*.js" --include="*.jsx" --include="*.ts" --include="*.tsx" --include="*.html" --include="*.css" ./src
```

### Fix

1. **Replace HTTP with HTTPS:**
   ```bash
   # Protocol-relative URLs (legacy)
   <script src="//example.com/script.js">
   
   # HTTPS URLs (recommended)
   <script src="https://example.com/script.js">
   ```

2. **Use environment variables for API URLs:**
   ```javascript
   const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://api.example.com';
   ```

3. **Content Security Policy:**
   ```nginx
   add_header Content-Security-Policy "upgrade-insecure-requests" always;
   ```

4. **Platform setting (if available):**
   - Enable "Force HTTPS" to redirect HTTP to HTTPS

---

## Certificate Troubleshooting

### Certificate Chain Errors

**Symptom:** Browser shows "Your connection is not fully secure" or "Certificate not trusted"

**Diagnosis:**
```bash
# Check certificate chain
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -issuer

# Expected: issuer points to trusted CA
```

**Fix:**
- Ensure full chain is served (`fullchain.pem` not `cert.pem`)
- For Let's Encrypt: chain included by default
- For Cloudflare Origin: bundle included

### SNI Issues

**Symptom:** Works in browser but fails for some clients/crawlers

**Diagnosis:**
```bash
# Test with explicit SNI
openssl s_client -connect example.com:443 -servername example.com </dev/null

# Test without SNI (older clients)
openssl s_client -connect example.com:443 </dev/null
```

**Fix:**
- Ensure server supports SNI (nginx, Caddy, Apache all support by default)
- All modern servers support SNI

### Certificate Expired

**Symptom:** Browser shows "Your connection is not secure" / certificate expired

**Diagnosis:**
```bash
# Check expiry
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -dates

# Check renewal status
sudo certbot certificates  # For Let's Encrypt
```

**Fix:**

For Let's Encrypt:
```bash
sudo certbot renew
sudo systemctl reload nginx  # or apache
```

For Caddy: Automatic renewal — check logs for failures:
```bash
journalctl -u caddy -f
```

For platform hosting: Usually automatic — contact support if persisted >24h.

### Certificate Not Matching Domain

**Symptom:** "Certificate valid for www.example.com, but not example.com"

**Diagnosis:**
```bash
# Check certificate SAN (Subject Alternative Names)
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"
```

**Fix:**
- Provision certificate for all needed domains:
  ```bash
  sudo certbot --nginx -d example.com -d www.example.com
  ```
- For wildcards, include both apex and wildcard:
  ```bash
  sudo certbot certonly --manual --preferred-challenges dns \
    -d '*.example.com' -d example.com
  ```

### Rate Limits (Let's Encrypt)

**Symptom:** "Too many certificates already issued for: example.com"

**Current limits:**
- 50 certificates per registered domain per week
- 5 duplicate certificates per week
- 300 failures per 3 hours (account-wide)

**Fix:**
- Use staging environment for testing: `--test-cert`
- Wait 7 days for rate reset
- Use wildcard certificate to cover multiple subdomains
- Consider ZeroSSL as alternative CA

---

## Certificate Renewal Automation

### Certbot (Let's Encrypt)

**Systemd timer (recommended):**
```bash
# Verify timer exists
systemctl list-timers | grep certbot

# Check timer details
systemctl status certbot.timer

# Manual renewal test
sudo certbot renew --dry-run
```

**Cron (alternative):**
```cron
# /etc/cron.d/certbot-renewal
0 3 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
```

### Caddy (Built-in)

Caddy renews automatically 30 days before expiry. Monitor with:
```bash
journalctl -u caddy -f | grep -i renew
```

### Platform Hosting

All major platforms (Vercel, Netlify, Cloudflare) handle renewal automatically:

| Platform | Renewal Method | Action Required |
|----------|----------------|-----------------|
| Vercel | Automatic | None |
| Netlify | Automatic | None |
| Cloudflare | Automatic (if proxied) | None |
| Self-hosted | Certbot or Caddy | Configure automation |

---

## References

- [Ops: DNS & Domain Setup](ops-dns-domain-setup.md) — DNS configuration
- [Ops: Reverse Proxy Config](ops-reverse-proxy-config.md) — nginx/Caddy configuration
- [Ops: Launch Procedures](ops-launch-procedures.md) — SSL check for launch
- [Deployment Target Pack](deployment-target-pack.md) — Platform comparison
- [Launch Handoff Checklist](launch-handoff-checklist.md) — SSL verification