"""Test settings – high throttle limits so tests don't hit 429."""

from .base import *  # noqa: F403

# Force local media storage in tests — no S3
USE_S3_MEDIA = False

# Celery — always run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# High throttle limits so tests don't get 429
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # type: ignore[name-defined]  # noqa: F405
    "anon": "100000/hour",
    "user": "100000/hour",
    "login": "100000/hour",
    "password_reset": "100000/hour",
    "otp": "100000/hour",
}
