"""Tests for milestone CRUD, ordering, permissions, and state transitions."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class MilestoneAPITestCase(TestCase):
    """Milestone creation, update, reorder, permissions."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_ms", email="client_ms@test.com",
            password="pass123", role="client",
            phone_number="07700000010", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech_ms", email="tech_ms@test.com",
            password="pass123", role="technician",
            phone_number="07700000011", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.client2_user = User.objects.create_user(
            username="client2_ms", email="client2_ms@test.com",
            password="pass123", role="client",
            phone_number="07700000012", governorate="Baghdad",
        )
        self.client2_profile = ClientProfile.objects.create(user=self.client2_user)

        self.tech2_user = User.objects.create_user(
            username="tech2_ms", email="tech2_ms@test.com",
            password="pass123", role="technician",
            phone_number="07700000013", governorate="Basra",
        )
        self.tech2_profile = TechnicianProfile.objects.create(
            user=self.tech2_user, approved=True,
            job_title="Electrician", about="Expert", years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.tech2_profile.pk).update(is_complete=True)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Milestone test work",
            agreed_amount=Decimal("200000.00"),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=20,
            status="in_progress",
            escrow_amount=Decimal("200000.00"),
        )
        self.client_api = APIClient()
        self.tech_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.tech_api.force_authenticate(user=self.tech_user)

    def test_client_create_milestone(self):
        resp = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "First", "description": "Do work", "sequence": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.contract.execution_milestones.count(), 1)

    def test_create_auto_sequences(self):
        resp1 = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "A", "description": "Work A"}, format="json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "B", "description": "Work B"}, format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        ms = self.contract.execution_milestones.order_by("sequence")
        self.assertEqual(ms[0].sequence, 1)
        self.assertEqual(ms[1].sequence, 2)

    def test_technician_cannot_create_milestone(self):
        resp = self.tech_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "Bad", "description": "No"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_client_cannot_create_milestone(self):
        other = APIClient()
        other.force_authenticate(user=self.client2_user)
        resp = other.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "Hack", "description": "No"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_draft_milestone(self):
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="Old", description="Old desc",
            status=ExecutionMilestone.Status.DRAFT,
        )
        resp = self.client_api.patch(
            f"/api/contracts/milestones/{ms.id}/",
            {"title": "Updated", "description": "New desc"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ms.refresh_from_db()
        self.assertEqual(ms.title, "Updated")

    def test_approved_milestone_immutable(self):
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="Done", description="Approved",
            status=ExecutionMilestone.Status.APPROVED,
        )
        resp = self.client_api.patch(
            f"/api/contracts/milestones/{ms.id}/",
            {"title": "Hack"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_milestones(self):
        ms1 = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="First", status=ExecutionMilestone.Status.DRAFT,
        )
        ms2 = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=2,
            title="Second", status=ExecutionMilestone.Status.DRAFT,
        )
        resp = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/reorder/",
            {"sequence": [str(ms2.id), str(ms1.id)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ms1.refresh_from_db()
        ms2.refresh_from_db()
        self.assertEqual(ms1.sequence, 2)
        self.assertEqual(ms2.sequence, 1)

    def test_list_milestones(self):
        ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="M1", status=ExecutionMilestone.Status.DRAFT,
        )
        resp = self.client_api.get(f"/api/contracts/{self.contract.id}/milestones/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_technician_can_list_milestones(self):
        ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title="M1", status=ExecutionMilestone.Status.DRAFT,
        )
        resp = self.tech_api.get(f"/api/contracts/{self.contract.id}/milestones/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cross_technician_cannot_list_milestones(self):
        other = APIClient()
        other.force_authenticate(user=self.tech2_user)
        resp = other.get(f"/api/contracts/{self.contract.id}/milestones/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_denied(self):
        anon = APIClient()
        resp = anon.get(f"/api/contracts/{self.contract.id}/milestones/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
