"""Tests for sandbox chargeback events."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from dispute.models import (
    ChargebackEvent, ChargebackStatus,
)
from dispute.services import (
    create_sandbox_chargeback, start_chargeback_review,
    submit_chargeback_evidence, sandbox_uphold_chargeback,
    sandbox_reject_chargeback, sandbox_partial_chargeback,
)

User = get_user_model()


class ChargebackEventTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True, role="admin",
        )
        self.contract = self._make_contract()

    def test_create_sandbox_chargeback(self):
        cb = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            reason_code="fraud",
            created_by=self.staff_user,
        )
        self.assertEqual(cb.status, ChargebackStatus.RECEIVED)
        self.assertEqual(cb.amount, Decimal("500000.00"))

    def test_create_chargeback_idempotent(self):
        cb1 = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
            idempotency_key="cb-key-1",
        )
        cb2 = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
            idempotency_key="cb-key-1",
        )
        self.assertEqual(cb1.id, cb2.id)

    def test_chargeback_review_flow(self):
        cb = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
        )
        cb = start_chargeback_review(chargeback_id=cb.id, actor=self.staff_user)
        self.assertEqual(cb.status, ChargebackStatus.UNDER_REVIEW)

        cb = submit_chargeback_evidence(chargeback_id=cb.id, actor=self.staff_user)
        self.assertEqual(cb.status, ChargebackStatus.EVIDENCE_SUBMITTED)

    def test_sandbox_uphold(self):
        cb = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
        )
        cb, dispute, resolution = sandbox_uphold_chargeback(
            chargeback_id=cb.id, actor=self.staff_user,
        )
        self.assertEqual(cb.status, ChargebackStatus.UPHELD)
        self.assertIsNotNone(dispute)
        self.assertIsNotNone(resolution)

    def test_sandbox_reject(self):
        cb = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
        )
        cb = sandbox_reject_chargeback(chargeback_id=cb.id, actor=self.staff_user)
        self.assertEqual(cb.status, ChargebackStatus.REJECTED)

    def test_sandbox_partial(self):
        cb = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
        )
        cb = sandbox_partial_chargeback(
            chargeback_id=cb.id, actor=self.staff_user,
            partial_amount=Decimal("250000.00"),
        )
        self.assertEqual(cb.status, ChargebackStatus.PARTIALLY_UPHELD)

    def test_reject_idempotent(self):
        cb1 = create_sandbox_chargeback(
            contract_id=self.contract.id,
            amount=Decimal("500000.00"),
            created_by=self.staff_user,
        )
        r1 = sandbox_reject_chargeback(
            chargeback_id=cb1.id, actor=self.staff_user,
            idempotency_key="reject-key",
        )
        r2 = sandbox_reject_chargeback(
            chargeback_id=cb1.id, actor=self.staff_user,
            idempotency_key="reject-key",
        )
        self.assertEqual(r1.id, r2.id)
        self.assertEqual(ChargebackEvent.objects.filter(status=ChargebackStatus.REJECTED).count(), 1)

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import Wallet
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        return Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"),
            escrow_amount=Decimal("500000.00"),
            status="active",
        )
