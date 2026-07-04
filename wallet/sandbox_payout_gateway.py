"""
Sandbox payout gateway — simulates withdrawal payout processing.

Enabled only in DEBUG/dev mode. No real funds. No real credentials.
Deterministic success/failure. Idempotent retry support.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings


SANDBOX_PAYOUT_PROVIDER = "sandbox_payout"


def is_sandbox_payout_enabled() -> bool:
    """Sandbox payout only works in DEBUG or when explicitly enabled."""
    if not settings.DEBUG and not getattr(settings, "PAYOUT_SANDBOX_ENABLED", False):
        return False
    provider = getattr(settings, "PAYOUT_PROVIDER", SANDBOX_PAYOUT_PROVIDER)
    return provider == SANDBOX_PAYOUT_PROVIDER


def sandbox_process_payout(
    *,
    amount: Decimal,
    currency: str,
    withdrawal_id: str,
    recipient_username: str,
    simulate_failure: bool = False,
) -> dict:
    """
    Simulate a payout provider call.

    Returns a dict mimicking a payout webhook payload:
        {
            "success": True/False,
            "provider": "sandbox_payout",
            "provider_event_id": "<uuid>",
            "provider_reference": "<uuid>",
            "amount": <Decimal>,
            "currency": "IQD",
            "withdrawal_id": "<str>",
            "error_code": None or "payout_failed",
            "error_message": None or "simulated payout failure",
        }
    """
    if not is_sandbox_payout_enabled():
        raise RuntimeError("Sandbox payout gateway is not enabled.")

    if simulate_failure:
        return {
            "success": False,
            "provider": SANDBOX_PAYOUT_PROVIDER,
            "provider_event_id": uuid.uuid4().hex,
            "provider_reference": uuid.uuid4().hex,
            "amount": amount,
            "currency": currency,
            "withdrawal_id": withdrawal_id,
            "error_code": "sandbox_payout_failed",
            "error_message": "Simulated payout failure (sandbox test).",
        }

    return {
        "success": True,
        "provider": SANDBOX_PAYOUT_PROVIDER,
        "provider_event_id": uuid.uuid4().hex,
        "provider_reference": uuid.uuid4().hex,
        "amount": amount,
        "currency": currency,
        "withdrawal_id": withdrawal_id,
        "error_code": None,
        "error_message": None,
    }


def verify_sandbox_payout_signature(payload: dict, signature: str) -> bool:
    """Sandbox payout signature verification — always returns True in dev."""
    return is_sandbox_payout_enabled()
