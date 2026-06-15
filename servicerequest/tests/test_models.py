"""Model tests for ServiceRequest — default status, transitions, string representation."""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest

User = get_user_model()


class ServiceRequestModelTest(TestCase):
    """Test ServiceRequest model defaults, transitions, and helpers."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="sr_client", email="sr_c@t.com", password="pass123",
            role="client", phone_number="07500000100", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="sr_tech", email="sr_t@t.com", password="pass123",
            role="technician", phone_number="07500000101", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user,
            job_title="Tech", about="Test", years_of_expertise=3,
            approved=True, is_available=True,
        )

    def _make_request(self, **kwargs):
        defaults = dict(
            client=self.client_profile,
            technician=self.tech_profile,
            title="Test Request",
            description="Need help with something.",
        )
        defaults.update(kwargs)
        return ServiceRequest.objects.create(**defaults)

    def test_default_status_is_pending(self):
        sr = self._make_request()
        self.assertEqual(sr.status, ServiceRequest.Status.PENDING)

    def test_timestamps_set_on_creation(self):
        sr = self._make_request()
        self.assertIsNotNone(sr.created_at)
        self.assertIsNotNone(sr.updated_at)

    def test_string_representation(self):
        sr = self._make_request()
        expected = f"Request {sr.id} - {sr.title} ({sr.status})"
        self.assertEqual(str(sr), expected)

    def test_ordering_newest_first(self):
        sr1 = self._make_request(title="First")
        sr2 = self._make_request(title="Second")
        qs = ServiceRequest.objects.all()
        self.assertEqual(qs.first(), sr2)
        self.assertEqual(qs.last(), sr1)

    def test_valid_pending_to_accepted(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.Status.ACCEPTED)

    def test_valid_pending_to_declined(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.DECLINED
        sr.save()
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.Status.DECLINED)

    def test_valid_pending_to_cancelled(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.CANCELLED
        sr.save()
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.Status.CANCELLED)

    def test_valid_pending_to_withdrawn(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.WITHDRAWN
        sr.save()
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.Status.WITHDRAWN)

    def test_invalid_accepted_to_declined_raises(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        sr.status = ServiceRequest.Status.DECLINED
        with self.assertRaises(ValidationError):
            sr.save()

    def test_invalid_accepted_to_cancelled_raises(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        sr.status = ServiceRequest.Status.CANCELLED
        with self.assertRaises(ValidationError):
            sr.save()

    def test_invalid_declined_to_accepted_raises(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.DECLINED
        sr.save()
        sr.status = ServiceRequest.Status.ACCEPTED
        with self.assertRaises(ValidationError):
            sr.save()

    def test_invalid_cancelled_to_accepted_raises(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.CANCELLED
        sr.save()
        sr.status = ServiceRequest.Status.ACCEPTED
        with self.assertRaises(ValidationError):
            sr.save()

    def test_invalid_withdrawn_to_accepted_raises(self):
        sr = self._make_request()
        sr.status = ServiceRequest.Status.WITHDRAWN
        sr.save()
        sr.status = ServiceRequest.Status.ACCEPTED
        with self.assertRaises(ValidationError):
            sr.save()

    def test_double_transition_raises(self):
        """ACCEPTED → ACCEPTED (no-op in clean, but save works)."""
        sr = self._make_request()
        sr.status = ServiceRequest.Status.ACCEPTED
        sr.save()
        sr.refresh_from_db()
        self.assertEqual(sr.status, ServiceRequest.Status.ACCEPTED)

    def test_client_ownership(self):
        sr = self._make_request()
        self.assertEqual(sr.client, self.client_profile)

    def test_technician_assignment(self):
        sr = self._make_request()
        self.assertEqual(sr.technician, self.tech_profile)
