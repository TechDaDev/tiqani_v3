"""Concurrency tests for offer acceptance — duplicate, race, and rollback safety."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.test import TestCase

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract
from contract.offer_models import Offer
from contract.offer_services import accept_offer
from servicerequest.models import ServiceRequest

User = get_user_model()


class OfferConcurrencyTest(TestCase):
    """Concurrent acceptance behavior tests."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="con_client", email="con_client@test.com",
            password="pass123", role="client",
            phone_number="07701234590", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="con_tech", email="con_tech@test.com",
            password="pass123", role="technician",
            phone_number="07701234591", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Test", about="Test", years_of_expertise=5,
        )
        self.request = ServiceRequest.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            title="Concurrency test",
            description="Test",
            status=ServiceRequest.Status.ACCEPTED,
        )
        self.offer = Offer.objects.create(
            service_request=self.request,
            amount=Decimal("100000.00"),
            description="Test offer",
            duration_days=3,
            status=Offer.Status.SUBMITTED,
        )

    def test_duplicate_sequential_acceptance_returns_conflict(self):
        """Second sequential accept should raise ValueError."""
        offer, contract = accept_offer(self.offer, self.client_user)
        self.assertEqual(offer.status, Offer.Status.ACCEPTED)
        self.assertIsNotNone(contract)

        # Second accept should fail
        with self.assertRaises(ValueError):
            accept_offer(self.offer, self.client_user)

    def test_no_duplicate_contract_after_duplicate_accept(self):
        """Only one contract exists after a duplicate accept attempt."""
        accept_offer(self.offer, self.client_user)
        try:
            accept_offer(self.offer, self.client_user)
        except ValueError:
            pass

        contract_count = Contract.objects.filter(
            client=self.client_profile,
            technician=self.tech_profile,
        ).count()
        self.assertEqual(contract_count, 1)

    def test_accepted_amount_integrity(self):
        """Contract amount must match offer amount exactly."""
        offer, contract = accept_offer(self.offer, self.client_user)
        self.assertEqual(contract.agreed_amount, self.offer.amount)

    def test_accepted_currency_is_iqd(self):
        """Contract currency must be IQD."""
        offer, contract = accept_offer(self.offer, self.client_user)
        self.assertEqual(contract.currency, "IQD")

    def test_accepted_description_integrity(self):
        """Contract work_description must match offer description."""
        offer, contract = accept_offer(self.offer, self.client_user)
        self.assertEqual(contract.work_description, self.offer.description)

    def test_accepted_offer_is_immutable(self):
        """Accepted offer cannot be edited."""
        offer, contract = accept_offer(self.offer, self.client_user)
        offer.refresh_from_db()
        self.assertEqual(offer.status, Offer.Status.ACCEPTED)
        # Try to transition from ACCEPTED — should fail
        offer.status = Offer.Status.SUBMITTED
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            offer.save()

    def test_unique_constraint_prevents_two_accepted(self):
        """DB unique constraint prevents two ACCEPTED offers per request."""
        accept_offer(self.offer, self.client_user)
        # Create a second offer for the same request and try to accept
        offer2 = Offer.objects.create(
            service_request=self.request,
            amount=Decimal("200000.00"),
            description="Second offer",
            duration_days=5,
            status=Offer.Status.SUBMITTED,
        )
        # Expect IntegrityError from the unique constraint
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                accept_offer(offer2, self.client_user)


class OfferContractSecurityTest(APITestCase):
    """Contract access control and data security tests."""

    def setUp(self):
        self.client_api = APIClient()

        self.client_a = User.objects.create_user(
            username="sec_client_a", email="sec_client_a@test.com",
            password="pass123", role="client",
            phone_number="07701234592", governorate="Baghdad",
        )
        self.client_a_profile = ClientProfile.objects.create(user=self.client_a)

        self.client_b = User.objects.create_user(
            username="sec_client_b", email="sec_client_b@test.com",
            password="pass123", role="client",
            phone_number="07701234593", governorate="Basra",
        )
        self.client_b_profile = ClientProfile.objects.create(user=self.client_b)

        self.tech_a = User.objects.create_user(
            username="sec_tech_a", email="sec_tech_a@test.com",
            password="pass123", role="technician",
            phone_number="07701234594", governorate="Baghdad",
        )
        self.tech_a_profile = TechnicianProfile.objects.create(
            user=self.tech_a, approved=True,
            job_title="Test", about="Test", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_a_profile.pk).update(is_complete=True)

        self.tech_b = User.objects.create_user(
            username="sec_tech_b", email="sec_tech_b@test.com",
            password="pass123", role="technician",
            phone_number="07701234595", governorate="Basra",
        )
        self.tech_b_profile = TechnicianProfile.objects.create(
            user=self.tech_b, approved=True,
            job_title="Test2", about="Test2", years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.tech_b_profile.pk).update(is_complete=True)

        # Request A: Client A → Tech A
        self.request_a = ServiceRequest.objects.create(
            client=self.client_a_profile,
            technician=self.tech_a_profile,
            title="Req A",
            description="For contract test A",
            status=ServiceRequest.Status.ACCEPTED,
        )
        # Request B: Client B → Tech B
        self.request_b = ServiceRequest.objects.create(
            client=self.client_b_profile,
            technician=self.tech_b_profile,
            title="Req B",
            description="For contract test B",
            status=ServiceRequest.Status.ACCEPTED,
        )

        # Offer A → Contract A
        self.offer_a = Offer.objects.create(
            service_request=self.request_a,
            amount=Decimal("50000.00"),
            description="Offer A",
            status=Offer.Status.SUBMITTED,
        )
        self.offer_a, self.contract_a = accept_offer(self.offer_a, self.client_a)

        # Offer B → Contract B
        self.offer_b = Offer.objects.create(
            service_request=self.request_b,
            amount=Decimal("75000.00"),
            description="Offer B",
            status=Offer.Status.SUBMITTED,
        )
        self.offer_b, self.contract_b = accept_offer(self.offer_b, self.client_b)

    def test_client_a_can_view_own_contract(self):
        self.client_api.force_authenticate(user=self.client_a)
        resp = self.client_api.get(f"/api/contracts/{self.contract_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_client_a_cannot_view_client_b_contract(self):
        self.client_api.force_authenticate(user=self.client_a)
        resp = self.client_api.get(f"/api/contracts/{self.contract_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_tech_a_can_view_own_contract(self):
        self.client_api.force_authenticate(user=self.tech_a)
        resp = self.client_api.get(f"/api/contracts/{self.contract_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_tech_a_cannot_view_tech_b_contract(self):
        self.client_api.force_authenticate(user=self.tech_a)
        resp = self.client_api.get(f"/api/contracts/{self.contract_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_user_denied_contract(self):
        unrelated = User.objects.create_user(
            username="unrelated", email="unrelated@test.com",
            password="pass123", role="client",
            phone_number="07701234596", governorate="Najaf",
        )
        ClientProfile.objects.create(user=unrelated)
        self.client_api.force_authenticate(user=unrelated)
        resp = self.client_api.get(f"/api/contracts/{self.contract_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_denied_contract(self):
        resp = self.client_api.get(f"/api/contracts/{self.contract_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_contract_response_excludes_private_fields(self):
        self.client_api.force_authenticate(user=self.client_a)
        resp = self.client_api.get(f"/api/contracts/{self.contract_a.id}/")
        body = str(resp.data)
        self.assertNotIn("email", body)
        self.assertNotIn("phone", body)
        self.assertNotIn("password", body)
