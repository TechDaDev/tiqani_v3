"""Tests for sandbox payment confirmation."""
from decimal import Decimal
from rest_framework import status
from django.test import override_settings
from wallet.models import PaymentIntent, WalletTransaction
from .test_funding_base import FundingTestBase


@override_settings(DEBUG=True, PAYMENT_PROVIDER="sandbox")
class SandboxConfirmTest(FundingTestBase):
    def setUp(self):
        super().setUp()
        self._ensure_breakdown(self.contract)
        self.client_api.force_authenticate(user=self.client_user)

        # Create pending intent
        self.intent = PaymentIntent.objects.create(
            contract=self.contract, user=self.client_user,
            amount=Decimal("525000.00"), currency="IQD",
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PENDING,
        )
        self.confirm_url = f"/api/wallet/payment-intents/{self.intent.id}/sandbox-confirm/"

    def test_success_confirms_payment(self):
        resp = self.client_api.post(self.confirm_url, {"simulate_failure": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["provider_result"]["success"])

        # Reload intent
        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.PAID)
        self.assertIsNotNone(self.intent.paid_at)

        # Contract funded
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, self.contract.agreed_amount)

    def test_failure_does_not_fund(self):
        resp = self.client_api.post(self.confirm_url, {"simulate_failure": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["provider_result"]["success"])

        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.FAILED)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, Decimal("0.00"))

    def test_duplicate_success_safe(self):
        self.client_api.post(self.confirm_url, {"simulate_failure": False}, format="json")
        resp2 = self.client_api.post(self.confirm_url, {"simulate_failure": False}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already paid", resp2.data["detail"].lower())

        # Exactly one transaction
        txns = WalletTransaction.objects.filter(contract=self.contract)
        self.assertEqual(txns.count(), 2)  # deposit + escrow

    def test_technician_cannot_confirm(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.confirm_url, {"simulate_failure": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_denied(self):
        self.client_api.force_authenticate(user=None)
        resp = self.client_api.post(self.confirm_url, {"simulate_failure": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_intent(self):
        resp = self.client_api.post(
            "/api/wallet/payment-intents/00000000-0000-0000-0000-000000000000/sandbox-confirm/",
            {"simulate_failure": False}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_success_creates_one_transaction(self):
        self.client_api.post(self.confirm_url, {"simulate_failure": False}, format="json")
        txns = WalletTransaction.objects.filter(contract=self.contract)
        self.assertEqual(txns.count(), 2)
        types = [t.transaction_type for t in txns]
        self.assertIn(WalletTransaction.Type.DEPOSIT, types)
        self.assertIn(WalletTransaction.Type.ESCROW, types)
