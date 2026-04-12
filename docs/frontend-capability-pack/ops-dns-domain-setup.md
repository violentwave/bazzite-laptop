# Ops: DNS & Domain Setup

Practical DNS configuration and troubleshooting for website deployment.

---

## Purpose

This runbook covers DNS record setup per platform, propagation diagnosis, domain transfers, and common failure modes. It complements the platform comparison in [Deployment Target Pack](deployment-target-pack.md).

For certificate provisioning, see [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md).

---

## Per-Platform DNS Record Tables

### Vercel

| Record Type | Name | Value | Notes |
|-------------|------|-------|-------|
| A | `@` | `76.76.21.21` | Apex domain |
| CNAME | `www` | `cname.vercel-dns.com` | www subdomain |
| CNAME | `subdomain` | `cname.vercel-dns.com` | Custom subdomains |

**Alternative (nameserver method for wildcards):**
- Change nameservers to Vercel-provided NS records
- Required for `*.example.com` wildcard domains

**Vercel DNS Verification:**
```bash
dig @8.8.8.8 example.com +short
# Expected: 76.76.21.21

dig @8.8.8.8 www.example.com +short
# Expected: cname.vercel-dns.com
```

### Netlify

| Record Type | Name | Value | Notes |
|-------------|------|-------|-------|
| A | `@` | `75.2.60.5` | Apex (Netlify load balancer) |
| CNAME | `www` | `[site-name].netlify.app` | www subdomain |
| CNAME | `subdomain` | `[site-name].netlify.app` | Custom subdomains |

**Netlify DNS Verification:**
```bash
dig @8.8.8.8 example.com +short
# Expected: 75.2.60.5

dig @8.8.8.8 www.example.com +short
# Expected: [site-name].netlify.app
```

### Cloudflare Pages

| Record Type | Name | Value | Notes |
|-------------|------|-------|-------|
| CNAME | `@` | `[site-name].pages.dev` | Apex (via CNAME flattening) |
| CNAME | `www` | `[site-name].pages.dev` | www subdomain |

**Cloudflare-Specific Configuration:**
1. **SSL/TLS Mode**: Set to "Full (Strict)" in SSL/TLS → Edge Certificates
2. **Always Use HTTPS**: Enable in SSL/TLS → Edge Certificates
3. **Auto Minify**: Optionally enable in Speed → Optimization
4. **Page Rules** for ACME challenges:
   - Pattern: `example.com/.well-known/*`
   - Setting: SSL → Off (temporarily during certificate provisioning)

**Cloudflare DNS Verification:**
```bash
dig @1.1.1.1 example.com +short
# Expected: [site-name].pages.dev (CNAME flattened to IP)
```

### Self-Hosted (Caddy/nginx)

| Record Type | Name | Value | Notes |
|-------------|------|-------|-------|
| A | `@` | `YOUR_SERVER_IP` | Apex pointing to server |
| A | `www` | `YOUR_SERVER_IP` | www subdomain |
| A | `subdomain` | `YOUR_SERVER_IP` | Additional subdomains |

**DNS Verification:**
```bash
dig @8.8.8.8 example.com +short
# Expected: YOUR_SERVER_IP
```

---

## DNS Propagation Diagnosis

### Check Propagation Globally

```bash
# Using dnschecker.org (browser)
https://dnschecker.org/#A/example.com

# Using command line
dig @8.8.8.8 example.com          # Google DNS
dig @1.1.1.1 example.com          # Cloudflare DNS
dig @9.9.9.9 example.com          # Quad9 DNS
dig NS example.com +short        # Get authoritative nameservers
dig @ns1.example.com example.com # Query authoritative directly
```

### Common Propagation Issues

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Works on 8.8.8.8 but not 1.1.1.1 | DNS resolvers caching old values | Wait for TTL (up to 48h), flush resolver cache |
| SERVFAIL on some resolvers | DNSSEC misconfiguration, DS record conflict | Check DS records at registrar, disable DNSSEC temporarily |
| No records returned | Records not added correctly | Re-add records in DNS dashboard |
| Wrong IP returned | Conflicting A/CNAME records | Remove old records, ensure only one A or CNAME per name |

### Flush DNS Cache

```bash
# macOS
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder

# Linux (systemd-resolved)
sudo systemd-resolve --flush-caches

# Linux (nscd)
sudo nscd -i hosts

# Windows
ipconfig /flushdns
```

---

## Cloudflare-Specific Setup

### Full (Strict) SSL Configuration

Required when proxying through Cloudflare to an HTTPS origin:

1. **SSL/TLS** → **Edge Certificates**
2. Set mode to **Full (Strict)**
3. Ensure origin server has valid certificate (Let's Encrypt or Cloudflare Origin Certificate)

### Origin Certificate Generation

For self-hosted origins without public certificates:

1. **SSL/TLS** → **Origin Server**
2. Create Certificate
3. Select hostnames: `example.com`, `*.example.com`
4. Certificate Validity: 15 years
5. Install on origin server:
   - Save certificate to `/etc/ssl/cloudflare-origin.pem`
   - Save key to `/etc/ssl/cloudflare-origin-key.pem`
   - Configure web server to use these files

### Page Rule for ACME Challenges (Vercel/Netlify)

When using Cloudflare DNS with Vercel/Netlify hosting:

**Create Page Rule:**
- Pattern: `example.com/.well-known/acme-challenge/*`
- Setting: SSL → Off
- This allows Let's Encrypt to verify domain ownership

**Alternative: Use CNAME method instead of A records** (some platforms handle ACME automatically).

---

## Domain Transfer Between Platforms

### From Vercel to Netlify

1. Remove domain from Vercel project settings
2. Export any DNS records from Vercel (if using Vercel DNS)
3. Add domain to Netlify project
4. Update DNS records at registrar to point to Netlify
5. Wait for DNS propagation (up to 48h)
6. Verify SSL certificate issuance

### From Netlify to Cloudflare Pages

1. Remove domain from Netlify
2. Add domain to Cloudflare Pages project
3. Update DNS records Cloudflare dashboard
4. Set SSL mode to Full (Strict)
5. Verify certificate validation

### From Any Platform to Self-Hosted

1. Deploy application to self-hosted server
2. Configure reverse proxy (see [Reverse Proxy Config](ops-reverse-proxy-config.md))
3. Point DNS A records to server IP
4. Provision SSL certificate (Let's Encrypt or Cloudflare Origin)
5. Verify HTTPS working before disabling platform deployment

---

## WWW Redirect Configuration

### Vercel

Vercel automatically redirects `www` to non-`www` (or vice versa) based on the primary domain setting. Configure in **Settings** → **Domains**.

### Netlify

Add to `netlify.toml`:
```toml
[[redirects]]
  from = "https://www.example.com/*"
  to = "https://example.com/:splat"
  status = 301
  force = true
```

### Cloudflare Pages

Create Page Rule:
- Pattern: `www.example.com/*`
- Setting: Forwarding URL (301 - Permanent Redirect)
- Destination: `https://example.com/$1`

### Self-Hosted (Caddy)

Automatic with default config:
```caddyfile
example.com, www.example.com {
    redir https://example.com{uri}
    # or keep www:
    # redir https://www.example.com{uri}
}
```

### Self-Hosted (nginx)

```nginx
server {
    server_name www.example.com;
    return 301 https://example.com$request_uri;
}

server {
    server_name example.com;
    # main config here
}
```

---

## Subdomain and Wildcard Setup

### Wildcard Domain (e.g., `*.example.com`)

**Vercel:**
- Must use nameserver method (cannot use A/CNAME)
- Add `*.example.com` to project domains
- Vercel handles ACME challenges automatically

**Netlify:**
- Add `*.example.com` to project domains
- Requires DNS provider that supports wildcard CNAME
- May need manual certificate provisioning

**Cloudflare Pages:**
- Wildcard domains supported natively
- Add `*.example.com` in project settings
- Certificates provisioned automatically

**Self-Hosted:**
```caddyfile
*.example.com {
    # Certificate must cover wildcard (dns-01 challenge required)
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy localhost:3000
}
```

For nginx with wildcard certificates:
```bash
# Certbot wildcard certificate
sudo certbot certonly --manual --preferred-challenges dns \
  -d '*.example.com' -d example.com
```

---

## Common Failure Modes

### "Invalid Configuration" on Platform Dashboard

| Cause | Diagnosis | Fix |
|-------|-----------|-----|
| Wrong DNS records | Check record type matches platform | Use correct A or CNAME |
| Conflicting records | Multiple A/CNAME for same name | Delete old records |
| DNS not propagated | Check multiple resolvers | Wait TTL, flush cache |
| SSL certificate pending | Check certificate status in dashboard | Trigger re-verification |

### Domain Stuck in "Pending" Status

1. Verify DNS records are correct
2. Wait 5-10 minutes for propagation check
3. If still pending:
   - Remove and re-add domain
   - Trigger manual verification in platform dashboard
   - Check DNSSEC is not blocking (temporarily disable)

### SSL Certificate Errors

See [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md) for certificate-specific troubleshooting.

### Mixed Content (HTTPS with HTTP assets)

Browser blocks HTTP resources on HTTPS pages:

**Detection:**
- Browser console shows "Mixed Content" errors
- Resources load on HTTP, blocked on HTTPS

**Fix:**
1. Update all asset URLs to use `https://` or protocol-relative `//`
2. Check hardcoded URLs in:
   - `<link>` CSS stylesheets
   - `<script>` JavaScript sources
   - `<img>` image sources
   - `<iframe>` embeds
   - API calls in JavaScript
3. Enable HTTPS-only in platform settings

---

## DNS Record Verification Commands

### Quick Verification Script

```bash
#!/bin/bash
DOMAIN="example.com"

echo "=== DNS Check for $DOMAIN ==="

echo -e "\n--- A Record ---"
dig +short A $DOMAIN

echo -e "\n--- WWW CNAME ---"
dig +short CNAME www.$DOMAIN

echo -e "\n--- Nameservers ---"
dig +short NS $DOMAIN

echo -e "\n--- MX Records ---"
dig +short MX $DOMAIN

echo -e "\n--- TXT Records ---"
dig +short TXT $DOMAIN

echo -e "\n--- DNSSEC ---"
dig +short DNSKEY $DOMAIN
dig +short DS $DOMAIN

echo -e "\n=== Global Propagation ==="
echo "Check: https://dnschecker.org/#A/$DOMAIN"
```

### Platform-Specific DNS Verification

**Vercel:**
```bash
dig +short A example.com
# Expected: 76.76.21.21

dig +short CNAME www.example.com
# Expected: cname.vercel-dns.com
```

**Netlify:**
```bash
dig +short A example.com
# Expected: 75.2.60.5

dig +short CNAME www.example.com
# Expected: [site-name].netlify.app
```

**Cloudflare:**
```bash
dig +short A example.com @1.1.1.1
# Expected: Cloudflare IPs (flattened CNAME)

# Check if proxied
dig +short A example.com @8.8.8.8
dig +short A example.com @1.1.1.1
# Different IPs = Cloudflare proxy enabled
```

---

## References

- [Deployment Target Pack](deployment-target-pack.md) — Platform comparison
- [Environment Config Checklist](environment-config-checklist.md) — Environment variables
- [Launch Handoff Checklist](launch-handoff-checklist.md) — DNS checks for launch
- [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md) — Certificate setup
- [Ops: Troubleshooting Playbook](ops-troubleshooting-playbook.md) — DNS failure diagnosis