"""Tests for contract stage lifecycle endpoints."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract, ContractStage
from wallet.models import Wallet, WalletTransaction

User = get_user_model()


class ContractStageTestBase(APITestCase):
    """Set up an in_progress contract with stages."""

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

        # Create in_progress contract with stages
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Project", agreed_amount=Decimal("900.00"),
            stage_number=3, start_date=timezone.now().date(),
            duration_days=15, status="in_progress",
        )
        self.contract.save()
        # Manually create stages if save didn't
        if self.contract.stages.count() == 0:
            for i in range(1, 4):
                ContractStage.objects.create(
                    contract=self.contract, stage_number=i,
                    amount=Decimal("300.00"),
                    deadline=timezone.now().date() + timezone.timedelta(days=i * 5),
                )

        self.stage = self.contract.stages.first()
        self.list_url = f"/api/contracts/{self.contract.id}/stages/"
        self.detail_url = f"/api/contracts/{self.contract.id}/stages/{self.stage.id}/"
        self.submit_url = f"/api/contracts/{self.contract.id}/stages/{self.stage.id}/submit/"
        self.approve_url = f"/api/contracts/{self.contract.id}/stages/{self.stage.id}/approve/"


class StageListTest(ContractStageTestBase):

    def test_participant_can_list_stages(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)

    def test_unrelated_user_cannot_list_stages(self):
        other = User.objects.create_user(
            username="other", email="o@test.com", password="pass", role="client",
        )
        ClientProfile.objects.create(user=other)
        self.client_api.force_authenticate(user=other)
        resp = self.client_api.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_list_stages(self):
        resp = self.client_api.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class StageUpdateTest(ContractStageTestBase):

    def test_technician_can_update_stage(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.patch(self.detail_url, {
            "stage_description": "Updated desc",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_client_cannot_update_stage_details(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.patch(self.detail_url, {
            "stage_description": "Client edit",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class StageSubmitTest(ContractStageTestBase):

    def test_technician_can_submit_stage(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.submit_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.stage.refresh_from_db()
        self.assertIsNotNone(self.stage.completed_at)

    def test_client_cannot_submit_stage(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.submit_url)
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])


class StageApproveTest(ContractStageTestBase):

    def test_client_approve_stage(self):
        # First submit
        self.stage.mark_complete()
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.approve_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_approve_all_stages_completes_contract(self):
        self.client_api.force_authenticate(user=self.tech_user)
        # Submit all stages
        for stage in self.contract.stages.all():
            stage.mark_complete()
        # Approve all stages
        self.client_api.force_authenticate(user=self.client_user)
        for stage in self.contract.stages.all():
            url = f"/api/contracts/{self.contract.id}/stages/{stage.id}/approve/"
            resp = self.client_api.post(url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "completed")

    def test_unapproved_stage_cannot_be_approved(self):
        """Stage must be submitted first."""
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.approve_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
