"""Tests for withdrawal requests."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from wallet.models import Wallet, WithdrawalRequest

User = get_user_model()


class WithdrawalTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="tech", email="t@test.com", password="pass", role="technician",
        )
        wallet, _ = Wallet.objects.get_or_create(user=self.user)
        wallet.balance = Decimal("5000.00")
        wallet.save(update_fields=["balance"])

        self.admin = User.objects.create_user(
            username="admin", email="a@test.com", password="pass", is_staff=True, role="admin",
        )

        self.list_url = "/api/wallet/withdrawals/"

    def test_create_withdrawal(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.list_url, {"amount": "1000.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_cannot_withdraw_more_than_balance(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.list_url, {"amount": "99999.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_cannot_create(self):
        resp = self.client.post(self.list_url, {"amount": "100.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_approve_withdrawal(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.list_url, {"amount": "1000.00"}, format="json")
        wr_id = resp.data["id"]

        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f"/api/wallet/withdrawals/{wr_id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_reject_withdrawal(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.list_url, {"amount": "1000.00"}, format="json")
        wr_id = resp.data["id"]

        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f"/api/wallet/withdrawals/{wr_id}/reject/", {"admin_note": "No"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_approve(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.list_url, {"amount": "100.00"}, format="json")
        wr_id = resp.data["id"]

        other = User.objects.create_user(
            username="other", email="o@test.com", password="pass", role="client",
        )
        self.client.force_authenticate(user=other)
        resp = self.client.post(f"/api/wallet/withdrawals/{wr_id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
