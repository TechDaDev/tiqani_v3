"""Test settings – high throttle limits so tests don't hit 429."""

from .base import *  # noqa: F403

# In-memory SQLite so tests never need an external database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Force local media storage in tests — no S3
USE_S3_MEDIA = False

# Celery — always run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Channels — use in-memory layer in tests (no Redis dependency)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# High throttle limits so tests don't get 429
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # type: ignore[name-defined]  # noqa: F405
    "anon": "100000/hour",
    "user": "100000/hour",
    "login": "100000/hour",
    "password_reset": "100000/hour",
    "otp": "100000/hour",
    "dealership_finance": "100000/hour",
    "wallet_finance": "100000/hour",
    "reviews": "100000/hour",
    "notifications": "100000/hour",
    "chat_message": "100000/hour",
    "chat_attachment": "100000/hour",
    "chat_price_offer": "100000/hour",
    "schema": "100000/hour",
}

# API docs accessible in test
API_DOCS_PUBLIC = True
