"""Tests for atomic contract creation on offer acceptance."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract
from contract.offer_models import Offer
from servicerequest.models import ServiceRequest

User = get_user_model()


class OfferContractCreationTest(APITestCase):
    """Atomic contract creation on offer acceptance."""

    def setUp(self):
        self.client_api = APIClient()
        self.client_user = User.objects.create_user(
            username="cc_client", email="cc_client@test.com",
            password="pass123", role="client",
            phone_number="07701234520", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="cc_tech", email="cc_tech@test.com",
            password="pass123", role="technician",
            phone_number="07701234521", governorate="Basra",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Test", about="Test", years_of_expertise=5,
        )
        self.request = ServiceRequest.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            title="Test",
            description="Test",
            status=ServiceRequest.Status.ACCEPTED,
        )
        self.offer = Offer.objects.create(
            service_request=self.request,
            amount=Decimal("100000.00"),
            description="Test offer description",
            duration_days=3,
            status=Offer.Status.SUBMITTED,
        )

    def test_acceptance_creates_contract(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        contract = Contract.objects.filter(
            client=self.client_profile,
            technician=self.tech_profile,
        ).first()
        self.assertIsNotNone(contract)
        self.assertEqual(contract.agreed_amount, Decimal("100000.00"))
        self.assertEqual(contract.work_description, "Test offer description")
        self.assertEqual(contract.currency, "IQD")
        self.assertTrue(contract.client_accepted)
        self.assertTrue(contract.technician_accepted)

    def test_duplicate_acceptance_no_duplicate_contract(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp1 = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        resp2 = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)

        contract_count = Contract.objects.filter(
            client=self.client_profile,
            technician=self.tech_profile,
        ).count()
        self.assertEqual(contract_count, 1)

    def test_contract_values_match_offer(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        contract = Contract.objects.get(id=resp.data["contract_id"])
        self.assertEqual(contract.agreed_amount, self.offer.amount)
        self.assertEqual(contract.work_description, self.offer.description)
        self.assertEqual(contract.client.user, self.client_user)
        self.assertEqual(contract.technician.user, self.tech_user)

    def test_offer_status_changed_to_accepted(self):
        self.client_api.force_authenticate(user=self.client_user)
        self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.status, Offer.Status.ACCEPTED)
