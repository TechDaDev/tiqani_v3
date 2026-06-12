# Deployment Guide — tiqani_v3

## Table of Contents

1. [Local venv deployment](#1-local-venv-deployment)
2. [Docker deployment (development)](#2-docker-deployment-development)
3. [Production-like Docker deployment](#3-production-like-docker-deployment)
4. [Environment variables](#4-environment-variables)
5. [Migrations](#5-migrations)
6. [Static files](#6-static-files)
7. [Gunicorn](#7-gunicorn)
8. [Reverse proxy / Nginx](#8-reverse-proxy--nginx)
9. [HTTPS](#9-https)
10. [Database setup](#10-database-setup)
11. [Media / static handling](#11-media--static-handling)

---

## 1. Local venv deployment

```bash
# Clone & enter
git clone https://github.com/TechDaDev/tiqani_v3.git
cd tiqani_v3

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env as needed (defaults work for local SQLite dev)

# Run migrations
.venv/bin/python manage.py migrate

# Seed platform fees (required for wallet fee calculations)
.venv/bin/python manage.py seed_platform_fees

# Create superuser
.venv/bin/python manage.py createsuperuser

# Start server
.venv/bin/python manage.py runserver
```

## 2. Docker deployment (development)

```bash
# Clone & enter
git clone https://github.com/TechDaDev/tiqani_v3.git
cd tiqani_v3

# Configure environment
cp .env.example .env

# Build and start
docker compose up --build

# The API will be available at http://localhost:8000
```

This uses `docker-compose.yml` which starts PostgreSQL, Redis, and the Django dev server with auto-reload.

## 3. Production-like Docker deployment

```bash
# Clone & enter
git clone https://github.com/TechDaDev/tiqani_v3.git
cd tiqani_v3

# Configure production environment
cp .env.production.example .env
# Edit .env with real production values

# Build and start
docker compose -f docker-compose.prod.yml up --build -d
```

**WARNING:** This is production-like, NOT a complete production deployment. It is suitable for staging or preview environments. For true production, consider using Docker Swarm, Kubernetes, or a managed PaaS.

## 4. Environment variables

See `.env.production.example` for the complete list of required and optional variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Yes | `tiqani_v3.settings.dev` | Settings module to use |
| `SECRET_KEY` | Yes | — | Django secret key (keep secret!) |
| `DEBUG` | Yes | `True` | Debug mode (must be False in production) |
| `ALLOWED_HOSTS` | Yes | — | Comma-separated allowed hosts |
| `DATABASE_URL` | Yes | — | Database connection string |
| `CORS_ALLOWED_ORIGINS` | Yes | — | Comma-separated allowed CORS origins |
| `CSRF_TRUSTED_ORIGINS` | Yes | — | Comma-separated trusted CSRF origins |
| `EMAIL_BACKEND` | No | SMTP | Email backend class |
| `OTP_VALIDITY_SECONDS` | No | 600 | OTP code validity duration |
| `OTP_MAX_ATTEMPTS` | No | 3 | Max failed OTP attempts |
| `THROTTLE_ANON` | No | `10/minute` | DRF anonymous throttle rate |
| `THROTTLE_USER` | No | `60/minute` | DRF authenticated user throttle rate |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `SENTRY_DSN` | No | — | Sentry DSN for error tracking |
| `REDIS_URL` | No | — | Redis connection URL |

## 5. Migrations

```bash
# Run all pending migrations
.venv/bin/python manage.py migrate

# Check for pending migrations without applying
.venv/bin/python manage.py makemigrations --check --dry-run
```

Migrations are run automatically on container start when `RUN_MIGRATIONS=true`.

## 6. Static files

```bash
.venv/bin/python manage.py collectstatic --noinput --clear
```

In production, static files are served by WhiteNoise (included in the WSGI stack). No separate web server is required for static files, but a CDN is recommended for high-traffic deployments.

## 7. Gunicorn

```bash
.venv/bin/python -m gunicorn tiqani_v3.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

- **Workers:** Generally `2 * CPU cores + 1`.
- **Timeout:** Adjust based on your slowest endpoint response time.
- For async support, consider Uvicorn with ASGI.

## 8. Reverse proxy / Nginx

For production, place Nginx (or similar) in front of Gunicorn:

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /media/ {
        alias /path/to/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Set `USE_X_FORWARDED_HOST=True` and configure `SECURE_PROXY_SSL_HEADER` in production settings when using a reverse proxy.

## 9. HTTPS

- Set `SECURE_SSL_REDIRECT=True` to auto-redirect HTTP to HTTPS.
- Set `SESSION_COOKIE_SECURE=True` and `CSRF_COOKIE_SECURE=True` for secure cookies.
- Configure HSTS headers (default: 1 year).

## 10. Database setup

### PostgreSQL

```sql
CREATE USER tiqani_user WITH PASSWORD 'strong_password';
CREATE DATABASE tiqani_db OWNER tiqani_user;
ALTER USER tiqani_user CREATEDB;  -- needed for test database creation
```

Then set `DATABASE_URL=postgres://tiqani_user:strong_password@localhost:5432/tiqani_db`.

## 11. Media / static handling

- **Static files:** Served by WhiteNoise in production. Collected via `collectstatic`.
- **Media files** (user uploads): Must be served by the reverse proxy, a CDN, or an S3-compatible storage backend.
- Django does not serve media files in production by default.
- See [`docs/MEDIA_STORAGE.md`](MEDIA_STORAGE.md) for full configuration details, including S3 setup, file validation, and cost controls.
- In Docker Compose, media and static volumes are mounted for persistence.
