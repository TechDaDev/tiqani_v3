"""Tests for Offer API — creation, transitions, permissions, IDOR."""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from contract.offer_models import Offer
from servicerequest.models import ServiceRequest

User = get_user_model()


class OfferApiTestBase(APITestCase):
    """Base class with client, technician, accepted request."""

    def setUp(self):
        self.client_api = APIClient()

        # Client A
        self.client_user = User.objects.create_user(
            username="client_a", email="client_a@test.com",
            password="pass123", role="client",
            phone_number="07701234510", governorate="Baghdad",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        # Client B (unrelated)
        self.client_b_user = User.objects.create_user(
            username="client_b", email="client_b@test.com",
            password="pass123", role="client",
            phone_number="07701234511", governorate="Basra",
        )
        self.client_b_profile = ClientProfile.objects.create(user=self.client_b_user)

        # Technician A
        self.tech_user = User.objects.create_user(
            username="tech_a", email="tech_a@test.com",
            password="pass123", role="technician",
            phone_number="07701234512", governorate="Baghdad",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title="Plumber", about="Expert", years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        # Technician B (unrelated)
        self.tech_b_user = User.objects.create_user(
            username="tech_b", email="tech_b@test.com",
            password="pass123", role="technician",
            phone_number="07701234513", governorate="Basra",
        )
        self.tech_b_profile = TechnicianProfile.objects.create(
            user=self.tech_b_user, approved=True,
            job_title="Electrician", about="Pro", years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.tech_b_profile.pk).update(is_complete=True)

        # Accepted request: Client A → Technician A
        self.accepted_request = ServiceRequest.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            title="Fix AC",
            description="AC not cooling.",
            status=ServiceRequest.Status.ACCEPTED,
        )

        # Pending request (not eligible for offers)
        self.pending_request = ServiceRequest.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            title="Pending Task",
            description="Not yet accepted.",
            status=ServiceRequest.Status.PENDING,
        )

        # Accepted request for IDOR: Client B → Technician B
        self.cross_request = ServiceRequest.objects.create(
            client=self.client_b_profile,
            technician=self.tech_b_profile,
            title="Cross request",
            description="Belongs to Client B.",
            status=ServiceRequest.Status.ACCEPTED,
        )


# ------------------------------------------------------------------
# Offer creation
# ------------------------------------------------------------------

class OfferCreateTest(OfferApiTestBase):
    """POST /api/technician/offers/"""

    def setUp(self):
        super().setUp()
        self.url = "/api/technician/offers/"
        self.valid_payload = {
            "service_request_id": str(self.accepted_request.id),
            "amount": "150000.00",
            "description": "I will fix the AC unit completely.",
            "duration_days": 3,
        }

    def test_technician_can_create_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(self.url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "DRAFT")
        self.assertEqual(resp.data["amount"], "150000.00")

    def test_anonymous_cannot_create_offer(self):
        resp = self.client_api.post(self.url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_cannot_create_offer(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(self.url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_technician_cannot_create_offer(self):
        """Technician B cannot create offer for Tech A's request."""
        self.client_api.force_authenticate(user=self.tech_b_user)
        resp = self.client_api.post(self.url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_create_offer_for_pending_request(self):
        self.client_api.force_authenticate(user=self.tech_user)
        payload = {**self.valid_payload, "service_request_id": str(self.pending_request.id)}
        resp = self.client_api.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_invalid_amount_zero(self):
        self.client_api.force_authenticate(user=self.tech_user)
        payload = {**self.valid_payload, "amount": "0"}
        resp = self.client_api.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_request_id(self):
        self.client_api.force_authenticate(user=self.tech_user)
        payload = {**self.valid_payload, "service_request_id": "00000000-0000-0000-0000-000000000000"}
        resp = self.client_api.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ------------------------------------------------------------------
# Technician offer management
# ------------------------------------------------------------------

class TechnicianOfferManageTest(OfferApiTestBase):
    """List, detail, update, submit, withdraw."""

    def setUp(self):
        super().setUp()
        self.offer = Offer.objects.create(
            service_request=self.accepted_request,
            amount=Decimal("100000.00"),
            description="Test offer",
            duration_days=2,
        )
        # Another offer for same request (cross for IDOR)
        self.cross_offer = Offer.objects.create(
            service_request=self.cross_request,
            amount=Decimal("200000.00"),
            description="Cross offer",
            duration_days=5,
        )

    def test_technician_can_list_own_offers(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.get("/api/technician/offers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)  # only own

    def test_technician_cannot_see_other_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.get(f"/api/technician/offers/{self.cross_offer.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_technician_can_update_draft_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.patch(
            f"/api/technician/offers/{self.offer.id}/",
            {"description": "Updated description"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["description"], "Updated description")

    def test_technician_can_submit_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(f"/api/technician/offers/{self.offer.id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "SUBMITTED")

    def test_technician_can_withdraw_submitted_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        self.offer.status = Offer.Status.SUBMITTED
        self.offer.save()
        resp = self.client_api.post(f"/api/technician/offers/{self.offer.id}/withdraw/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "WITHDRAWN")

    def test_cannot_withdraw_draft_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(f"/api/technician/offers/{self.offer.id}/withdraw/")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


# ------------------------------------------------------------------
# Client offer review
# ------------------------------------------------------------------

class ClientOfferReviewTest(OfferApiTestBase):
    """Client views, accepts, rejects offers."""

    def setUp(self):
        super().setUp()
        # Submitted offer for Client A's request
        self.offer = Offer.objects.create(
            service_request=self.accepted_request,
            amount=Decimal("150000.00"),
            description="AC fix offer",
            duration_days=3,
            status=Offer.Status.SUBMITTED,
        )
        # Cross offer for Client B
        self.cross_offer = Offer.objects.create(
            service_request=self.cross_request,
            amount=Decimal("250000.00"),
            description="Cross offer",
            duration_days=4,
            status=Offer.Status.SUBMITTED,
        )

    def test_client_can_list_incoming_offers(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get("/api/offers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_client_cannot_see_other_client_offers(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get(f"/api/offers/{self.cross_offer.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_can_accept_offer(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["offer_status"], "ACCEPTED")
        self.assertIsNotNone(resp.data.get("contract_id"))

    def test_accept_creates_contract(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        from contract.models import Contract
        contract = Contract.objects.get(id=resp.data["contract_id"])
        self.assertEqual(contract.agreed_amount, self.offer.amount)
        self.assertEqual(contract.client.user, self.client_user)
        self.assertEqual(contract.technician.user, self.tech_user)
        self.assertEqual(contract.work_description, self.offer.description)

    def test_duplicate_accept_is_safe(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp1 = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        resp2 = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)

    def test_client_can_reject_offer(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/reject/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "REJECTED")

    def test_technician_cannot_accept_own_offer(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_accept_other_client_offer(self):
        self.client_api.force_authenticate(user=self.client_b_user)
        # Client B trying to accept Client A's offer via URL
        resp = self.client_api.post(f"/api/offers/{self.offer.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ------------------------------------------------------------------
# By-request lookup
# ------------------------------------------------------------------

class OfferByRequestTest(OfferApiTestBase):
    """GET /api/offers/by-request/<uuid:request_id>/"""

    def setUp(self):
        super().setUp()
        self.offer = Offer.objects.create(
            service_request=self.accepted_request,
            amount=Decimal("100000.00"),
            description="Test offer",
            duration_days=2,
        )

    def test_client_can_lookup_by_request(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get(f"/api/offers/by-request/{self.accepted_request.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_technician_can_lookup_by_request(self):
        self.client_api.force_authenticate(user=self.tech_user)
        resp = self.client_api.get(f"/api/offers/by-request/{self.accepted_request.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_unrelated_user_cannot_lookup(self):
        self.client_api.force_authenticate(user=self.tech_b_user)
        resp = self.client_api.get(f"/api/offers/by-request/{self.accepted_request.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ------------------------------------------------------------------
# Security / IDOR
# ------------------------------------------------------------------

class OfferSecurityTest(OfferApiTestBase):
    """Cross-user access, anonymous, private fields."""

    def setUp(self):
        super().setUp()
        self.offer = Offer.objects.create(
            service_request=self.accepted_request,
            amount=Decimal("100000.00"),
            description="Test offer",
            duration_days=2,
            status=Offer.Status.SUBMITTED,
        )

    def test_anonymous_access_denied(self):
        resp = self.client_api.get("/api/technician/offers/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        resp = self.client_api.get("/api/offers/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cross_client_offer_access_denied(self):
        self.client_api.force_authenticate(user=self.client_b_user)
        resp = self.client_api.get(f"/api/offers/{self.offer.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_technician_offer_access_denied(self):
        self.client_api.force_authenticate(user=self.tech_b_user)
        resp = self.client_api.get(f"/api/technician/offers/{self.offer.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_malformed_uuid_safe(self):
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get("/api/offers/not-a-uuid/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_offer_detail_no_private_fields(self):
        """Offer detail should not expose emails, phones, etc."""
        self.client_api.force_authenticate(user=self.client_user)
        resp = self.client_api.get(f"/api/offers/{self.offer.id}/")
        self.assertNotIn("email", str(resp.data.get("technician", {})))
        self.assertNotIn("phone", str(resp.data.get("technician", {})))
        self.assertNotIn("password", str(resp.data))
