import logging
import os

from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
def health_live(request):
    """Minimal liveness probe — returns 200 if the process is alive."""
    return JsonResponse({"status": "alive"})


@never_cache
def health_ready(request):
    """Readiness probe — verifies critical dependencies without exposing secrets."""
    db_status = "ok"
    redis_status = "not_required"
    config_status = "ok"
    status_code = 200
    try:
        conn = connections[DEFAULT_DB_ALIAS]
        conn.ensure_connection()
    except Exception as exc:
        db_status = "error"
        status_code = 503
        logger.error("Readiness check failed: %s", exc)

    redis_url = (
        os.environ.get("REDIS_URL")
        or os.environ.get("CELERY_BROKER_URL")
        or os.environ.get("CHANNEL_LAYERS_REDIS_URL")
    )
    if redis_url and "redis://" in redis_url:
        redis_status = "configured"

    if not settings.DEBUG:
        missing = []
        if not (os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("SECRET_KEY")):
            missing.append("DJANGO_SECRET_KEY")
        if not os.environ.get("ALLOWED_HOSTS"):
            missing.append("ALLOWED_HOSTS")
        if missing:
            config_status = "error"
            status_code = 503

    overall_ok = db_status == "ok" and config_status == "ok"
    return JsonResponse(
        {
            "status": "ok" if overall_ok else "error",
            "service": "tiqani_v3",
            "database": db_status,
            "redis": redis_status,
            "configuration": config_status,
        },
        status=status_code,
    )


@never_cache
def health_deep(request):
    """Deep health check — database, Celery (if not eager), and version info."""
    db_status = "ok"
    db_error = None
    try:
        conn = connections[DEFAULT_DB_ALIAS]
        conn.ensure_connection()
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)

    # Celery worker status (best-effort ping)
    celery_status = "not_configured"
    celery_error = None
    if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
        try:
            from celery.utils import uuid as celery_uuid

            from tiqani_v3.celery import app as celery_app

            ping_id = celery_uuid()
            result = celery_app.control.ping(timeout=2.0)
            if result:
                celery_status = "ok"
            else:
                celery_status = "no_workers"
        except Exception as exc:
            celery_status = "error"
            celery_error = str(exc)
    else:
        celery_status = "eager_mode"

    overall_status = "ok" if db_status == "ok" else "error"

    return JsonResponse(
        {
            "status": overall_status,
            "service": "tiqani_v3",
            "database": db_status,
            "database_error": db_error,
            "celery": celery_status,
            "celery_error": celery_error,
            "debug": settings.DEBUG,
            "version": os.environ.get("APP_VERSION", ""),
        },
        status=200 if overall_status == "ok" else 503,
    )


# Backward-compatible alias
health = health_ready
ready = health_ready
