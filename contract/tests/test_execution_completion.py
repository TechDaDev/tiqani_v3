"""Tests for completion request, confirmation, rejection, and escrow safety."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone, DeliverableSubmission, CompletionRequest
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class CompletionTestCase(TestCase):
    """Completion request, confirmation, rejection."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_comp", email="client_comp@test.com",
            password="pass123", role="client",
            phone_number="07700000050", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech_comp", email="tech_comp@test.com",
            password="pass123", role="technician",
            phone_number="07700000051", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.wrong_tech = User.objects.create_user(
            username="tech_wrong", email="tech_wrong@test.com",
            password="pass123", role="technician",
            phone_number="07700000052", governorate="Basra",
        )
        self.wrong_tech_profile = TechnicianProfile.objects.create(
            user=self.wrong_tech, approved=True,
            job_title="Wrong", about="Wrong", years_of_expertise=2,
        )
        TechnicianProfile.objects.filter(pk=self.wrong_tech_profile.pk).update(is_complete=True)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Completion test",
            agreed_amount=Decimal("100000.00"),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=10,
            status="active",
            escrow_amount=Decimal("100000.00"),
        )
        self.milestone = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="MS1", status=ExecutionMilestone.Status.APPROVED,
        )

        self.client_api = APIClient()
        self.tech_api = APIClient()
        self.wrong_tech_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.tech_api.force_authenticate(user=self.tech_user)
        self.wrong_tech_api.force_authenticate(user=self.wrong_tech)

    def test_technician_requests_completion(self):
        resp = self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "All done"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "completion_requested")

    def test_incomplete_milestones_rejected(self):
        ExecutionMilestone.objects.create(
            contract=self.contract, sequence=2,
            title="MS2", status=ExecutionMilestone.Status.PENDING,
        )
        resp = self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Not done"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_technician_rejected(self):
        resp = self.wrong_tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Hack"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_confirms_completion(self):
        self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Done"}, format="json",
        )
        resp = self.client_api.post(f"/api/contracts/{self.contract.id}/complete/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "completed")
        self.assertIsNotNone(self.contract.completed_at)

    def test_escrow_unchanged_after_completion(self):
        original_escrow = self.contract.escrow_amount
        original_total_paid = self.contract.total_paid
        self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Done"}, format="json",
        )
        self.client_api.post(f"/api/contracts/{self.contract.id}/complete/")
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, original_escrow)
        self.assertEqual(self.contract.total_paid, original_total_paid)

    def test_client_rejects_completion(self):
        self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Done"}, format="json",
        )
        resp = self.client_api.post(
            f"/api/contracts/{self.contract.id}/completion-reject/",
            {"confirm": False, "response_message": "More work needed"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "active")

    def test_duplicate_completion_request_safe(self):
        self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Done"}, format="json",
        )
        resp2 = self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Again"}, format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_confirmation_safe(self):
        self.tech_api.post(
            f"/api/contracts/{self.contract.id}/completion-request/",
            {"completion_message": "Done"}, format="json",
        )
        self.client_api.post(f"/api/contracts/{self.contract.id}/complete/")
        # Contract is completed, cannot confirm again
        resp2 = self.client_api.post(f"/api/contracts/{self.contract.id}/complete/")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
