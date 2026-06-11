"""Tests for payment intents."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from wallet.models import Wallet, PaymentIntent
from contract.models import Contract
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class PaymentIntentTestBase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.client_user = User.objects.create_user(
            username="client", email="c@test.com", password="pass", role="client",
            phone_number="07701234567", governorate="Baghdad", address="A",
        )
        User.objects.create_user(
            username="admin", email="a@test.com", password="pass", is_staff=True, role="admin",
        )
        Wallet.objects.get_or_create(user=self.client_user, defaults={"balance": Decimal("1000")})
        Wallet.objects.filter(user=self.client_user).update(balance=Decimal("1000"))

        # Create a minimal contract to reference
        cp = ClientProfile.objects.create(user=self.client_user)
        tech_user = User.objects.create_user(
            username="techpi", email="tpi@test.com", password="pass", role="technician",
            phone_number="07701234568", governorate="Basra", address="B",
        )
        tp = TechnicianProfile.objects.create(user=tech_user, approved=True)
        self.contract = Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000"),
            start_date=timezone.now().date(), duration_days=10,
        )

        self.intent = PaymentIntent.objects.create(
            contract=self.contract,
            user=self.client_user,
            amount=Decimal("525000.00"),
        )
        self.list_url = "/api/wallet/payment-intents/"
        self.detail_url = f"/api/wallet/payment-intents/{self.intent.id}/"
        self.mark_url = f"/api/wallet/payment-intents/{self.intent.id}/mark-paid/"


class PaymentIntentListTest(PaymentIntentTestBase):
    def test_user_can_list_own(self):
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_list(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentIntentMarkPaidTest(PaymentIntentTestBase):
    def test_non_admin_cannot_mark_paid(self):
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.post(self.mark_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_mark_paid(self):
        admin = User.objects.get(username="admin")
        self.client.force_authenticate(user=admin)
        resp = self.client.post(self.mark_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.PAID)
