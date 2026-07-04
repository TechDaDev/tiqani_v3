"""Tests for execution history — event recording, append-only, actor tracking."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from contract.models import Contract, ExecutionMilestone, DeliverableSubmission, ContractAuditEvent
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class HistoryTestCase(TestCase):
    """Execution history recording and permissions."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_hist", email="client_hist@test.com",
            password="pass123", role="client",
            phone_number="07700000060", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech_hist", email="tech_hist@test.com",
            password="pass123", role="technician",
            phone_number="07700000061", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.other_user = User.objects.create_user(
            username="other_hist", email="other_hist@test.com",
            password="pass123", role="client",
            phone_number="07700000062", governorate="Baghdad",
        )
        ClientProfile.objects.create(user=self.other_user)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="History test",
            agreed_amount=Decimal("100000.00"),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=10,
            status="active",
            escrow_amount=Decimal("100000.00"),
        )

        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.client_user)

    def test_history_returns_events(self):
        from contract.execution_services import _record_event
        _record_event(self.contract, "CONTRACT_ACTIVATED", self.client_user, {"ts": "now"})
        resp = self.client_api.get(f"/api/contracts/{self.contract.id}/execution-history/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_unrelated_user_cannot_read_history(self):
        other = APIClient()
        other.force_authenticate(user=self.other_user)
        resp = other.get(f"/api/contracts/{self.contract.id}/execution-history/")
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_cannot_read_history(self):
        anon = APIClient()
        resp = anon.get(f"/api/contracts/{self.contract.id}/execution-history/")
        self.assertEqual(resp.status_code, 401)

    def test_event_has_actor_and_type(self):
        from contract.execution_services import _record_event
        _record_event(self.contract, "MILESTONE_APPROVED", self.client_user, {})
        resp = self.client_api.get(f"/api/contracts/{self.contract.id}/execution-history/")
        self.assertEqual(resp.status_code, 200)
        event = resp.data[0]
        self.assertIn("event_type", event)
        self.assertIn("actor_name", event)
        self.assertIn("created_at", event)
