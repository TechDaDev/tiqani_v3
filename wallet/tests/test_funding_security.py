"""Tests for funding response security — no private/sensitive fields exposed."""
from decimal import Decimal
from rest_framework import status
from wallet.models import PaymentIntent
from wallet.serializers import PaymentIntentSerializer
from .test_funding_base import FundingTestBase

FORBIDDEN_RESPONSE_FIELDS = [
    "card_number", "card_no", "cvv", "cvc",
    "payment_token", "provider_secret", "webhook_secret",
    "raw_provider_payload", "internal_exception", "exception",
    "private_email", "private_phone", "password", "payout_secret",
    "wallet_balance",
]


class FundingResponseSecurityTest(FundingTestBase):
    def setUp(self):
        super().setUp()
        self._ensure_breakdown(self.contract)
        self.intent = PaymentIntent.objects.create(
            contract=self.contract, user=self.client_user,
            amount=Decimal("525000.00"), currency="IQD",
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PENDING,
            metadata={"test": "data"},
        )

    def test_payment_intent_serializer_no_secrets(self):
        data = PaymentIntentSerializer(self.intent).data
        for field in FORBIDDEN_RESPONSE_FIELDS:
            self.assertNotIn(field, data, f"Field '{field}' should not be in serializer output")

    def test_eligibility_response_no_secrets(self):
        self.client_api.force_authenticate(user=self.client_user)
        url = f"/api/wallet/contracts/{self.contract.id}/funding/eligibility/"
        resp = self.client_api.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for field in FORBIDDEN_RESPONSE_FIELDS:
            self.assertNotIn(field, resp.data)

    def test_funding_status_no_wallet_balance_for_technician(self):
        self.client_api.force_authenticate(user=self.tech_user)
        url = f"/api/wallet/contracts/{self.contract.id}/funding/status/"
        resp = self.client_api.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("wallet_balance", resp.data)
        self.assertNotIn("active_intent", resp.data)
