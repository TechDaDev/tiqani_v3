"""
Logging utilities — sensitive-data redaction and structured JSON formatter.

Usage in settings::

    LOGGING["filters"]["sensitive_redact"] = {
        "()": "tiqani_v3.logging_filters.SensitiveDataFilter",
    }
    LOGGING["formatters"]["json"] = {
        "()": "tiqani_v3.logging_filters.StructuredJSONFormatter",
    }
"""

import logging
import re
from typing import Any, Dict


# ── Patterns whose values should be masked in logs ────────────────
SENSITIVE_KEYS = re.compile(
    r"("
    r"password|secret|token|auth|credential|api_key|apikey|"
    r"authorization|jwt|access|refresh|ssn|credit_card|"
    r"passwd|pwd|signature|private_key"
    r")",
    re.IGNORECASE,
)


def _should_mask(key: str) -> bool:
    """Return ``True`` if *key* looks like it holds sensitive data."""
    return bool(SENSITIVE_KEYS.search(key))


def _mask_payload(payload: dict) -> dict:
    """Return a copy of *payload* with sensitive values replaced."""
    return {
        k: ("[REDACTED]" if _should_mask(k) else v)
        for k, v in payload.items()
    }


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that redacts sensitive fields from ``record.__dict__``.

    Also redacts ``args[0]`` if it is a dict (common for structured
    loggers).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact top-level keys on the record dict
        for key in list(record.__dict__):
            if _should_mask(key):
                record.__dict__[key] = "[REDACTED]"

        # Redact positional arg if it's a dict (structured logging)
        if record.args:
            try:
                if isinstance(record.args, dict):
                    record.args = _mask_payload(record.args)
                elif (
                    isinstance(record.args, (tuple, list))
                    and len(record.args) > 0
                    and isinstance(record.args[0], dict)
                ):
                    record.args = (_mask_payload(record.args[0]),) + record.args[1:]
            except (KeyError, IndexError, TypeError):
                pass

        return True  # Never drop the record


# ── Header redaction ──────────────────────────────────────────────

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
}

_HEADER_VALUE_PATTERN = re.compile(
    r"(" + "|".join(re.escape(h) for h in SENSITIVE_HEADERS) + r"):\s*\S+.*",
    re.IGNORECASE,
)


class SensitiveHeaderFilter(logging.Filter):
    """
    Log filter that redacts sensitive HTTP headers (e.g. Authorization,
    Cookie, X-API-Key) from ``django.request`` log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        msg = _HEADER_VALUE_PATTERN.sub(r"\1: [REDACTED]", msg)
        record.msg = msg
        record.args = ()
        return True


class StructuredJSONFormatter(logging.Formatter):
    """
    JSON log formatter that includes ``request_id`` when available.

    Falls back to the ``verbose`` format if ``pythonjsonlogger`` is not
    installed (graceful degradation).
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            from pythonjsonlogger import jsonlogger

            fmt = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                timestamp=True,
            )
            # Inject extra context if present
            extra = getattr(record, "log_extra", None) or {}
            record.__dict__.update(extra)
            return fmt.format(record)
        except ImportError:
            # Fallback
            return super().format(record)
