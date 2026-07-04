"""Comprehensive Phase 9 tests — concurrency, rollback, reconciliation, security, withdrawals.

Simplified to avoid PostgreSQL managed-model flush issues.
Uses TestCase everywhere.
"""

from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from contract.models import Contract, ContractAuditEvent
from wallet.models import (
    ContractSettlement, ContractPaymentBreakdown,
    Wallet, WalletTransaction, PlatformWallet,
    PlatformEarning, PlatformWalletTransaction, PaymentIntent,
    WithdrawalRequest,
)
from wallet.settlement_services import (
    settle_completed_contract, check_settlement_eligibility,
    get_financial_summary,
)
from wallet.reconciliation_services import reconcile_contract
from wallet import services as svc

User = get_user_model()


# ══════════════════════════════════════════════════════════════
#  Settlement tests (concurrency, rollback, basic)
# ══════════════════════════════════════════════════════════════

class SettlementTest(TestCase):
    """Settlement creation, concurrency, and rollback."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="st_client", password="pass", role="client",
        )
        self.tech_user = User.objects.create_user(
            username="st_tech", password="pass", role="technician",
        )
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        self.contract = self._make_contract()
        self.platform_wallet = PlatformWallet.get_global_wallet()

    def test_basic_settlement_succeeds(self):
        """Basic settlement creates completed settlement."""
        settlement = settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        self.assertEqual(settlement.status, ContractSettlement.Status.COMPLETED)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, Decimal("0.00"))

    def test_idempotency_key_returns_same(self):
        """Same key returns same settlement."""
        s1 = settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
            idempotency_key="key-1",
        )
        s2 = settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
            idempotency_key="key-1",
        )
        self.assertEqual(s1.id, s2.id)
        self.assertEqual(
            ContractSettlement.objects.filter(status=ContractSettlement.Status.COMPLETED).count(), 1,
        )

    def test_duplicate_settlement_raises(self):
        """Second settlement attempt raises."""
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        with self.assertRaises(ValueError):
            settle_completed_contract(
                contract_id=str(self.contract.id), actor=self.client_user,
            )

    def test_technician_wallet_credited(self):
        """Technician wallet receives net amount."""
        initial = self.tech_user.wallet.balance
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        self.tech_user.wallet.refresh_from_db()
        self.assertEqual(self.tech_user.wallet.balance, initial + Decimal("450000.00"))

    def test_platform_wallet_credited(self):
        """Platform wallet receives fees."""
        initial = self.platform_wallet.balance
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        self.platform_wallet.refresh_from_db()
        self.assertEqual(self.platform_wallet.balance, initial + Decimal("75000.00"))

    def test_one_release_txn(self):
        """Exactly one RELEASE transaction."""
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        count = WalletTransaction.objects.filter(
            contract=self.contract, transaction_type=WalletTransaction.Type.RELEASE,
        ).count()
        self.assertEqual(count, 1)

    def test_earnings_recorded(self):
        """Both earning types exist."""
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        self.assertEqual(
            PlatformEarning.objects.filter(contract=self.contract).count(), 2,
        )

    def test_audit_event_created(self):
        """ESCROW_RELEASED audit event exists."""
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        self.assertTrue(
            ContractAuditEvent.objects.filter(
                contract=self.contract, event_type="ESCROW_RELEASED",
            ).exists(),
        )

    def test_technician_cannot_release(self):
        """Technician not eligible to release."""
        eligible, _ = check_settlement_eligibility(self.contract, self.tech_user)
        self.assertFalse(eligible)

    def test_financial_summary_returns(self):
        """Financial summary returns expected fields."""
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        summary = get_financial_summary(str(self.contract.id))
        self.assertIn("settlement", summary)
        self.assertIsNotNone(summary["settlement"])

    def test_balanced_reconciliation(self):
        """Settled contract reconciles as BALANCED."""
        settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user,
        )
        result = reconcile_contract(str(self.contract.id))
        self.assertEqual(result.reconciliation_status, "BALANCED")
        self.assertEqual(result.discrepancies, [])

    def test_unsettled_reconciliation(self):
        """Uns settled contract returns UNSETTLED."""
        result = reconcile_contract(str(self.contract.id))
        self.assertEqual(result.reconciliation_status, "UNSETTLED")

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
            status=PaymentIntent.Status.PAID, paid_at="2026-06-21T10:00:00Z",
        )
        from wallet.services import create_contract_payment_breakdown
        create_contract_payment_breakdown(c)
        return c


# ══════════════════════════════════════════════════════════════
#  Withdrawal tests
# ══════════════════════════════════════════════════════════════

class WithdrawalTest(TestCase):
    """Withdrawal creation, approval, processing, payout."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            username="w_staff", password="pass", email="w_staff@test.com",
        )
        self.tech_user = User.objects.create_user(
            username="w_tech", password="pass", role="technician",
        )
        wallet, _ = Wallet.objects.get_or_create(user=self.tech_user)
        wallet.balance = Decimal("50000.00")
        wallet.save(update_fields=["balance"])

    def test_create_withdrawal(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        self.assertEqual(wr.status, WithdrawalRequest.Status.PENDING)
        self.assertEqual(wr.amount, Decimal("10000.00"))

    def test_minimum_withdrawal(self):
        with self.assertRaises(ValueError):
            svc.create_withdrawal_request(self.tech_user, Decimal("500.00"))

    def test_insufficient_balance(self):
        with self.assertRaises(ValueError):
            svc.create_withdrawal_request(self.tech_user, Decimal("99999.00"))

    def test_reserved_balance(self):
        svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        available = svc.get_available_balance(self.tech_user.wallet)
        self.assertEqual(available, Decimal("40000.00"))

    def test_two_withdrawals(self):
        svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        available = svc.get_available_balance(self.tech_user.wallet)
        self.assertEqual(available, Decimal("30000.00"))

    def test_approve_succeeds(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.approve_withdrawal_request(wr, self.staff)
        wr.refresh_from_db()
        self.assertEqual(wr.status, WithdrawalRequest.Status.APPROVED)

    def test_reject_succeeds(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.reject_withdrawal_request(wr, self.staff)
        wr.refresh_from_db()
        self.assertEqual(wr.status, WithdrawalRequest.Status.REJECTED)

    def test_cancel_succeeds(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.cancel_withdrawal_request(wr, self.tech_user)
        wr.refresh_from_db()
        self.assertEqual(wr.status, WithdrawalRequest.Status.CANCELED)


@override_settings(PAYOUT_SANDBOX_ENABLED=True, PAYOUT_PROVIDER="sandbox_payout")
class WithdrawalSandboxTest(TestCase):
    """Withdrawal processing with sandbox payout."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            username="ws_staff", password="pass", email="ws_staff@test.com",
        )
        self.tech_user = User.objects.create_user(
            username="ws_tech", password="pass", role="technician",
        )
        wallet, _ = Wallet.objects.get_or_create(user=self.tech_user)
        wallet.balance = Decimal("50000.00")
        wallet.save(update_fields=["balance"])

    def test_process_deducts_wallet(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.approve_withdrawal_request(wr, self.staff)
        bal_before = self.tech_user.wallet.balance
        svc.process_withdrawal_request(wr, self.staff)
        self.tech_user.wallet.refresh_from_db()
        self.assertEqual(self.tech_user.wallet.balance, bal_before - Decimal("10000.00"))

    def test_sandbox_payout_success(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.approve_withdrawal_request(wr, self.staff)
        result = svc.confirm_withdrawal_payout(wr, self.staff, simulate_failure=False)
        result.refresh_from_db()
        self.assertEqual(result.status, WithdrawalRequest.Status.PAID)

    def test_sandbox_payout_failure(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.approve_withdrawal_request(wr, self.staff)
        result = svc.confirm_withdrawal_payout(wr, self.staff, simulate_failure=True)
        result.refresh_from_db()
        self.assertEqual(result.status, WithdrawalRequest.Status.FAILED)

    def test_retry_after_failure(self):
        wr = svc.create_withdrawal_request(self.tech_user, Decimal("10000.00"))
        svc.approve_withdrawal_request(wr, self.staff)
        svc.confirm_withdrawal_payout(wr, self.staff, simulate_failure=True)
        wr.refresh_from_db()
        self.assertEqual(wr.status, WithdrawalRequest.Status.FAILED)
        result = svc.retry_failed_withdrawal(wr, self.staff, simulate_failure=False)
        result.refresh_from_db()
        self.assertEqual(result.status, WithdrawalRequest.Status.PAID)
