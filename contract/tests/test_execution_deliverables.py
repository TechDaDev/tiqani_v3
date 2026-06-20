"""Tests for deliverable submission, versioning, and permissions."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class DeliverableTestCase(TestCase):
    """Deliverable submission, versioning, permissions."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_del", email="client_del@test.com",
            password="pass123", role="client",
            phone_number="07700000020", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech_del", email="tech_del@test.com",
            password="pass123", role="technician",
            phone_number="07700000021", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.other_tech = User.objects.create_user(
            username="tech_del2", email="tech_del2@test.com",
            password="pass123", role="technician",
            phone_number="07700000022", governorate="Basra",
        )
        self.other_tech_profile = TechnicianProfile.objects.create(
            user=self.other_tech, approved=True,
            job_title="Other", about="Other", years_of_expertise=2,
        )
        TechnicianProfile.objects.filter(pk=self.other_tech_profile.pk).update(is_complete=True)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Deliverable test",
            agreed_amount=Decimal("100000.00"),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=10,
            status="active",
            escrow_amount=Decimal("100000.00"),
        )
        self.milestone = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="MS1", status=ExecutionMilestone.Status.IN_PROGRESS,
        )

        self.client_api = APIClient()
        self.tech_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.tech_api.force_authenticate(user=self.tech_user)
        self.other_tech_api = APIClient()
        self.other_tech_api.force_authenticate(user=self.other_tech)

    def test_technician_submits_deliverable(self):
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "Work complete", "notes": "All done"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.milestone.submissions.count(), 1)
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.status, ExecutionMilestone.Status.SUBMITTED)

    def test_client_cannot_submit_deliverable(self):
        resp = self.client_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "Client hack"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_technician_rejected(self):
        resp = self.other_tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "Wrong tech"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_approved_milestone_rejects_submission(self):
        self.milestone.status = ExecutionMilestone.Status.APPROVED
        self.milestone.save()
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "Too late"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_version_increments(self):
        self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "v1"}, format="json",
        )
        # Submit again needs revision cycle
        self.milestone.status = ExecutionMilestone.Status.REVISION_REQUESTED
        self.milestone.save()
        self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "v2"}, format="json",
        )
        subs = self.milestone.submissions.order_by("version")
        self.assertEqual(subs.count(), 2)
        self.assertEqual(subs[0].version, 1)
        self.assertEqual(subs[1].version, 2)

    def test_list_submissions(self):
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "Done"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp2 = self.client_api.get(f"/api/contracts/milestones/{self.milestone.id}/submissions/")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp2.data), 1)

    def test_submission_private_fields_excluded(self):
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "Done"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("wallet", resp.data)
        self.assertNotIn("escrow", resp.data)
