# Ops: Reverse Proxy Config

Caddy and nginx configurations for self-hosted deployments.

---

## Purpose

This runbook covers reverse proxy setup for self-hosted websites. Use when deploying outside Vercel/Netlify/Cloudflare Pages. For platform-managed TLS, see [Deployment Target Pack](deployment-target-pack.md).

**Note:** Caddy is the primary recommendation (simpler, auto-TLS). nginx is the alternative for teams needing more control.

---

## When to Use Reverse Proxy

Self-hosted reverse proxies are needed when:
- Deploying to VPS, dedicated server, or on-premises
- Using Docker containers that need SSL termination
- Requirements prevent use of managed platforms
- Need fine-grained control over routing/headers

**When NOT needed:**
- Vercel, Netlify, Cloudflare Pages handle this automatically
- Static file hosting (S3 + CloudFront, etc.)
- Platform-as-a-Service (Heroku, Railway, Render)

---

## Caddy (Primary Recommendation)

### Why Caddy

- **Automatic HTTPS**: Certificates provisioned and renewed automatically
- **Simple config**: No complex SSL directives
- **HTTP/2 and HTTP/3**: Enabled by default
- **Memory efficient**: Single binary, small footprint
- **Production-ready**: Used by organizations worldwide

### Installation

```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# macOS
brew install caddy

# Docker
docker pull caddy:latest
```

### Basic Configuration

**File: `/etc/caddy/Caddyfile`**

```caddyfile
# Simple static site
example.com {
    root * /var/www/html
    file_server
    # TLS automatic (no config needed)
}

# Application with reverse proxy
example.com {
    reverse_proxy localhost:3000
    # TLS automatic (no config needed)
}

# Multiple domains
example.com, www.example.com {
    reverse_proxy localhost:3000
}

# API subdomain
api.example.com {
    reverse_proxy localhost:4000
}
```

### Application Proxy Examples

**Node.js/Next.js:**
```caddyfile
example.com {
    reverse_proxy localhost:3000
}
```

**Static files:**
```caddyfile
example.com {
    root * /var/www/public
    file_server
    encode gzip zstd
}
```

**Docker container:**
```caddyfile
example.com {
    reverse_proxy app:3000  # Docker network service name
}
```

**Multiple services:**
```caddyfile
example.com {
    # Serve static files
    root * /var/www/public
    
    # API routes
    handle_path /api/* {
        reverse_proxy localhost:4000
    }
    
    # Everything else
    handle {
        file_server
        encode gzip zstd
    }
}
```

### WebSocket Support

WebSocket support is automatic in Caddy:
```caddyfile
example.com {
    reverse_proxy localhost:3000
    # WebSocket upgrade handled automatically
}
```

### Compression

```caddyfile
example.com {
    encode gzip zstd
    reverse_proxy localhost:3000
}
```

### Security Headers

```caddyfile
(example.com) {
    header {
        # Security headers
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        
        # Remove server identification
        -Server
    }
    
    reverse_proxy localhost:3000
}
```

### Rate Limiting

```caddyfile
{
    # Global rate limit (requires caddy-rate-limit plugin)
    servers {
        rate_limit {
            zone dynamic {
                key {remote_host}
                events 100
                window 1m
            }
        }
    }
}

example.com {
    rate_limit dynamic {
        key {remote_host}
        events 50
        window 1m
    }
    reverse_proxy localhost:3000
}
```

Install rate limiting plugin:
```bash
caddy add-package github.com/mholt/caddy-ratelimit
```

### Wildcard Certificate (DNS Challenge)

```caddyfile
*.example.com {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy localhost:3000
}
```

Install DNS provider:
```bash
caddy add-package github.com/caddy-dns/cloudflare
```

### On-Demand TLS (Multi-Tenant)

For SaaS hosting arbitrary customer domains:
```caddyfile
{
    on_demand_tls {
        ask http://localhost:5555/check  # Validate domain is allowed
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

### Systemd Service

Unit file installed automatically. Common commands:
```bash
sudo systemctl start caddy
sudo systemctl enable caddy
sudo systemctl restart caddy
sudo systemctl status caddy
sudo journalctl -u caddy -f  # Follow logs
```

### Configuration Reload

```bash
# Validate config
caddy validate --config /etc/caddy/Caddyfile

# Reload without downtime
caddy reload --config /etc/caddy/Caddyfile

# Restart (brief downtime)
sudo systemctl restart caddy
```

---

## nginx (Alternative)

Use nginx when:
- Already familiar with nginx
- Need advanced routing features not in Caddy
- Existing infrastructure uses nginx
- Require specific nginx modules

### Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo dnf install nginx

# macOS
brew install nginx
```

### Basic Configuration

**File: `/etc/nginx/sites-available/example.com`**

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    # TLS settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to application
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Static Files

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    root /var/www/public;
    index index.html;
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # HTML - no cache for SPA
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
}
```

### Application Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### WebSocket

```nginx
# In server block
location /socket.io/ {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400;  # 24 hours
}
```

### Rate Limiting

```nginx
# In http block (nginx.conf)
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# In server block
server {
    # Rate limit requests
    limit_req zone=general burst=20 nodelay;
    
    # Connection limit
    limit_conn conn_limit 10;
    
    location / {
        proxy_pass http://localhost:3000;
    }
}
```

### Multiple Applications

```nginx
# API and frontend
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # API
    location /api/ {
        proxy_pass http://localhost:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Cloudflare Origin Certificate

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/ssl/cloudflare/origin.pem;
    ssl_certificate_key /etc/ssl/cloudflare/origin-key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://localhost:3000;
    }
}
```

---

## Health Check Endpoints

### Caddy

```caddyfile
example.com {
    # Health check
    handle /health {
        respond "OK" 200
    }
    
    reverse_proxy localhost:3000
}
```

### nginx

```nginx
location /health {
    access_log off;
    return 200 "OK\n";
    add_header Content-Type text/plain;
}
```

**Application-level health check:**
```nginx
location /health {
    proxy_pass http://localhost:3000/health;
    access_log off;
}
```

---

## Self-Hosted Deployment Checklist

### Pre-Deployment

- [ ] Server provisioned and accessible (SSH access)
- [ ] Domain DNS pointing to server IP
- [ ] Firewall configured (ports 80, 443 open)
- [ ] Application tested locally
- [ ] Environment variables documented

### Server Setup

- [ ] OS updated (`apt update && apt upgrade`)
- [ ] Non-root user created
- [ ] SSH key authentication enabled
- [ ] Firewall configured (ufw or iptables)
- [ ] Fail2ban or similar installed

### Application Setup

- [ ] Node.js/Python/runtime installed
- [ ] Application deployed
- [ ] Environment variables set
- [ ] Application running on localhost port
- [ ] Environment variables documented

### Reverse Proxy Setup

- [ ] Caddy or nginx installed
- [ ] Configuration created for domain
- [ ] Configuration tested (`caddy validate` or `nginx -t`)
- [ ] Service enabled (`systemctl enable caddy` or `systemctl enable nginx`)
- [ ] Service running (`systemctl status caddy`)

### TLS Verification

- [ ] HTTPS working in browser
- [ ] Certificate valid (not self-signed, unless Cloudflare Origin)
- [ ] HTTP redirecting to HTTPS
- [ ] Certificate auto-renewal configured
- [ ] HSTS header set (optional)

### Post-Deployment

- [ ] DNS propagation complete
- [ ] HTTPS working globally (check multiple locations)
- [ ] Monitoring configured (uptime, errors)
- [ ] Backup configuration documented
- [ ] Rollback plan documented

---

## Caddy vs nginx Comparison

| Feature | Caddy | nginx |
|---------|-------|-------|
| **Auto TLS** | ✅ Automatic | ❌ Manual (Certbot) |
| **Config complexity** | Very simple | Moderate |
| **Performance** | Excellent | Excellent |
| **Memory usage** | Lower | Moderate |
| **WebSocket** | Automatic | Manual config |
| **HTTP/2** | Automatic | Manual enable |
| **HTTP/3 (QUIC)** | Automatic | Requires module |
| **Ecosystem** | Smaller | Very large |
| **Learning curve** | Low | Moderate |
| **Best for** | New projects, simplicity | Existing infrastructure, nginx expertise |

### Choose Caddy When:
- Starting fresh with no nginx expertise
- Want zero-config HTTPS
- Prefer simpler configuration
- Modern stack (HTTP/3, auto-compression)

### Choose nginx When:
- Already have nginx expertise
- Existing infrastructure uses nginx
- Need specific nginx modules (Lua, complex auth)
- Organization mandates nginx

---

## Migration from Platform to Self-Hosted

### From Vercel/Netlify to Self-Hosted

1. **Export application:**
   ```bash
   # Next.js static export
   npm run build
   npm run export  # Creates ./out directory
   
   # Or build for Node
   npm run build
   ```

2. **Set up server:**
   ```bash
   # Install Node.js
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt install -y nodejs
   
   # Install PM2 for process management
   sudo npm install -g pm2
   ```

3. **Deploy application:**
   ```bash
   # Copy to server
   scp -r ./out user@server:/var/www/example.com
   
   # Or for Node app
   pm2 start npm --name "app" -- start
   pm2 save
   pm2 startup
   ```

4. **Configure Caddy:**
   ```caddyfile
   example.com {
       root * /var/www/example.com
       file_server
   }
   ```
   
   Or for Node app:
   ```caddyfile
   example.com {
       reverse_proxy localhost:3000
   }
   ```

5. **Update DNS:**
   - Change A record from platform IP to server IP
   - Wait for propagation (up to 48h)

6. **Verify:**
   - HTTPS working
   - All routes functioning
   - Environment variables set

---

## References

- [Ops: DNS & Domain Setup](ops-dns-domain-setup.md) — DNS configuration
- [Ops: TLS/SSL Provisioning](ops-tls-ssl-provisioning.md) — Certificate setup
- [Deployment Target Pack](deployment-target-pack.md) — Platform comparison
- [Launch Procedures](ops-launch-procedures.md) — Deployment runbooks