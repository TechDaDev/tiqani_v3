"""Tests for Offer model — defaults, transitions, validation."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from contract.offer_models import Offer
from servicerequest.models import ServiceRequest


class OfferModelTest(TestCase):
    """Offer model field defaults, constraints, and string representation."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        cls.client_user = User.objects.create_user(
            username="offer_client", email="offer_client@test.com",
            password="pass123", role="client",
            phone_number="07701234501", governorate="Baghdad",
        )
        cls.tech_user = User.objects.create_user(
            username="offer_tech", email="offer_tech@test.com",
            password="pass123", role="technician",
            phone_number="07701234502", governorate="Baghdad",
        )
        from accounts.models import ClientProfile, TechnicianProfile
        cls.client_profile = ClientProfile.objects.create(user=cls.client_user)
        cls.tech_profile = TechnicianProfile.objects.create(
            user=cls.tech_user, approved=True, job_title="Test",
            about="Test", years_of_expertise=3,
        )

        cls.request = ServiceRequest.objects.create(
            client=cls.client_profile,
            technician=cls.tech_profile,
            title="Test Request",
            description="Test description",
            status=ServiceRequest.Status.ACCEPTED,
        )

    def setUp(self):
        self.offer = Offer.objects.create(
            service_request=self.request,
            amount=Decimal("100000.00"),
            description="Test offer",
            duration_days=3,
        )

    def test_default_status_is_draft(self):
        self.assertEqual(self.offer.status, Offer.Status.DRAFT)

    def test_default_currency_is_iqd(self):
        self.assertEqual(self.offer.currency, "IQD")

    def test_amount_precision(self):
        self.offer.amount = Decimal("99999.99")
        self.offer.save()
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.amount, Decimal("99999.99"))

    def test_client_property(self):
        self.assertEqual(self.offer.client, self.client_profile)

    def test_technician_property(self):
        self.assertEqual(self.offer.technician, self.tech_profile)

    def test_is_terminal_accepted(self):
        self.offer.status = Offer.Status.ACCEPTED
        self.assertTrue(self.offer.is_terminal)

    def test_is_terminal_rejected(self):
        self.offer.status = Offer.Status.REJECTED
        self.assertTrue(self.offer.is_terminal)

    def test_is_terminal_withdrawn(self):
        self.offer.status = Offer.Status.WITHDRAWN
        self.assertTrue(self.offer.is_terminal)

    def test_is_terminal_draft(self):
        self.assertFalse(self.offer.is_terminal)

    def test_is_terminal_submitted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.assertFalse(self.offer.is_terminal)

    def test_can_edit_draft(self):
        self.assertTrue(self.offer.can_edit())

    def test_cannot_edit_submitted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.assertFalse(self.offer.can_edit())

    def test_can_withdraw_submitted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.assertTrue(self.offer.can_withdraw())

    def test_cannot_withdraw_draft(self):
        self.assertFalse(self.offer.can_withdraw())

    def test_str_representation(self):
        expected = f"Offer {self.offer.id} on {self.request.id} ({self.offer.status})"
        self.assertEqual(str(self.offer), expected)

    def test_amount_positive_validation(self):
        offer = Offer(
            service_request=self.request,
            amount=Decimal("0.00"),
            description="Zero amount",
        )
        with self.assertRaises(ValidationError):
            offer.save()

    def test_amount_negative_validation(self):
        offer = Offer(
            service_request=self.request,
            amount=Decimal("-100.00"),
            description="Negative amount",
        )
        with self.assertRaises(ValidationError):
            offer.save()

    def test_status_transition_draft_to_submitted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        self.assertEqual(self.offer.status, Offer.Status.SUBMITTED)

    def test_status_transition_submitted_to_accepted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        self.offer.status = Offer.Status.ACCEPTED
        self.offer.save()
        self.assertEqual(self.offer.status, Offer.Status.ACCEPTED)

    def test_status_transition_submitted_to_rejected(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        self.offer.status = Offer.Status.REJECTED
        self.offer.save()
        self.assertEqual(self.offer.status, Offer.Status.REJECTED)

    def test_status_transition_submitted_to_withdrawn(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        self.offer.status = Offer.Status.WITHDRAWN
        self.offer.save()
        self.assertEqual(self.offer.status, Offer.Status.WITHDRAWN)

    def test_invalid_transition_draft_to_accepted(self):
        with self.assertRaises(ValidationError):
            self.offer.status = Offer.Status.ACCEPTED
            self.offer.save()

    def test_invalid_transition_accepted_to_submitted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        self.offer.status = Offer.Status.ACCEPTED
        self.offer.save()
        with self.assertRaises(ValidationError):
            self.offer.status = Offer.Status.SUBMITTED
            self.offer.save()

    def test_invalid_transition_rejected_to_submitted(self):
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        self.offer.status = Offer.Status.REJECTED
        self.offer.save()
        with self.assertRaises(ValidationError):
            self.offer.status = Offer.Status.SUBMITTED
            self.offer.save()
