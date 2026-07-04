"""Tests for post-settlement reversal from technician wallet."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from wallet.models import ContractSettlement, PaymentIntent
from wallet.services import create_contract_payment_breakdown
from wallet.settlement_services import settle_completed_contract
from dispute.models import ContractDispute, DisputeStatus, DisputeReason, ResolutionType, RefundStatus
from dispute.services import open_dispute, start_review, resolve_dispute

User = get_user_model()


class PostSettlementReversalTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True, role="admin",
        )
        self.contract = self._make_settled_contract()

    def test_post_settlement_reversal(self):
        self._credit_tech_wallet()
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.PAYMENT_OR_SETTLEMENT_ERROR,
            statement="Payment error - need reversal.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        updated, resolution, refund, liability = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Post-settlement reversal approved.",
        )
        self.assertEqual(updated.status, DisputeStatus.RESOLVED)
        self.assertIsNotNone(refund)
        self.assertEqual(refund.status, RefundStatus.COMPLETED)

        # Original settlement unchanged (escrow_amount = 500000)
        settlement = ContractSettlement.objects.filter(
            contract=self.contract, status=ContractSettlement.Status.COMPLETED,
        ).first()
        self.assertEqual(settlement.released_principal, Decimal("500000.00"))

    def test_partial_recovery_creates_liability(self):
        # Tech wallet has only 100000
        tech_wallet = self.tech_user.wallet
        tech_wallet.balance = Decimal("100000.00")
        tech_wallet.save(update_fields=["balance"])

        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.PAYMENT_OR_SETTLEMENT_ERROR,
            statement="Need refund.",
            claimed_amount=Decimal("450000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        updated, resolution, refund, liability = resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.MANUAL_RECOVERY_REQUIRED,
            client_refund_amount=Decimal("100000.00"),
            outstanding_liability_amount=Decimal("350000.00"),
            resolution_reason="Partial recovery with liability.",
        )
        self.assertIsNotNone(liability)
        self.assertEqual(liability.remaining_amount, Decimal("350000.00"))

    def test_resolution_audit_events(self):
        self._credit_tech_wallet()
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.PAYMENT_OR_SETTLEMENT_ERROR,
            statement="Reversal needed.",
            claimed_amount=Decimal("500000.00"),
        )
        d = start_review(dispute_id=dispute.id, actor=self.staff_user)
        resolve_dispute(
            dispute_id=d.id,
            actor=self.staff_user,
            resolution_type=ResolutionType.FULL_CLIENT_REFUND,
            client_refund_amount=Decimal("500000.00"),
            resolution_reason="Post-settlement reversal.",
        )
        from dispute.models import DisputeAuditEvent
        events = DisputeAuditEvent.objects.filter(dispute=dispute)
        event_types = [e.event_type for e in events]
        self.assertIn("DISPUTE_RESOLVED", event_types)
        self.assertIn("REFUND_CREATED", event_types)

    def _credit_tech_wallet(self):
        tech_wallet = self.tech_user.wallet
        tech_wallet.balance = Decimal("500000.00")
        tech_wallet.save(update_fields=["balance"])

    def _make_settled_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import Wallet, PlatformWallet
        Wallet.objects.get_or_create(user=self.client_user, defaults={'balance': Decimal('999999.00')})
        Wallet.objects.get_or_create(user=self.tech_user, defaults={'balance': Decimal('999999.00')})
        PlatformWallet.objects.get_or_create(key=PlatformWallet.GLOBAL_KEY)
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        c = Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"),
            escrow_amount=Decimal("500000.00"),
            status="completed",
        )
        PaymentIntent.objects.create(
            contract=c, user=self.client_user,
            amount=Decimal("525000.00"),
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PAID,
        )
        create_contract_payment_breakdown(c)

        # Settle
        settle_completed_contract(contract_id=c.id, actor=self.client_user)
        return c
