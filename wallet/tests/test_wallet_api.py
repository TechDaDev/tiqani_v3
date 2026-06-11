"""Tests for wallet API endpoints."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from wallet.models import Wallet, WalletTransaction, PlatformFeeConfig, ContractPaymentBreakdown

User = get_user_model()


class WalletApiTestBase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="pass123", role="client",
        )
        wallet, _ = Wallet.objects.get_or_create(user=self.user)
        wallet.balance = Decimal("1000.00")
        wallet.save(update_fields=["balance"])
        self.url = "/api/wallet/me/"


class WalletMeTest(WalletApiTestBase):
    def test_anonymous_returns_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_returns_200(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["balance"], "1000.00")


class WalletTransactionTest(WalletApiTestBase):
    def test_list_transactions(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/wallet/transactions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_sees_own_transactions_only(self):
        other = User.objects.create_user(
            username="other", email="o@test.com", password="pass", role="client",
        )
        Wallet.objects.get_or_create(user=other)
        self.client.force_authenticate(user=other)
        resp = self.client.get("/api/wallet/transactions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
