"""
Django base settings for tiqani_v3 project.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOW_CREDENTIALS=(bool, True),
    API_DOCS_PUBLIC=(bool, True),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "development"),
    SENTRY_TRACES_SAMPLE_RATE=(float, 0.0),
)

# Read .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Sentry (initialised in prod.py; config here so env vars are parsed)
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT")
SENTRY_TRACES_SAMPLE_RATE = env("SENTRY_TRACES_SAMPLE_RATE")

# ---------------------------------------------------------------------------
# API documentation access control
# ---------------------------------------------------------------------------
API_DOCS_PUBLIC = env("API_DOCS_PUBLIC")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=True)
CELERY_TIMEZONE = "Asia/Baghdad"
CELERY_ENABLE_UTC = True
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=240)
CELERY_WORKER_MAX_TASKS_PER_CHILD = env.int("CELERY_WORKER_MAX_TASKS_PER_CHILD", default=1000)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# OTP cleanup retention
OTP_CLEANUP_RETENTION_DAYS = env.int("OTP_CLEANUP_RETENTION_DAYS", default=7)

# ---------------------------------------------------------------------------
# ASGI / Channels
# ---------------------------------------------------------------------------
ASGI_APPLICATION = "tiqani_v3.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": env(
            "CHANNEL_LAYERS_BACKEND",
            default="channels_redis.core.RedisChannelLayer",
        ),
        "CONFIG": {
            "hosts": [
                env(
                    "CHANNEL_LAYERS_REDIS_URL",
                    default="redis://redis:6379/2",
                )
            ],
        },
    },
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "django_celery_beat",
    "channels",
    "drf_spectacular",
    # Local apps
    "accounts",
    "category",
    "contract",
    "ratereview",
    "wallet",
    "notification",
    "dashboard",
    "dealership",
    "chat",
    "servicerequest",
    "dispute",
]

AUTH_USER_MODEL = "accounts.CustomUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Project middleware
    "tiqani_v3.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "tiqani_v3.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tiqani_v3.wsgi.application"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Baghdad"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Media storage — S3-compatible (overridable in prod.py / dev.py)
# ---------------------------------------------------------------------------
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)

# S3-compatible storage settings
S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID", default="")
S3_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY", default="")
S3_STORAGE_BUCKET_NAME = env("S3_STORAGE_BUCKET_NAME", default="")
S3_REGION_NAME = env("S3_REGION_NAME", default="us-east-1")
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="")
S3_CUSTOM_DOMAIN = env("S3_CUSTOM_DOMAIN", default="")
S3_SIGNATURE_VERSION = env("S3_SIGNATURE_VERSION", default="s3v4")
S3_ADDRESSING_STYLE = env("S3_ADDRESSING_STYLE", default="virtual")
S3_DEFAULT_ACL = env("S3_DEFAULT_ACL", default="private")
S3_QUERYSTRING_AUTH = env.bool("S3_QUERYSTRING_AUTH", default=True)
S3_QUERYSTRING_EXPIRE = env.int("S3_QUERYSTRING_EXPIRE", default=900)
S3_FILE_OVERWRITE = env.bool("S3_FILE_OVERWRITE", default=False)
S3_OBJECT_PARAMETERS_CACHE_CONTROL = env("S3_OBJECT_PARAMETERS_CACHE_CONTROL", default="max-age=86400")
S3_MEDIA_LOCATION = env("S3_MEDIA_LOCATION", default="media")
S3_PRIVATE_MEDIA_LOCATION = env("S3_PRIVATE_MEDIA_LOCATION", default="private")
S3_PUBLIC_MEDIA_LOCATION = env("S3_PUBLIC_MEDIA_LOCATION", default="public")

# Upload size limits (MB)
MAX_PROFILE_IMAGE_SIZE_MB = env.int("MAX_PROFILE_IMAGE_SIZE_MB", default=2)
MAX_CATEGORY_ICON_SIZE_MB = env.int("MAX_CATEGORY_ICON_SIZE_MB", default=1)
MAX_DOCUMENT_SIZE_MB = env.int("MAX_DOCUMENT_SIZE_MB", default=10)
MAX_PROOF_FILE_SIZE_MB = env.int("MAX_PROOF_FILE_SIZE_MB", default=5)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tiqani-v3-cache",
    }
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="10/minute"),
        "user": env("THROTTLE_USER", default="60/minute"),
        "login": env("THROTTLE_LOGIN", default="5/minute"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="3/minute"),
        "otp": env("THROTTLE_OTP", default="3/minute"),
        "dealership_finance": env("THROTTLE_DEALERSHIP_FINANCE_RATE", default="30/minute"),
        "wallet_finance": env("THROTTLE_WALLET_FINANCE_RATE", default="30/minute"),
        "reviews": env("THROTTLE_REVIEWS_RATE", default="60/minute"),
        "notifications": env("THROTTLE_NOTIFICATIONS_RATE", default="120/minute"),
        "chat_message": env("THROTTLE_CHAT_MESSAGE_RATE", default="60/minute"),
        "chat_attachment": env("THROTTLE_CHAT_ATTACHMENT_RATE", default="10/minute"),
        "chat_price_offer": env("THROTTLE_CHAT_PRICE_OFFER_RATE", default="10/minute"),
        "schema": env("THROTTLE_SCHEMA_RATE", default="20/minute"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=120),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="premium86.web-hosting.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="info@iqtiqani.com")
SERVER_EMAIL = env("SERVER_EMAIL", default="info@iqtiqani.com")

# ---------------------------------------------------------------------------
# OTP Settings
# ---------------------------------------------------------------------------
OTP_VALIDITY_SECONDS = env.int("OTP_VALIDITY_SECONDS", default=600)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=3)
REGISTRATION_VERIFICATION_REQUIRED = env.bool(
    "REGISTRATION_VERIFICATION_REQUIRED", default=True
)

# ---------------------------------------------------------------------------
# Electronic Contracts (Phase 19)
# ---------------------------------------------------------------------------
CONTRACT_PUBLIC_VERIFY_BASE_URL = env(
    "CONTRACT_PUBLIC_VERIFY_BASE_URL",
    default="http://localhost:8000",
)
CONTRACT_PLATFORM_REGISTRATION = env(
    "CONTRACT_PLATFORM_REGISTRATION",
    default="",
)
CONTRACT_PDF_MAX_UPLOAD_MB = env.int("CONTRACT_PDF_MAX_UPLOAD_MB", default=10)

# ---------------------------------------------------------------------------
# Logging — structured JSON with sensitive-data redaction
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_FORMAT = env("LOG_FORMAT", default="verbose")  # "json" or "verbose"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "sensitive_redact": {
            "()": "tiqani_v3.logging_filters.SensitiveDataFilter",
        },
        "sensitive_header_redact": {
            "()": "tiqani_v3.logging_filters.SensitiveHeaderFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "()": "tiqani_v3.logging_filters.StructuredJSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "filters": ["sensitive_redact"],
            "formatter": "json" if LOG_FORMAT == "json" else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
            "filters": ["sensitive_header_redact"],
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "contract": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "wallet": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "notification": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# API documentation (drf-spectacular)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Tiqani API",
    "DESCRIPTION": "Backend API for Tiqani service marketplace, wallets, dealership finance, notifications, and admin operations.",
    "VERSION": "16.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "SECURITY": [{"bearerAuth": []}],
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env("CORS_ALLOW_CREDENTIALS")
