"""
Development settings for tiqani_v3.

Intended for local development with python manage.py runserver.
"""

from .base import *  # noqa: F403, F401

# ---------------------------------------------------------------------------
# Debug / Security overrides for local development
# ---------------------------------------------------------------------------
DEBUG = True

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-change-in-production")  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

# ---------------------------------------------------------------------------
# Database — SQLite fallback for local dev
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(  # noqa: F405
        "DATABASE_URL",
        default="sqlite:///db.sqlite3",
    ),
}

# ---------------------------------------------------------------------------
# Email — console backend for local dev
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# CORS — permissive for local frontends
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
