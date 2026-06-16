"""Tests for funding permissions and IDOR."""
from rest_framework import status
from wallet.models import PaymentIntent
from .test_funding_base import FundingTestBase


class FundingPermissionsTest(FundingTestBase):
    def setUp(self):
        super().setUp()
        self._ensure_breakdown(self.contract)
        self.elig_url = f"/api/wallet/contracts/{self.contract.id}/funding/eligibility/"
        self.intent_url = f"/api/wallet/contracts/{self.contract.id}/funding/intents/"
        self.status_url = f"/api/wallet/contracts/{self.contract.id}/funding/status/"

    def test_client_owner_sees_eligibility(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get(self.elig_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_technician_denied_eligibility(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.get(self.elig_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["eligible"])

    def test_technician_can_view_status(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.get(self.status_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Technician should NOT see active_intent details
        self.assertNotIn("active_intent", resp.data)

    def test_other_client_denied_funding(self):
        self.client_api.force_authenticate(user=self.other_client)
        resp = self.client_api.post(self.intent_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_client_cannot_view_status(self):
        self.client_api.force_authenticate(user=self.other_client)
        resp = self.client_api.get(self.status_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_all_denied(self):
        resp = self.client_api.get(self.elig_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        resp = self.client_api.post(self.intent_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        resp = self.client_api.get(self.status_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_uuid_safe(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get("/api/wallet/contracts/not-a-uuid/funding/eligibility/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
