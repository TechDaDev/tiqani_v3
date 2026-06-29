"""
Production settings for tiqani_v3.

Requires SECRET_KEY, ALLOWED_HOSTS, and DATABASE_URL to be set via
environment variables.
"""

import os

from .base import *  # noqa: F403, F401

# ---------------------------------------------------------------------------
# Debug — must be False in production
# ---------------------------------------------------------------------------
DEBUG = False

# API docs protected in production by default
API_DOCS_PUBLIC = env.bool("API_DOCS_PUBLIC", default=False)  # noqa: F405

# ---------------------------------------------------------------------------
# Sentry — error tracking & performance monitoring
# ---------------------------------------------------------------------------
if SENTRY_DSN:  # noqa: F405
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        environment=SENTRY_ENVIRONMENT,  # noqa: F405
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,  # noqa: F405
        send_default_pii=False,  # Do NOT send user PII to Sentry
        release=os.environ.get("APP_VERSION", "unknown"),  # noqa: F405
    )

# ---------------------------------------------------------------------------
# Security — required
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or env("SECRET_KEY", default="")  # noqa: F405
if not SECRET_KEY or SECRET_KEY.startswith("change-me"):
    raise RuntimeError("Production requires a non-placeholder DJANGO_SECRET_KEY or SECRET_KEY.")
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
EMAIL_HOST = env("EMAIL_HOST", default="premium86.web-hosting.com")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # noqa: F405
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=20)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="otp@iqtiqani.com")  # noqa: F405
SERVER_EMAIL = env("SERVER_EMAIL", default="otp@iqtiqani.com")  # noqa: F405
EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="smtp")  # noqa: F405
EMAIL_API_TIMEOUT = env.float("EMAIL_API_TIMEOUT", default=10.0)  # noqa: F405
RESEND_API_KEY = env("RESEND_API_KEY", default="")  # noqa: F405

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
# Static and media files
# ---------------------------------------------------------------------------
if not USE_S3_STATIC:  # noqa: F405
    MIDDLEWARE.insert(0, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if (USE_S3_MEDIA or USE_S3_STATIC) and "storages" not in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS.insert(0, "storages")  # noqa: F405


def _s3_storage_options(location, *, querystring_auth=None, file_overwrite=None):
    return {
        "access_key": S3_ACCESS_KEY_ID,  # noqa: F405
        "secret_key": S3_SECRET_ACCESS_KEY,  # noqa: F405
        "bucket_name": S3_STORAGE_BUCKET_NAME,  # noqa: F405
        "region_name": S3_REGION_NAME,  # noqa: F405
        "endpoint_url": S3_ENDPOINT_URL if S3_ENDPOINT_URL else None,  # noqa: F405
        "custom_domain": S3_CUSTOM_DOMAIN if S3_CUSTOM_DOMAIN else None,  # noqa: F405
        "signature_version": S3_SIGNATURE_VERSION,  # noqa: F405
        "addressing_style": S3_ADDRESSING_STYLE,  # noqa: F405
        "default_acl": S3_DEFAULT_ACL,  # noqa: F405
        "querystring_auth": S3_QUERYSTRING_AUTH if querystring_auth is None else querystring_auth,  # noqa: F405
        "querystring_expire": S3_QUERYSTRING_EXPIRE,  # noqa: F405
        "file_overwrite": S3_FILE_OVERWRITE if file_overwrite is None else file_overwrite,  # noqa: F405
        "object_parameters": {
            "CacheControl": S3_OBJECT_PARAMETERS_CACHE_CONTROL,  # noqa: F405
        },
        "location": location,
    }


if USE_S3_MEDIA:  # noqa: F405
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": _s3_storage_options(S3_MEDIA_LOCATION),  # noqa: F405
    }

if USE_S3_STATIC:  # noqa: F405
    STORAGES["staticfiles"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": _s3_storage_options(
            S3_STATIC_LOCATION,  # noqa: F405
            querystring_auth=S3_STATIC_QUERYSTRING_AUTH,  # noqa: F405
            file_overwrite=True,
        ),
    }

# No public media serving by Django in production — nginx / CDN handles it

# ---------------------------------------------------------------------------
# CORS & CSRF — from environment
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")  # noqa: F405 — will raise if not set
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")  # noqa: F405 — will raise if not set
