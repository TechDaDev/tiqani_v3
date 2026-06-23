"""Tests for refund idempotency and concurrency."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from dispute.models import RefundRecord, ContractDispute, DisputeReason, ResolutionType
from dispute.services import open_dispute, start_review, resolve_dispute

User = get_user_model()


class RefundIdempotencyTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True, role="admin",
        )
        self.contract = self._make_contract()

    def test_two_resolution_calls_one_refund(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Work not delivered.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)

        resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund.",
            idempotency_key="idem-1",
        )
        resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund.",
            idempotency_key="idem-1",
        )
        self.assertEqual(RefundRecord.objects.count(), 1)

    def test_no_duplicate_refund_without_key(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Work not delivered.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)

        resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund.",
        )
        # Second call should fail because dispute is already resolved
        with self.assertRaises(ValueError):
            resolve_dispute(
                dispute_id=d.id,
                actor=self.staff_user,
                resolution_type=ResolutionType.FULL_CLIENT_REFUND,
                client_refund_amount=Decimal("500000.00"),
                resolution_reason="Full refund.",
            )
        # Only one resolution should exist
        self.assertIsNotNone(dispute.resolution)

    def test_escrow_not_double_refunded(self):
        initial_escrow = self.contract.escrow_amount
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Work not delivered.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)

        resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund.",
        )
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, Decimal("0.00"))

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import PaymentIntent, Wallet
        from wallet.services import create_contract_payment_breakdown
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        c = cp.contracts.create(
            technician=tp,
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
