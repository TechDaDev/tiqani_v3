"""Tests for dispute state machine transitions."""
from decimal import Decimal
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from wallet.models import Wallet, WalletTransaction
from dispute.models import (
    ContractDispute, DisputeStatement, DisputeAuditEvent,
    DisputeStatus, DisputeReason,
)
from dispute.services import (
    open_dispute, add_dispute_statement, cancel_dispute,
    assign_staff, start_review, start_mediation, propose_resolution,
    reject_dispute, close_dispute,
)

User = get_user_model()


class DisputeStateMachineTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True, role="admin",
        )
        self.contract = self._make_contract()
        self.dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Work not delivered.",
            claimed_amount=Decimal("500000.00"),
        )

    def test_open_to_awaiting_response(self):
        updated = add_dispute_statement(
            dispute_id=self.dispute.id,
            submitted_by=self.tech_user,
            statement="I delivered the work. Here is the proof.",
        )
        self.assertEqual(updated.status, DisputeStatus.AWAITING_RESPONSE)

    def test_open_to_under_review(self):
        updated = start_review(dispute_id=self.dispute.id, actor=self.staff_user)
        self.assertEqual(updated.status, DisputeStatus.UNDER_REVIEW)

    def test_under_review_to_mediation(self):
        d = start_review(dispute_id=self.dispute.id, actor=self.staff_user)
        updated = start_mediation(dispute_id=d.id, actor=self.staff_user)
        self.assertEqual(updated.status, DisputeStatus.MEDIATION)

    def test_under_review_to_resolution_proposed(self):
        d = start_review(dispute_id=self.dispute.id, actor=self.staff_user)
        updated = propose_resolution(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_data={"resolution_type": "full_client_refund", "amount": "500000.00"},
        )
        self.assertEqual(updated.status, DisputeStatus.RESOLUTION_PROPOSED)

    def test_open_canceled_by_opener(self):
        updated = cancel_dispute(dispute_id=self.dispute.id, actor=self.client_user)
        self.assertEqual(updated.status, DisputeStatus.CANCELED)

    def test_technician_cannot_cancel(self):
        with self.assertRaises(ValueError):
            cancel_dispute(dispute_id=self.dispute.id, actor=self.tech_user)

    def test_reject_workflow(self):
        d = start_review(dispute_id=self.dispute.id, actor=self.staff_user)
        updated = reject_dispute(dispute_id=d.id, actor=self.staff_user, reason="No evidence.")
        self.assertEqual(updated.status, DisputeStatus.REJECTED)

    def test_close_workflow(self):
        d = start_review(dispute_id=self.dispute.id, actor=self.staff_user)
        d = reject_dispute(dispute_id=d.id, actor=self.staff_user, reason="No evidence.")
        updated = close_dispute(dispute_id=d.id, actor=self.staff_user)
        self.assertEqual(updated.status, DisputeStatus.CLOSED)

    def test_audit_events_created(self):
        start_review(dispute_id=self.dispute.id, actor=self.staff_user)
        events = DisputeAuditEvent.objects.filter(dispute=self.dispute)
        self.assertGreaterEqual(events.count(), 2)

    def test_assign_staff(self):
        updated = assign_staff(dispute_id=self.dispute.id, staff_user=self.staff_user)
        self.assertEqual(updated.assigned_staff_id, self.staff_user.id)

    def test_invalid_transition_raises(self):
        with self.assertRaises(ValueError):
            start_mediation(dispute_id=self.dispute.id, actor=self.staff_user)

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import PaymentIntent
        from wallet.services import create_contract_payment_breakdown
        # Ensure wallets exist
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
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
