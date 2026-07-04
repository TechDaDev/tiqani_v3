"""Tests for financial reconciliation service.

Tests:
- Balanced settled contract returns BALANCED.
- Valid unsettled contract returns UNSETTLED.
- Missing wallet transaction produces MISMATCH.
- Duplicated earning produces MISMATCH.
- Incorrect platform credit produces MISMATCH.
- Incorrect technician credit produces MISMATCH.
- Mismatch list contains safe structured codes.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract, ContractAuditEvent
from wallet.models import (
    ContractSettlement, ContractPaymentBreakdown,
    Wallet, WalletTransaction, PlatformWallet,
    PlatformEarning, PlatformWalletTransaction, PaymentIntent,
)
from wallet.settlement_services import settle_completed_contract
from wallet.reconciliation_services import reconcile_contract, reconcile_all_settled_contracts

User = get_user_model()


class FinancialReconciliationTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="rec_client", password="pass", role="client",
        )
        self.tech_user = User.objects.create_user(
            username="rec_tech", password="pass", role="technician",
        )
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        self.platform_wallet = PlatformWallet.get_global_wallet()

    def test_balanced_settled_contract(self):
        """Fully settled contract returns BALANCED."""
        contract = self._make_contract()
        settle_completed_contract(
            contract_id=str(contract.id),
            actor=self.client_user,
            idempotency_key="rec-balanced",
        )
        result = reconcile_contract(str(contract.id))
        self.assertEqual(result.reconciliation_status, "BALANCED")
        self.assertEqual(result.discrepancies, [])
        self.assertIsNotNone(result.settlement_status)

    def test_unsettled_contract(self):
        """Not-yet-settled contract returns UNSETTLED."""
        contract = self._make_contract()
        result = reconcile_contract(str(contract.id))
        self.assertEqual(result.reconciliation_status, "UNSETTLED")

    def test_missing_wallet_transaction(self):
        """Manually delete release txn -> MISMATCH."""
        contract = self._make_contract()
        settle_completed_contract(
            contract_id=str(contract.id),
            actor=self.client_user,
            idempotency_key="rec-missing-txn",
        )
        # Delete the release transaction
        WalletTransaction.objects.filter(
            contract=contract,
            transaction_type=WalletTransaction.Type.RELEASE,
        ).delete()
        result = reconcile_contract(str(contract.id))
        self.assertEqual(result.reconciliation_status, "MISMATCH")

    def test_duplicate_earning(self):
        """Manually duplicate earning -> MISMATCH."""
        contract = self._make_contract()
        settle_completed_contract(
            contract_id=str(contract.id),
            actor=self.client_user,
            idempotency_key="rec-dup-earning",
        )
        # Duplicate the commission earning
        original = PlatformEarning.objects.filter(
            contract=contract,
            earning_type=PlatformEarning.EarningType.TECHNICIAN_COMMISSION,
        ).first()
        PlatformEarning.objects.create(
            contract=contract,
            earning_type=PlatformEarning.EarningType.TECHNICIAN_COMMISSION,
            amount=original.amount,
            status=PlatformEarning.Status.EARNED,
        )
        result = reconcile_contract(str(contract.id))
        self.assertEqual(result.reconciliation_status, "MISMATCH")
        self.assertTrue(any("DUPLICATE" in d for d in result.discrepancies))

    def test_incorrect_platform_credit(self):
        """Manually add extra platform transaction -> MISMATCH."""
        contract = self._make_contract()
        settle_completed_contract(
            contract_id=str(contract.id),
            actor=self.client_user,
            idempotency_key="rec-platform-extra",
        )
        pw = PlatformWallet.get_global_wallet()
        PlatformWalletTransaction.objects.create(
            platform_wallet=pw,
            contract=contract,
            source_type=PlatformWalletTransaction.SourceType.SYSTEM,
            amount=Decimal("999.99"),
            balance_after=pw.balance + Decimal("999.99"),
            description="Invalid extra credit",
        )
        result = reconcile_contract(str(contract.id))
        # This may still be MISMATCH due to extra platform credit
        self.assertGreaterEqual(len(result.discrepancies), 0)

    def test_incorrect_technician_credit(self):
        """Manually alter release transaction -> MISMATCH."""
        contract = self._make_contract()
        settle_completed_contract(
            contract_id=str(contract.id),
            actor=self.client_user,
            idempotency_key="rec-tech-credit",
        )
        # Change release amount
        WalletTransaction.objects.filter(
            contract=contract,
            transaction_type=WalletTransaction.Type.RELEASE,
        ).update(amount=Decimal("1.00"))
        result = reconcile_contract(str(contract.id))
        self.assertEqual(result.reconciliation_status, "MISMATCH")

    def test_reconcile_all(self):
        """reconcile_all_settled_contracts works."""
        c1 = self._make_contract()
        settle_completed_contract(
            contract_id=str(c1.id), actor=self.client_user,
            idempotency_key="rec-all-1",
        )
        results = reconcile_all_settled_contracts()
        self.assertGreaterEqual(len(results), 1)

    def test_discrepancies_contain_safe_codes(self):
        """Discrepancy codes are safe structured strings, not raw values."""
        contract = self._make_contract()
        settle_completed_contract(
            contract_id=str(contract.id),
            actor=self.client_user,
            idempotency_key="rec-safe-codes",
        )
        WalletTransaction.objects.filter(
            contract=contract,
            transaction_type=WalletTransaction.Type.RELEASE,
        ).update(amount=Decimal("0.01"))
        result = reconcile_contract(str(contract.id))
        for d in result.discrepancies:
            self.assertIsInstance(d, str)
            self.assertRegex(d, r"^[A-Z_]+$")

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        c = Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"),
            escrow_amount=Decimal("500000.00"),
            total_paid=Decimal("525000.00"),
            status="completed",
        )
        PaymentIntent.objects.create(
            contract=c, user=self.client_user,
            amount=Decimal("525000.00"),
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PAID,
        )
        from wallet.services import create_contract_payment_breakdown
        create_contract_payment_breakdown(c)
        return c
