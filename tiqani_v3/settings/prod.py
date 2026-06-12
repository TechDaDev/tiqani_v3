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
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    } if USE_S3_MEDIA else {  # noqa: F405
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if USE_S3_MEDIA:  # noqa: F405
    # Add storages to INSTALLED_APPS
    INSTALLED_APPS.insert(0, "storages")  # noqa: F405
    # S3 default storage config
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": S3_ACCESS_KEY_ID,  # noqa: F405
            "secret_key": S3_SECRET_ACCESS_KEY,  # noqa: F405
            "bucket_name": S3_STORAGE_BUCKET_NAME,  # noqa: F405
            "region_name": S3_REGION_NAME,  # noqa: F405
            "endpoint_url": S3_ENDPOINT_URL if S3_ENDPOINT_URL else None,  # noqa: F405
            "custom_domain": S3_CUSTOM_DOMAIN if S3_CUSTOM_DOMAIN else None,  # noqa: F405
            "signature_version": S3_SIGNATURE_VERSION,  # noqa: F405
            "addressing_style": S3_ADDRESSING_STYLE,  # noqa: F405
            "default_acl": S3_DEFAULT_ACL,  # noqa: F405
            "querystring_auth": S3_QUERYSTRING_AUTH,  # noqa: F405
            "querystring_expire": S3_QUERYSTRING_EXPIRE,  # noqa: F405
            "file_overwrite": S3_FILE_OVERWRITE,  # noqa: F405
            "object_parameters": {
                "CacheControl": S3_OBJECT_PARAMETERS_CACHE_CONTROL,  # noqa: F405
            },
            "location": S3_MEDIA_LOCATION,  # noqa: F405
        },
    }

# No public media serving by Django in production — nginx / CDN handles it

# ---------------------------------------------------------------------------
# CORS & CSRF — from environment
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")  # noqa: F405 — will raise if not set
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")  # noqa: F405 — will raise if not set
