"""
Celery app configuration for tiqani_v3.

Usage:
    celery -A tiqani_v3 worker -l info
    celery -A tiqani_v3 beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tiqani_v3.settings.dev")

app = Celery("tiqani_v3")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
