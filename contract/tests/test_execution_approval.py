"""Tests for milestone approval — idempotent, client-only, escrow unchanged."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone, DeliverableSubmission
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class ApprovalTestCase(TestCase):
    """Milestone approval rules."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_app", email="client_app@test.com",
            password="pass123", role="client",
            phone_number="07700000040", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech_app", email="tech_app@test.com",
            password="pass123", role="technician",
            phone_number="07700000041", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Approval test",
            agreed_amount=Decimal("100000.00"),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=10,
            status="active",
            escrow_amount=Decimal("100000.00"),
        )
        self.milestone = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="MS1", status=ExecutionMilestone.Status.SUBMITTED,
        )
        self.submission = DeliverableSubmission.objects.create(
            milestone=self.milestone,
            submitted_by=self.tech_user,
            version=1,
            summary="Done",
        )

        self.client_api = APIClient()
        self.tech_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.tech_api.force_authenticate(user=self.tech_user)

    def test_client_approves(self):
        resp = self.client_api.post(f"/api/contracts/milestones/{self.milestone.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.status, ExecutionMilestone.Status.APPROVED)
        self.assertIsNotNone(self.milestone.approved_at)

    def test_technician_cannot_approve_own_work(self):
        resp = self.tech_api.post(f"/api/contracts/milestones/{self.milestone.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_approval_without_submission_rejected(self):
        ms2 = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=2,
            title="MS2", status=ExecutionMilestone.Status.PENDING,
        )
        resp = self.client_api.post(f"/api/contracts/milestones/{ms2.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_approval_safe(self):
        self.client_api.post(f"/api/contracts/milestones/{self.milestone.id}/approve/")
        resp2 = self.client_api.post(f"/api/contracts/milestones/{self.milestone.id}/approve/")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_escrow_unchanged_after_approval(self):
        original = self.contract.escrow_amount
        self.client_api.post(f"/api/contracts/milestones/{self.milestone.id}/approve/")
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, original)
