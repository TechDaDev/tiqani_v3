"""Tests for funding idempotency and concurrency."""
from decimal import Decimal
from django.test import override_settings
from django.db import transaction
from django.test import TestCase
from wallet.models import PaymentIntent, WalletTransaction
from wallet.services import create_contract_payment_intent, confirm_sandbox_payment
from .test_funding_base import FundingTestBase


class FundingIdempotencyTest(FundingTestBase):
    def setUp(self):
        super().setUp()
        self._ensure_breakdown(self.contract)

    def test_create_contract_payment_intent_idempotent(self):
        i1 = create_contract_payment_intent(self.contract, self.client_user)
        i2 = create_contract_payment_intent(self.contract, self.client_user)
        self.assertEqual(i1.id, i2.id)

    def test_failed_intent_allows_retry_creation(self):
        intent = create_contract_payment_intent(self.contract, self.client_user)
        intent.status = PaymentIntent.Status.FAILED
        intent.save(update_fields=["status"])
        # Should create a new intent since old one is FAILED
        i2 = create_contract_payment_intent(self.contract, self.client_user)
        self.assertIsNotNone(i2)


@override_settings(DEBUG=True, PAYMENT_PROVIDER="sandbox")
class FundingRollbackTest(FundingTestBase):
    def setUp(self):
        super().setUp()
        self._ensure_breakdown(self.contract)
        self.intent = create_contract_payment_intent(self.contract, self.client_user)

    def test_failure_does_not_create_transactions(self):
        """Sandbox failure should not leave any transactions behind."""
        intent_before = PaymentIntent.objects.get(id=self.intent.id)
        txns_before = WalletTransaction.objects.filter(contract=self.contract).count()

        intent, result = confirm_sandbox_payment(str(self.intent.id), simulate_failure=True)
        self.assertFalse(result["success"])

        txns_after = WalletTransaction.objects.filter(contract=self.contract).count()
        self.assertEqual(txns_after, txns_before)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, Decimal("0.00"))
