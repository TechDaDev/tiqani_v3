"""Tests for concurrency, rollback, security, and input validation.

Covers:
- Concurrent operations (transaction isolation)
- Rollback on service failure
- Security: spoofed identity, private field exclusion, wallet/escrow immutability
- Input validation: unsafe data, oversized payloads
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone, DeliverableSubmission, RevisionRequest
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class ExecutionConcurrencyTestCase(TestCase):
    """Concurrent execution operations maintain data integrity."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="con_client", email="con_client@test.com",
            password="pass123", role="client",
            phone_number="07700000100", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="con_tech", email="con_tech@test.com",
            password="pass123", role="technician",
            phone_number="07700000101", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Concurrency test", agreed_amount=Decimal("100000.00"),
            stage_number=2, start_date=timezone.now().date(),
            duration_days=10, status="active", escrow_amount=Decimal("100000.00"),
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)

    def test_concurrent_milestone_creation_sequences(self):
        """Two milestones created in rapid succession get unique sequences."""
        resp1 = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "A"}, format="json",
        )
        resp2 = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "B"}, format="json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        seqs = set()
        for ms in self.contract.execution_milestones.all():
            self.assertNotIn(ms.sequence, seqs)
            seqs.add(ms.sequence)

    def test_concurrent_reorder_no_duplicates(self):
        ms1 = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="X",
            status=ExecutionMilestone.Status.DRAFT,
        )
        ms2 = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=2, title="Y",
            status=ExecutionMilestone.Status.DRAFT,
        )
        resp = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/reorder/",
            {"sequence": [str(ms2.id), str(ms1.id)]}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ms1.refresh_from_db()
        ms2.refresh_from_db()
        self.assertNotEqual(ms1.sequence, ms2.sequence)


class ExecutionRollbackTestCase(TestCase):
    """Failed operations roll back without partial state."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="roll_client", email="roll_client@test.com",
            password="pass123", role="client",
            phone_number="07700000110", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="roll_tech", email="roll_tech@test.com",
            password="pass123", role="technician",
            phone_number="07700000111", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Rollback test", agreed_amount=Decimal("100000.00"),
            stage_number=2, start_date=timezone.now().date(),
            duration_days=10, status="active", escrow_amount=Decimal("100000.00"),
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)

    def test_approval_failure_no_state_change(self):
        """Approving a PENDING milestone does not change status."""
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="NoSub",
            status=ExecutionMilestone.Status.PENDING,
        )
        resp = self.client_api.post(f"/api/contracts/milestones/{ms.id}/approve/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        ms.refresh_from_db()
        self.assertEqual(ms.status, ExecutionMilestone.Status.PENDING)

    def test_revision_without_submission_rollback(self):
        """No submission to revise — no revision record created."""
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="Fresh",
            status=ExecutionMilestone.Status.SUBMITTED,
        )
        resp = self.client_api.post(
            f"/api/contracts/milestones/{ms.id}/revision/",
            {"reason": "Fix it"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(RevisionRequest.objects.filter(milestone=ms).count(), 0)


class ExecutionSecurityTestCase(TestCase):
    """Security: spoofed identity, private fields, wallet/escrow immutability."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="sec_client", email="sec_client@test.com",
            password="pass123", role="client",
            phone_number="07700000120", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="sec_tech", email="sec_tech@test.com",
            password="pass123", role="technician",
            phone_number="07700000121", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Security test", agreed_amount=Decimal("100000.00"),
            stage_number=2, start_date=timezone.now().date(),
            duration_days=10, status="active", escrow_amount=Decimal("100000.00"),
        )
        self.client_api = APIClient()
        self.tech_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)
        self.tech_api.force_authenticate(user=self.tech_user)

    def test_spoofed_contract_id_returns_404(self):
        """Non-existent contract UUID returns 404, not 500."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = self.client_api.get(f"/api/contracts/{fake_id}/execution/eligibility/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_spoofed_milestone_id_returns_404(self):
        """Non-existent milestone UUID returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = self.client_api.get(f"/api/contracts/milestones/{fake_id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_access_any_contract(self):
        """Staff users can bypass participant checks."""
        staff_user = User.objects.create_user(
            username="staff_sec", password="pass123",
            email="staff@test.com", role="client",
            phone_number="07700000122", governorate="Baghdad",
            is_staff=True,
        )
        staff_api = APIClient()
        staff_api.force_authenticate(user=staff_user)
        resp = staff_api.get(f"/api/contracts/{self.contract.id}/execution-history/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_wallet_fields_excluded_from_milestone_response(self):
        """Milestone responses exclude wallet and escrow fields."""
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="M1",
            status=ExecutionMilestone.Status.DRAFT,
        )
        resp = self.client_api.get(f"/api/contracts/milestones/{ms.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("wallet", resp.data)
        self.assertNotIn("escrow", resp.data)

    def test_escrow_mutation_rejected_through_milestones(self):
        """Cannot modify escrow via milestone endpoints."""
        original = self.contract.escrow_amount
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="M1",
            status=ExecutionMilestone.Status.DRAFT,
        )
        # Try PATCH with escrow field (should be ignored by serializer)
        resp = self.client_api.patch(
            f"/api/contracts/milestones/{ms.id}/",
            {"escrow_amount": "0"}, format="json",
        )
        # Should either ignore unknown fields or reject
        self.assertIn(resp.status_code, [200, 400])
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, original)

    def test_private_email_excluded_from_deliverable_response(self):
        """Deliverable responses exclude email and phone fields."""
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="M1",
            status=ExecutionMilestone.Status.IN_PROGRESS,
        )
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{ms.id}/submit/",
            {"summary": "Work done"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("email", resp.data)
        self.assertNotIn("phone", resp.data)

    def test_spoofed_technician_id_in_submit(self):
        """Wrong tech gets 404, not 403 (no info leak)."""
        other_tech = User.objects.create_user(
            username="other_sec", email="other_sec@test.com",
            password="pass123", role="technician",
            phone_number="07700000123", governorate="Basra",
        )
        TechnicianProfile.objects.create(
            user=other_tech, approved=True,
            job_title="Other", about="Other", years_of_expertise=2,
        )
        other_api = APIClient()
        other_api.force_authenticate(user=other_tech)
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="M1",
            status=ExecutionMilestone.Status.IN_PROGRESS,
        )
        resp = other_api.post(
            f"/api/contracts/milestones/{ms.id}/submit/",
            {"summary": "Hack"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ExecutionInputValidationTestCase(TestCase):
    """Input validation: unsafe data, oversized payloads."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="val_client", email="val_client@test.com",
            password="pass123", role="client",
            phone_number="07700000130", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="val_tech", email="val_tech@test.com",
            password="pass123", role="technician",
            phone_number="07700000131", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Validation test", agreed_amount=Decimal("100000.00"),
            stage_number=2, start_date=timezone.now().date(),
            duration_days=10, status="active", escrow_amount=Decimal("100000.00"),
        )
        ms = ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1, title="M1",
            status=ExecutionMilestone.Status.IN_PROGRESS,
        )
        self.milestone = ms
        self.tech_api = APIClient()
        self.tech_api.force_authenticate(user=self.tech_user)
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)

    def test_oversized_summary_rejected(self):
        """Very long summary text is rejected."""
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": "x" * 5001}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_summary_rejected(self):
        """Empty summary is rejected."""
        resp = self.tech_api.post(
            f"/api/contracts/milestones/{self.milestone.id}/submit/",
            {"summary": ""}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_milestone_past_due_date_rejected(self):
        """Creating a milestone with past due date is rejected."""
        resp = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "Late", "due_date": "2020-01-01"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_sequence_rejected(self):
        """Negative sequence value is rejected."""
        resp = self.client_api.post(
            f"/api/contracts/{self.contract.id}/milestones/",
            {"title": "Bad", "sequence": -1}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
