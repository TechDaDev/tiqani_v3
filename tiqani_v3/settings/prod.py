"""
Production settings for tiqani_v3.

Requires SECRET_KEY, ALLOWED_HOSTS, and DATABASE_URL to be set via
environment variables.
"""

from .base import *  # noqa: F403, F401

# ---------------------------------------------------------------------------
# Debug — must be False in production
# ---------------------------------------------------------------------------
DEBUG = False

# ---------------------------------------------------------------------------
# Security — required
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")  # noqa: F405 — will raise if not set
ALLOWED_HOSTS = env("ALLOWED_HOSTS")  # noqa: F405 — will raise if not set

# ---------------------------------------------------------------------------
# Database — PostgreSQL via DATABASE_URL (required)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL"),  # noqa: F405 — will raise if not set
}

# ---------------------------------------------------------------------------
# Email — SMTP required in production; overrides from env
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")  # noqa: F405
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")  # noqa: F405
SERVER_EMAIL = env("SERVER_EMAIL", default="noreply@example.com")  # noqa: F405

# ---------------------------------------------------------------------------
# Security headers & cookies
# ---------------------------------------------------------------------------
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Proxy support — set USE_X_FORWARDED_HOST=True if behind a reverse proxy
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Static files – whitenoise
# ---------------------------------------------------------------------------
MIDDLEWARE.insert(0, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# CORS & CSRF — from environment
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")  # noqa: F405 — will raise if not set
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")  # noqa: F405 — will raise if not set
