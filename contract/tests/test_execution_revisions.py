"""Tests for revision requests, resubmission, and history preservation."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone, DeliverableSubmission, RevisionRequest
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class RevisionTestCase(TestCase):
    """Revision request, resubmission, history preservation."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_rev", email="client_rev@test.com",
            password="pass123", role="client",
            phone_number="07700000030", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech_rev", email="tech_rev@test.com",
            password="pass123", role="technician",
            phone_number="07700000031", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.other_client = User.objects.create_user(
            username="client2_rev", email="client2_rev@test.com",
            password="pass123", role="client",
            phone_number="07700000032", governorate="Baghdad",
        )
        ClientProfile.objects.create(user=self.other_client)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Revision test",
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
            summary="First submission",
        )

        self.client_api = APIClient()
        self.tech_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.tech_api.force_authenticate(user=self.tech_user)

    def test_client_requests_revision(self):
        resp = self.client_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/revision/",
            {"reason": "Fix the quality"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.status, ExecutionMilestone.Status.REVISION_REQUESTED)
        self.assertEqual(self.milestone.revision_count, 1)

    def test_technician_cannot_request_revision(self):
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/revision/",
            {"reason": "Self-review"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_client_rejected(self):
        other = APIClient()
        other.force_authenticate(user=self.other_client)
        resp = other.post(
            f"/api/contracts/milestones/{self.milestone.id}/revision/",
            {"reason": "Hack"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_revision_after_approval_rejected(self):
        self.milestone.status = ExecutionMilestone.Status.APPROVED
        self.milestone.save()
        resp = self.client_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/revision/",
            {"reason": "Too late"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revision_history_preserved(self):
        self.client_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/revision/",
            {"reason": "Fix it"}, format="json",
        )
        self.assertEqual(RevisionRequest.objects.filter(milestone=self.milestone).count(), 1)
