# tiqani_v3 — Backend API

Django REST Framework backend for the Tiqani platform.

## Tech Stack

- **Framework:** Django 5.2 + Django REST Framework
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT (SimpleJWT)
- **Python:** 3.12+

---

## Quick Start (Development)

### 1. Clone & enter the project

```bash
cd tiqani_v3
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if needed. The defaults are suitable for local development.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

### 8. Test the health endpoint

```bash
curl http://127.0.0.1:8000/api/health/
```

Expected response:

```json
{
  "status": "ok",
  "service": "tiqani_v3",
  "database": "ok",
  "debug": true
}
```

---

## Project Structure

```
tiqani_v3/
├── tiqani_v3/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py          # Shared settings (all environments)
│   │   ├── dev.py           # Development overrides
│   │   └── prod.py          # Production overrides
│   ├── urls.py
│   ├── views.py             # Health check endpoint
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                # User authentication & profiles
├── category/                # Service categories
├── contract/                # Contracts & agreements
├── ratereview/              # Ratings & reviews
├── wallet/                  # Wallet & transactions
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Settings Modules

| Module                        | Environment | Usage                       |
|-------------------------------|-------------|-----------------------------|
| `tiqani_v3.settings.dev`      | dev         | `python manage.py runserver` (default) |
| `tiqani_v3.settings.prod`     | prod        | `gunicorn` or production WSGI |

Override via the `DJANGO_SETTINGS_MODULE` environment variable.

## Production Checklist

- [ ] Set `DJANGO_SETTINGS_MODULE=tiqani_v3.settings.prod`
- [ ] Set a strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Set `ALLOWED_HOSTS` to your domain(s)
- [ ] Set `DATABASE_URL` to your PostgreSQL connection string
- [ ] Set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`
- [ ] Configure a real SMTP `EMAIL_BACKEND`
- [ ] Run `python manage.py collectstatic`
- [ ] Use `gunicorn` behind a reverse proxy (nginx, Caddy, etc.)
