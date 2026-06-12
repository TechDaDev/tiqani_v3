"""
Middleware — request ID tagging and logging context enrichment.

Each incoming request gets a unique request ID (X-Request-ID header or
auto-generated UUIDv7).  The ID is threaded through Celery task headers
and structured log records so you can trace a single user action from
HTTP through background jobs.
"""

import logging
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)


def _generate_request_id() -> str:
    """Return a short, URL-safe unique identifier (8 hex chars)."""
    return uuid.uuid4().hex[:8]


class RequestIDMiddleware:
    """
    Attach a unique ``request.request_id`` to every request and set the
    ``X-Request-ID`` response header.

    Also pushes the request ID into Python's logging context so that
    structured log formatters (e.g. ``pythonjsonlogger``) can pick it up.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Use client-supplied ID if present (idempotency), else generate.
        request.request_id = request.META.get(
            "HTTP_X_REQUEST_ID",
            _generate_request_id(),
        )

        # ── Extra context for structured logging ──────────────
        user = getattr(request, "user", None)
        user_id = (
            str(user.pk) if user and user.is_authenticated else "anon"
        )
        request.log_extra = {
            "request_id": request.request_id,
            "method": request.method,
            "path": request.path,
            "user_id": user_id,
        }

        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
