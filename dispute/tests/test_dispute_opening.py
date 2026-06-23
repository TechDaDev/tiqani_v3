"""Tests for dispute opening flow."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from dispute.models import ContractDispute, DisputeStatus, DisputeReason
from dispute.services import open_dispute

User = get_user_model()


class DisputeOpeningTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.contract = self._make_active_funded_contract()

    def test_open_dispute_success(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Technician did not deliver any work.",
            claimed_amount=Decimal("500000.00"),
        )
        self.assertEqual(dispute.status, DisputeStatus.OPEN)
        self.assertEqual(dispute.opened_by_id, self.client_user.id)
        self.assertEqual(dispute.respondent_id, self.tech_user.id)
        self.assertEqual(dispute.statements.count(), 1)

    def test_open_dispute_technician(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.tech_user,
            reason=DisputeReason.CLIENT_NON_COOPERATION,
            statement="Client is not providing necessary information.",
            claimed_amount=Decimal("250000.00"),
        )
        self.assertEqual(dispute.opened_by_id, self.tech_user.id)
        self.assertEqual(dispute.respondent_id, self.client_user.id)

    def test_open_dispute_idempotent(self):
        d1 = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="First statement.",
            claimed_amount=Decimal("500000.00"),
            idempotency_key="dup-key",
        )
        d2 = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Second statement.",
            claimed_amount=Decimal("500000.00"),
            idempotency_key="dup-key",
        )
        self.assertEqual(d1.id, d2.id)
        self.assertEqual(ContractDispute.objects.count(), 1)

    def test_open_dispute_invalid_amount(self):
        with self.assertRaises(ValueError):
            open_dispute(
                contract_id=self.contract.id,
                opened_by=self.client_user,
                reason=DisputeReason.WORK_NOT_DELIVERED,
                statement="Claiming too much.",
                claimed_amount=Decimal("99999999.00"),
            )

    def _make_active_funded_contract(self):
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
