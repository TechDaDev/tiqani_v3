"""Security and permission tests for disputes."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from dispute.models import ContractDispute, DisputeStatus, DisputeReason
from dispute.services import (
    open_dispute, check_dispute_eligibility,
    cancel_dispute, add_dispute_statement,
)

User = get_user_model()


class DisputeSecurityTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.other_client = User.objects.create_user(username="other_client", password="pass", role="client")
        self.other_tech = User.objects.create_user(username="other_tech", password="pass", role="technician")
        self.contract = self._make_contract()

    def test_cannot_dispute_other_contract(self):
        other_contract = self._make_other_contract()
        eligible, reason = check_dispute_eligibility(other_contract, self.client_user)
        self.assertFalse(eligible)

    def test_idor_dispute_access(self):
        d1 = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="Issue with work.",
            claimed_amount=Decimal("100000.00"),
        )
        # Other user should not be able to access d1
        from dispute.views import _get_dispute
        result = _get_dispute(d1.id, self.other_client)
        self.assertIsNone(result)

    def test_only_opener_can_cancel(self):
        dispute = open_dispute(
            contract_id=self.contract.id,
            opened_by=self.tech_user,
            reason=DisputeReason.CLIENT_NON_COOPERATION,
            statement="Client not cooperating.",
            claimed_amount=Decimal("100000.00"),
        )
        with self.assertRaises(ValueError):
            cancel_dispute(dispute_id=dispute.id, actor=self.client_user)

    def test_no_anonymous_access(self):
        eligible, reason = check_dispute_eligibility(self.contract, None)
        self.assertFalse(eligible)

    def test_claimed_amount_maximum(self):
        with self.assertRaises(ValueError):
            open_dispute(
                contract_id=self.contract.id,
                opened_by=self.client_user,
                reason=DisputeReason.WORK_NOT_DELIVERED,
                statement="Overclaiming.",
                claimed_amount=Decimal("9999999.00"),
            )

    def test_no_duplicate_active_dispute(self):
        open_dispute(
            contract_id=self.contract.id,
            opened_by=self.client_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            statement="First dispute.",
            claimed_amount=Decimal("100000.00"),
        )
        with self.assertRaises(ValueError):
            open_dispute(
                contract_id=self.contract.id,
                opened_by=self.client_user,
                reason=DisputeReason.WORK_INCOMPLETE,
                statement="Second dispute.",
                claimed_amount=Decimal("100000.00"),
            )

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import PaymentIntent, Wallet
        from wallet.services import create_contract_payment_breakdown
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        Wallet.objects.get_or_create(user=self.other_client)
        Wallet.objects.get_or_create(user=self.other_tech)
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

    def _make_other_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import Wallet
        Wallet.objects.get_or_create(user=self.other_client)
        Wallet.objects.get_or_create(user=self.other_tech)
        other_cp = ClientProfile.objects.create(user=self.other_client)
        other_tp = TechnicianProfile.objects.create(user=self.other_tech)
        return Contract.objects.create(
            client=other_cp, technician=other_tp,
            agreed_amount=Decimal("300000.00"),
            escrow_amount=Decimal("300000.00"),
            status="active",
        )
