"""Tests for dispute eligibility checks."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract
from dispute.models import ContractDispute, DisputeStatus, DisputeReason
from dispute.services import check_dispute_eligibility

User = get_user_model()


class DisputeEligibilityTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        self.other_user = User.objects.create_user(username="other", password="pass", role="client")
        self.contract = self._make_active_funded_contract()

    def test_client_eligible(self):
        eligible, reason = check_dispute_eligibility(self.contract, self.client_user)
        self.assertTrue(eligible, reason)

    def test_technician_eligible(self):
        eligible, reason = check_dispute_eligibility(self.contract, self.tech_user)
        self.assertTrue(eligible, reason)

    def test_unrelated_user_ineligible(self):
        eligible, reason = check_dispute_eligibility(self.contract, self.other_user)
        self.assertFalse(eligible)

    def test_deleted_contract_ineligible(self):
        self.contract.is_delete = True
        self.contract.save(update_fields=["is_delete"])
        eligible, reason = check_dispute_eligibility(self.contract, self.client_user)
        self.assertFalse(eligible)

    def test_draft_contract_ineligible(self):
        self.contract.status = "draft"
        self.contract.save(update_fields=["status"])
        eligible, reason = check_dispute_eligibility(self.contract, self.client_user)
        self.assertFalse(eligible)

    def test_existing_active_dispute_ineligible(self):
        ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            claimed_amount=Decimal("500000.00"),
            status=DisputeStatus.OPEN,
        )
        eligible, reason = check_dispute_eligibility(self.contract, self.tech_user)
        self.assertFalse(eligible)

    def test_closed_dispute_allows_new(self):
        ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.WORK_NOT_DELIVERED,
            claimed_amount=Decimal("500000.00"),
            status=DisputeStatus.CLOSED,
        )
        eligible, reason = check_dispute_eligibility(self.contract, self.client_user)
        self.assertTrue(eligible, reason)

    def _make_active_funded_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        from wallet.models import PaymentIntent, Wallet
        from wallet.services import create_contract_payment_breakdown
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
