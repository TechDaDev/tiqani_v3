"""Tests for contract funding eligibility API."""
from decimal import Decimal
from rest_framework import status
from wallet.models import PaymentIntent
from wallet.services import check_funding_eligibility
from .test_funding_base import FundingTestBase


class FundingEligibilityServiceTest(FundingTestBase):
    """Service-level eligibility checks."""

    def test_contract_owner_eligible(self):
        eligible, reason = check_funding_eligibility(self.contract, self.client_user)
        self.assertTrue(eligible)
        self.assertIsNone(reason)

    def test_technician_denied(self):
        eligible, reason = check_funding_eligibility(self.contract, self.tech_user)
        self.assertFalse(eligible)
        self.assertIn("client", reason.lower())

    def test_unrelated_client_denied(self):
        eligible, reason = check_funding_eligibility(self.contract, self.other_client)
        self.assertFalse(eligible)
        self.assertIn("client", reason.lower())

    def test_already_funded_denied(self):
        self._fund_contract(self.contract)
        eligible, reason = check_funding_eligibility(self.contract, self.client_user)
        self.assertFalse(eligible)
        self.assertIn("funded", reason.lower())

    def test_canceled_contract_denied(self):
        self.contract.status = "canceled"
        self.contract.save()
        eligible, reason = check_funding_eligibility(self.contract, self.client_user)
        self.assertFalse(eligible)

    def test_no_agreed_amount_denied(self):
        self.contract.agreed_amount = None
        self.contract.save()
        eligible, reason = check_funding_eligibility(self.contract, self.client_user)
        self.assertFalse(eligible)

    def test_pending_intent_denied(self):
        PaymentIntent.objects.create(
            contract=self.contract, user=self.client_user,
            amount=Decimal("1000"), purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PENDING,
        )
        eligible, reason = check_funding_eligibility(self.contract, self.client_user)
        self.assertFalse(eligible)
        self.assertIn("pending", reason.lower())


class FundingEligibilityAPITest(FundingTestBase):
    """API-level eligibility endpoint tests."""

    def test_owner_can_access(self):
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.get(f"/api/wallet/contracts/{self.contract.id}/funding/eligibility/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["eligible"])

    def test_technician_denied(self):
        self.client.force_authenticate(user=self.tech_user)
        resp = self.client.get(f"/api/wallet/contracts/{self.contract.id}/funding/eligibility/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["eligible"])

    def test_unauthenticated_denied(self):
        resp = self.client.get(f"/api/wallet/contracts/{self.contract.id}/funding/eligibility/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_contract(self):
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.get("/api/wallet/contracts/00000000-0000-0000-0000-000000000000/funding/eligibility/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
