"""Tests for payment intent creation and listing via the funding API."""
from decimal import Decimal
from rest_framework import status
from wallet.models import PaymentIntent
from .test_funding_base import FundingTestBase


class PaymentIntentCreateTest(FundingTestBase):
    def setUp(self):
        super().setUp()
        self._ensure_breakdown(self.contract)

    def _create_url(self):
        return f"/api/wallet/contracts/{self.contract.id}/funding/intents/"

    def test_client_can_create_intent(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self._create_url())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], PaymentIntent.Status.PENDING)
        self.assertEqual(resp.data["currency"], "IQD")
        # Amount should include client service fee: 500000 + 5% = 525000
        self.assertEqual(Decimal(resp.data["amount"]), Decimal("525000.00"))

    def test_technician_cannot_create_intent(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self._create_url())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_client_cannot_create_intent(self):
        self.client_api.force_authenticate(user=self.other_client)
        resp = self.client_api.post(self._create_url())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_denied(self):
        resp = self.client_api.post(self._create_url())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_request_returns_same_intent(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp1 = self.client_api.post(self._create_url())
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self.client_api.post(self._create_url())
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp1.data["id"], resp2.data["id"])

    def test_already_funded_rejected(self):
        self._fund_contract(self.contract)
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self._create_url())
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_contract_uuid(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post("/api/wallet/contracts/00000000-0000-0000-0000-000000000000/funding/intents/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class PaymentIntentListTest(FundingTestBase):
    def test_user_sees_own_intents(self):
        PaymentIntent.objects.create(
            contract=self.contract, user=self.client_user,
            amount=Decimal("1000"), purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        )
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get("/api/wallet/payment-intents/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_other_user_does_not_see_intent(self):
        PaymentIntent.objects.create(
            contract=self.contract, user=self.client_user,
            amount=Decimal("1000"), purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        )
        self.client_api.force_authenticate(user=self.other_client)
        resp = self.client_api.get("/api/wallet/payment-intents/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)
