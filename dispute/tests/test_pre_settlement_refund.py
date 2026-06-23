"""Tests for pre-settlement refund from escrow."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from dispute.models import (
    ContractDispute, RefundRecord, DisputeStatus, DisputeReason,
    ResolutionType, RefundStatus,
)
from dispute.services import open_dispute, resolve_dispute, start_review

User = get_user_model()


class PreSettlementRefundTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True, role="admin",
        )
        self.contract = self._make_contract()
        self.initial_escrow = self.contract.escrow_amount

    def test_full_refund_from_escrow(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Work not delivered.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        updated, resolution, refund, liability = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund approved.",
        )
        self.assertEqual(updated.status, DisputeStatus.RESOLVED)
        self.assertIsNotNone(refund)
        self.assertEqual(refund.amount, Decimal("500000.00"))
        self.assertEqual(refund.status, RefundStatus.COMPLETED)

        # Escrow should be reduced
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, Decimal("0.00"))

        # Client wallet should be credited
        self.client_user.wallet.refresh_from_db()
        self.assertGreater(self.client_user.wallet.balance, Decimal("0"))

    def test_partial_refund_from_escrow(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_INCOMPLETE,
            statement="Only half the work was done.",
            claimed_amount=Decimal("250000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        updated, resolution, refund, liability = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.PARTIAL_CLIENT_REFUND,
            client_refund_amount=Decimal("250000.00"),
            resolution_reason="Partial refund for incomplete work.",
        )
        self.assertEqual(refund.amount, Decimal("250000.00"))

    def test_refund_idempotency(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Work not delivered.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        r1, _, _, _ = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund.",
            idempotency_key="refund-1",
        )
        r2, _, _, _ = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund.",
            idempotency_key="refund-1",
        )
        self.assertEqual(RefundRecord.objects.count(), 1)

    def test_refund_exceeding_escrow_capped(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Full refund requested.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        updated, resolution, refund, liability = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("999999.99"),
            resolution_reason="Refund capped by escrow.",
        )
        self.assertLessEqual(refund.amount, self.initial_escrow)

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import PaymentIntent, Wallet, PlatformWallet
        from wallet.services import create_contract_payment_breakdown
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        PlatformWallet.objects.get_or_create(key=PlatformWallet.GLOBAL_KEY)
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        c = Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"),
            escrow_amount=Decimal("500000.00"),
            status="active",
        )
        PaymentIntent.objects.create(
            contract=c, user=self.client_user,
            amount=Decimal("525000.00"),
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PAID,
        )
        create_contract_payment_breakdown(c)
        return c
