"""Technician API tests for ServiceRequest — inbox, detail, accept, decline."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest

User = get_user_model()


class TechnicianRequestApiTest(APITestCase):
    """Test all technician-facing request endpoints."""

    def setUp(self):
        self.api = APIClient()

        # Users
        self.client_user = User.objects.create_user(
            username="tc_client", email="tc_c@t.com", password="pass123",
            role="client", phone_number="07500000600", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tc_tech", email="tc_t@t.com", password="pass123",
            role="technician", phone_number="07500000601", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, job_title="Tech", about="Test",
            years_of_expertise=3, approved=True, is_available=True,
        )

        self.tech2_user = User.objects.create_user(
            username="tc_tech2", email="tc_t2@t.com", password="pass123",
            role="technician", phone_number="07500000602", governorate="Baghdad",
            address="Addr",
        )
        self.tech2_profile = TechnicianProfile.objects.create(
            user=self.tech2_user, job_title="Tech2", about="Test2",
            years_of_expertise=2, approved=True, is_available=True,
        )

        # Requests assigned to tech_user
        self.pending_req = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Pending Request", description="Please help",
        )
        self.accepted_req = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Accepted Request", description="Already accepted",
            status=ServiceRequest.Status.ACCEPTED,
        )
        self.declined_req = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Declined Request", description="Already declined",
            status=ServiceRequest.Status.DECLINED,
        )

        # Request assigned to tech2 (for IDOR)
        self.other_tech_req = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech2_profile,
            title="Other Tech Request", description="Not mine",
        )

    def _auth_as_tech(self):
        self.api.force_authenticate(user=self.tech_user)

    def _auth_as_tech2(self):
        self.api.force_authenticate(user=self.tech2_user)

    def _auth_as_client(self):
        self.api.force_authenticate(user=self.client_user)

    # ---- Authentication ----

    def test_unauthenticated_inbox_returns_401(self):
        response = self.api.get("/api/technician/requests/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- Inbox ----

    def test_technician_sees_assigned_requests_only(self):
        self._auth_as_tech()
        response = self.api.get("/api/technician/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data]
        self.assertIn(str(self.pending_req.id), ids)
        self.assertNotIn(str(self.other_tech_req.id), ids)

    def test_client_cannot_access_technician_inbox(self):
        self._auth_as_client()
        response = self.api.get("/api/technician/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inbox_status_filter(self):
        self._auth_as_tech()
        response = self.api.get("/api/technician/requests/?status=ACCEPTED")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data:
            self.assertEqual(r["status"], "ACCEPTED")

    # ---- Detail ----

    def test_technician_can_view_assigned_request(self):
        self._auth_as_tech()
        response = self.api.get(
            f"/api/technician/requests/{self.pending_req.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_cannot_view_other_technician_request(self):
        self._auth_as_tech()
        response = self.api.get(
            f"/api/technician/requests/{self.other_tech_req.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_detail_returns_404(self):
        self._auth_as_tech()
        response = self.api.get(
            "/api/technician/requests/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- Accept ----

    def test_technician_can_accept_pending(self):
        self._auth_as_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.pending_req.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ACCEPTED")

    def test_technician_cannot_accept_already_accepted(self):
        self._auth_as_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.accepted_req.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_technician_cannot_accept_other_technician_request(self):
        self._auth_as_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.other_tech_req.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_cannot_accept(self):
        self._auth_as_client()
        response = self.api.post(
            f"/api/technician/requests/{self.pending_req.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- Decline ----

    def test_technician_can_decline_pending(self):
        self._auth_as_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.pending_req.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "DECLINED")

    def test_technician_cannot_decline_already_declined(self):
        self._auth_as_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.declined_req.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_technician_cannot_decline_other_technician_request(self):
        self._auth_as_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.other_tech_req.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_cannot_decline(self):
        self._auth_as_client()
        response = self.api.post(
            f"/api/technician/requests/{self.pending_req.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
