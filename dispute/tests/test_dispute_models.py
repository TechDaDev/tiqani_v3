"""Tests for dispute models."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from dispute.models import (
    ContractDispute, DisputeStatement, DisputeEvidence,
    DisputeResolution, DisputeAuditEvent, RefundRecord,
    ChargebackEvent, UserFinancialLiability,
    DisputeStatus, DisputeReason, ResolutionType,
    RefundSourceType, RefundStatus, ChargebackStatus,
)

User = get_user_model()


class DisputeModelTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.contract = self._make_contract()

    def test_create_dispute(self):
        d = ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            claimed_amount=Decimal("500000.00"),
        )
        self.assertEqual(d.status, DisputeStatus.OPEN)
        self.assertEqual(d.claimed_amount, Decimal("500000.00"))
        self.assertEqual(str(d.contract.contract_reference), str(self.contract.contract_reference))

    def test_dispute_idempotency_key_unique(self):
        ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            claimed_amount=Decimal("500000.00"),
            idempotency_key="key-1",
        )
        with self.assertRaises(Exception):
            ContractDispute.objects.create(
                contract=self.contract,
                opened_by=self.client_user,
                respondent=self.tech_user,
                reason=DisputeReason.WORK_NOT_DELIVERED,
                claimed_amount=Decimal("500000.00"),
                idempotency_key="key-1",
            )

    def test_dispute_statement_creation(self):
        d = self._make_dispute()
        s = DisputeStatement.objects.create(
            dispute=d,
            submitted_by=self.client_user,
            statement="This is a statement about the dispute.",
        )
        self.assertEqual(s.dispute.id, d.id)
        self.assertEqual(s.submitted_by.username, "client")

    def test_dispute_evidence_creation(self):
        d = self._make_dispute()
        e = DisputeEvidence.objects.create(
            dispute=d,
            submitted_by=self.client_user,
            evidence_type="document",
            description="Invoice screenshot",
            mime_type="image/png",
            file_size=1024,
        )
        self.assertEqual(e.dispute.id, d.id)
        self.assertEqual(e.evidence_type, "document")

    def test_dispute_resolution_creation(self):
        d = self._make_dispute()
        r = DisputeResolution.objects.create(
            dispute=d,
            resolved_by=self.client_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Full refund approved.",
        )
        self.assertEqual(r.client_refund_amount, Decimal("500000.00"))

    def test_dispute_audit_event(self):
        d = self._make_dispute()
        e = DisputeAuditEvent.objects.create(
            dispute=d,
            event_type="DISPUTE_CREATED",
            actor=self.client_user,
            payload={"reason": "test"},
        )
        self.assertEqual(e.event_type, "DISPUTE_CREATED")

    def test_refund_record_creation(self):
        d = self._make_dispute()
        r = RefundRecord.objects.create(
            dispute=d,
            contract=self.contract,
            client=self.client_user,
            amount=Decimal("500000.00"),
            source_type=RefundSourceType.ESCROW,
            status=RefundStatus.COMPLETED,
            created_by=self.client_user,
            completed_at="2025-01-01T00:00:00Z",
        )
        self.assertEqual(r.amount, Decimal("500000.00"))
        self.assertEqual(r.status, RefundStatus.COMPLETED)

    def test_chargeback_event_creation(self):
        cb = ChargebackEvent.objects.create(
            contract=self.contract,
            amount=Decimal("500000.00"),
            reason_code="fraud",
            status=ChargebackStatus.RECEIVED,
        )
        self.assertEqual(cb.amount, Decimal("500000.00"))
        self.assertEqual(cb.status, ChargebackStatus.RECEIVED)

    def test_user_financial_liability(self):
        d = self._make_dispute()
        li = UserFinancialLiability.objects.create(
            user=self.tech_user,
            source_dispute=d,
            original_amount=Decimal("100000.00"),
            remaining_amount=Decimal("100000.00"),
        )
        self.assertEqual(li.remaining_amount, Decimal("100000.00"))
        self.assertEqual(str(li), f"Liability {li.remaining_amount} – Open")

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

    def _make_dispute(self):
        return ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            claimed_amount=Decimal("500000.00"),
        )
