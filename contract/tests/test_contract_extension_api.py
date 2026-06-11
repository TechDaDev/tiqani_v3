"""Tests for contract time extension requests."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract, TimeExtensionRequest
from wallet.models import Wallet

User = get_user_model()


class ExtensionTestBase(APITestCase):

    def setUp(self):
        self.client_api = APIClient()

        self.client_user = User.objects.create_user(
            username="client", email="c@test.com",
            password="pass", role="client",
            phone_number="07701234567", governorate="Baghdad", address="A",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech", email="t@test.com",
            password="pass", role="technician",
            phone_number="07701234568", governorate="Basra", address="B",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title="Dev",
            years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        # Fund wallets
        Wallet.objects.get_or_create(user=self.client_user, defaults={"balance": Decimal("5000")})
        Wallet.objects.filter(user=self.client_user).update(balance=Decimal("5000"))
        Wallet.objects.get_or_create(user=self.tech_user, defaults={"balance": Decimal("1000")})
        Wallet.objects.filter(user=self.tech_user).update(balance=Decimal("1000"))

        # Create in_progress contract
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Project", agreed_amount=Decimal("900.00"),
            stage_number=2, start_date=timezone.now().date(),
            duration_days=15, status="in_progress",
        )
        self.contract.save()

        self.create_url = f"/api/contracts/{self.contract.id}/extension-requests/create/"
        self.list_url = f"/api/contracts/{self.contract.id}/extension-requests/"


class ExtensionCreateTest(ExtensionTestBase):

    def test_technician_can_request_extension(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.create_url, {
            "requested_days": 5,
            "reason": "Need more time",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_client_cannot_request_extension(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.create_url, {
            "requested_days": 5,
            "reason": "No",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_request_extension(self):
        resp = self.client_api.post(self.create_url, {
            "requested_days": 5,
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ExtensionRespondTest(ExtensionTestBase):

    def setUp(self):
        super().setUp()
        self.ext = TimeExtensionRequest.objects.create(
            contract=self.contract,
            requested_by=self.tech_profile,
            requested_days=5,
            reason="More time needed",
        )
        self.approve_url = f"/api/contracts/{self.contract.id}/extension-requests/{self.ext.id}/approve/"
        self.reject_url = f"/api/contracts/{self.contract.id}/extension-requests/{self.ext.id}/reject/"

    def test_client_can_approve_extension(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.approve_url, {"client_response": "OK"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.ext.refresh_from_db()
        self.assertEqual(self.ext.status, "approved")

    def test_client_can_reject_extension(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.reject_url, {"client_response": "Not enough"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.ext.refresh_from_db()
        self.assertEqual(self.ext.status, "rejected")

    def test_technician_cannot_respond(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.approve_url)
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])

    def test_unrelated_user_cannot_respond(self):
        other = User.objects.create_user(
            username="other", email="o@test.com", password="pass", role="client",
        )
        ClientProfile.objects.create(user=other)
        self.client_api.force_authenticate(user=other)
        resp = self.client_api.post(self.approve_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_participant_can_list_extensions(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_anonymous_cannot_list_extensions(self):
        resp = self.client_api.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
