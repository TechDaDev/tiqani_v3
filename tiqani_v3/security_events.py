"""
Lightweight security-event helpers.

Logs noteworthy security events (failed login, password change, role
change, suspicious activity) in a consistent JSON format that can be
shipped to Sentry, parsed by the audit-log export command, or consumed
by external SIEM tools.
"""

import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest

logger = logging.getLogger("security")

User = get_user_model()


def _get_request_meta(request: Optional[HttpRequest]) -> dict:
    """Extract safe metadata from a request object."""
    if request is None:
        return {"ip": "unknown", "user_agent": "unknown", "request_id": ""}
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "unknown")
    return {
        "ip": ip,
        "user_agent": request.META.get("HTTP_USER_AGENT", "unknown")[:255],
        "request_id": getattr(request, "request_id", ""),
    }


def log_security_event(
    event_type: str,
    *,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    detail: Optional[str] = None,
    request: Optional[HttpRequest] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Emit a structured security event.

    Parameters
    ----------
    event_type : str
        Dot-separated classifier, e.g. ``"auth.login.failed"``,
        ``"auth.password_changed"``, ``"admin.role_changed"``,
        ``"auth.suspicious_activity"``.
    user_id : int, optional
    email : str, optional
    detail : str, optional
        Human-readable description.
    request : HttpRequest, optional
    extra : dict, optional
        Additional free-form context.
    """
    meta = _get_request_meta(request)
    payload = {
        "event": event_type,
        "user_id": user_id,
        "email": email,
        "detail": detail,
        "ip": meta["ip"],
        "user_agent": meta["user_agent"],
        "request_id": meta["request_id"],
        **(extra or {}),
    }
    logger.warning("SECURITY_EVENT", extra={"security_event": payload})

    # Also send to Sentry as a breadcrumb when available
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category="security",
            message=event_type,
            data=payload,
            level="warning",
        )
    except ImportError:
        pass
