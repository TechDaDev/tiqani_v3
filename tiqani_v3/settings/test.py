"""Test settings – high throttle limits so tests don't hit 429."""

from .base import *  # noqa: F403

# Force local media storage in tests — no S3
USE_S3_MEDIA = False

# High throttle limits so tests don't get 429
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # type: ignore[name-defined]  # noqa: F405
    "anon": "100000/hour",
    "user": "100000/hour",
    "login": "100000/hour",
    "password_reset": "100000/hour",
    "otp": "100000/hour",
}
