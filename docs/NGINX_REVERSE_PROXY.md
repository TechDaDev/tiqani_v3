# Nginx Reverse Proxy Guide

## Overview

This guide covers configuring Nginx as a reverse proxy in front of Daphne
for production deployments.

## Minimal Nginx Config

```nginx
upstream tiqani_app {
    server web:8000;
}

server {
    listen 80;
    server_name api.tiqani.com;

    # ── Redirect HTTP → HTTPS ────────────────────────────────
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.tiqani.com;

    # ── SSL ──────────────────────────────────────────────────
    ssl_certificate     /etc/ssl/certs/tiqani.crt;
    ssl_certificate_key /etc/ssl/private/tiqani.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # ── Security headers ─────────────────────────────────────
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;

    # ── Max upload size ──────────────────────────────────────
    client_max_body_size 20M;

    # ── Timeouts ─────────────────────────────────────────────
    proxy_connect_timeout 60s;
    proxy_send_timeout    60s;
    proxy_read_timeout    120s;

    # ── Proxy headers ────────────────────────────────────────
    proxy_set_header Host                 $host;
    proxy_set_header X-Real-IP            $remote_addr;
    proxy_set_header X-Forwarded-For      $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto    $scheme;

    # ── Health check endpoints (for load balancer) ───────────
    location /api/health/ {
        proxy_pass http://tiqani_app;
    }

    location /api/health/live/ {
        proxy_pass http://tiqani_app;
    }

    location /api/health/ready/ {
        proxy_pass http://tiqani_app;
    }

    # ── WebSocket upgrade ────────────────────────────────────
    location /ws/ {
        proxy_pass http://tiqani_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # ── Static files (WhiteNoise handles these, but Nginx can too) ──
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ── Media files (local fallback — prefer S3) ─────────────
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # ── API proxy ────────────────────────────────────────────
    location / {
        proxy_pass http://tiqani_app;
    }
}
```

## WebSocket Considerations

- Daphne handles WebSocket upgrades internally.
- Nginx MUST pass `Upgrade` and `Connection` headers for `/ws/` paths.
- WebSocket timeout should be long (86400s = 24h) to prevent mid-session drops.

## Media Strategy

- **Recommended**: S3-compatible storage (Cloudflare R2, DigitalOcean Spaces, MinIO).
  With S3, Nginx does not serve media — the app generates presigned URLs.
- **Local fallback**: Nginx serves `/media/` directly as shown above.

## Key Environment Variables

| Variable | Value |
|---|---|
| `USE_X_FORWARDED_HOST` | `True` |
| `SECURE_PROXY_SSL_HEADER` | `HTTP_X_FORWARDED_PROTO: https` |
| `ALLOWED_HOSTS` | `api.tiqani.com,localhost` |

## Verifying the Setup

```bash
# Test Nginx config
nginx -t

# Reload
nginx -s reload

# Check health
curl -I https://api.tiqani.com/api/health/

# Check WebSocket (from client machine)
curl -i -H "Upgrade: websocket" -H "Connection: Upgrade" https://api.tiqani.com/ws/notifications/?token=YOUR_JWT
```
