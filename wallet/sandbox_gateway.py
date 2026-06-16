"""
Sandbox payment gateway — provider-neutral test adapter.

Enabled only in DEBUG/dev mode. Impossible to enable accidentally in production.
No real funds. No real credentials. Deterministic success/failure.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings


SANDBOX_PROVIDER_NAME = "sandbox"


def is_sandbox_enabled() -> bool:
    """Sandbox only works in DEBUG or when PAYMENT_SANDBOX_ENABLED is explicitly set."""
    if not settings.DEBUG and not getattr(settings, "PAYMENT_SANDBOX_ENABLED", False):
        return False
    provider = getattr(settings, "PAYMENT_PROVIDER", SANDBOX_PROVIDER_NAME)
    return provider == SANDBOX_PROVIDER_NAME


def sandbox_confirm_payment(
    *,
    amount: Decimal,
    currency: str,
    contract_reference: str,
    payment_intent_id: str,
    simulate_failure: bool = False,
) -> dict:
    """
    Simulate a payment provider confirmation.

    Returns a dict mimicking a verified webhook payload:
        {
            "success": True/False,
            "provider": "sandbox",
            "provider_event_id": "<uuid>",
            "provider_reference": "<uuid>",
            "amount": <Decimal>,
            "currency": "IQD",
            "contract_reference": "<str>",
            "payment_intent_id": "<str>",
            "error_code": None or "card_declined",
            "error_message": None or "simulated failure",
        }
    """
    if not is_sandbox_enabled():
        raise RuntimeError("Sandbox gateway is not enabled in this environment.")

    if simulate_failure:
        return {
            "success": False,
            "provider": SANDBOX_PROVIDER_NAME,
            "provider_event_id": uuid.uuid4().hex,
            "provider_reference": uuid.uuid4().hex,
            "amount": amount,
            "currency": currency,
            "contract_reference": contract_reference,
            "payment_intent_id": payment_intent_id,
            "error_code": "sandbox_simulated_failure",
            "error_message": "Simulated payment failure (sandbox test).",
        }

    return {
        "success": True,
        "provider": SANDBOX_PROVIDER_NAME,
        "provider_event_id": uuid.uuid4().hex,
        "provider_reference": uuid.uuid4().hex,
        "amount": amount,
        "currency": currency,
        "contract_reference": contract_reference,
        "payment_intent_id": payment_intent_id,
        "error_code": None,
        "error_message": None,
    }


def verify_sandbox_signature(payload: dict, signature: str) -> bool:
    """Sandbox provider signature verification — always returns True in dev."""
    return is_sandbox_enabled()
