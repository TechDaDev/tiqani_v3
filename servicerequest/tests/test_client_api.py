"""Client API tests for ServiceRequest — create, list, detail, cancel, withdraw."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest

User = get_user_model()


class ClientRequestApiTest(APITestCase):
    """Test all client-facing request endpoints."""

    def setUp(self):
        self.client_api = APIClient()

        # Client user
        self.client_user = User.objects.create_user(
            username="api_client", email="api_c@t.com", password="pass123",
            role="client", phone_number="07500000500", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        # Technician
        self.tech_user = User.objects.create_user(
            username="api_tech", email="api_t@t.com", password="pass123",
            role="technician", phone_number="07500000501", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, job_title="Tech", about="Test",
            years_of_expertise=3, approved=True, is_available=True,
        )

        # Second client for IDOR
        self.client2_user = User.objects.create_user(
            username="api_client2", email="api_c2@t.com", password="pass123",
            role="client", phone_number="07500000502", governorate="Baghdad",
            address="Addr",
        )
        self.client2_profile = ClientProfile.objects.create(user=self.client2_user)

        # Second technician for IDOR
        self.tech2_user = User.objects.create_user(
            username="api_tech2", email="api_t2@t.com", password="pass123",
            role="technician", phone_number="07500000503", governorate="Baghdad",
            address="Addr",
        )
        self.tech2_profile = TechnicianProfile.objects.create(
            user=self.tech2_user, job_title="Tech2", about="Test2",
            years_of_expertise=2, approved=True, is_available=True,
        )

        # A request owned by client2 (for IDOR)
        self.other_request = ServiceRequest.objects.create(
            client=self.client2_profile, technician=self.tech_profile,
            title="Other Request", description="Other desc",
        )

        # A request owned by client assigned to tech2
        self.other_tech_request = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech2_profile,
            title="Cross Tech Request", description="Cross tech",
        )

    def _auth_as_client(self):
        self.client_api.force_authenticate(user=self.client_user)

    def _auth_as_client2(self):
        self.client_api.force_authenticate(user=self.client2_user)

    def _auth_as_technician(self):
        self.client_api.force_authenticate(user=self.tech_user)

    def _create_request(self):
        return self.client_api.post(
            "/api/requests/",
            {
                "technician": str(self.tech_user.id),
                "title": "Fix my AC",
                "description": "AC not working properly.",
            },
            format="json",
        )

    # ---- Authentication ----

    def test_unauthenticated_create_returns_401(self):
        response = self.client_api.post("/api/requests/", {"title": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_list_returns_401(self):
        response = self.client_api.get("/api/requests/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_detail_returns_401(self):
        response = self.client_api.get(f"/api/requests/{self.other_request.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- Create ----

    def test_client_can_create_request(self):
        self._auth_as_client()
        response = self._create_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["title"], "Fix my AC")

    def test_technician_cannot_create_request(self):
        self._auth_as_technician()
        response = self._create_request()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_missing_title_returns_400(self):
        self._auth_as_client()
        response = self.client_api.post(
            "/api/requests/",
            {"technician": str(self.tech_user.id), "description": "Test"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_description_returns_400(self):
        self._auth_as_client()
        response = self.client_api.post(
            "/api/requests/",
            {"technician": str(self.tech_user.id), "title": "Test"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_technician_returns_400(self):
        self._auth_as_client()
        response = self.client_api.post(
            "/api/requests/",
            {
                "technician": "00000000-0000-0000-0000-000000000000",
                "title": "Test",
                "description": "Test description",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_unapproved_technician_returns_400(self):
        self.tech_profile.approved = False
        self.tech_profile.save()
        self._auth_as_client()
        response = self._create_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_unavailable_technician_returns_400(self):
        self.tech_profile.is_available = False
        self.tech_profile.save()
        self._auth_as_client()
        response = self._create_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_optional_fields(self):
        self._auth_as_client()
        response = self.client_api.post(
            "/api/requests/",
            {
                "technician": str(self.tech_user.id),
                "title": "Test",
                "description": "Test description",
                "governorate": "Baghdad",
                "service_address": "123 Main St",
                "preferred_date": "2026-07-01",
                "preferred_time": "10:00",
                "is_urgent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ---- List ----

    def test_client_lists_own_requests_only(self):
        self._auth_as_client()
        # Create one request for this client
        self._create_request()
        response = self.client_api.get("/api/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for req in response.data:
            client = req.get("client", {})
            self.assertEqual(client.get("user_id"), str(self.client_user.id))

    def test_client_cannot_see_other_client_requests(self):
        self._auth_as_client()
        response = self.client_api.get("/api/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data]
        self.assertNotIn(str(self.other_request.id), ids)

    def test_list_with_status_filter(self):
        self._auth_as_client()
        sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Accepted", description="Already accepted",
            status=ServiceRequest.Status.ACCEPTED,
        )
        self._create_request()
        response = self.client_api.get("/api/requests/?status=ACCEPTED")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data]
        self.assertIn(str(sr.id), ids)
        for r in response.data:
            self.assertEqual(r["status"], "ACCEPTED")

    # ---- Detail ----

    def test_client_can_view_own_request(self):
        self._auth_as_client()
        create_resp = self._create_request()
        sr_id = create_resp.data["id"]
        response = self.client_api.get(f"/api/requests/{sr_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Fix my AC")

    def test_client_cannot_view_other_client_request(self):
        self._auth_as_client()
        response = self.client_api.get(f"/api/requests/{self.other_request.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- Cancel ----

    def test_client_can_cancel_pending_request(self):
        self._auth_as_client()
        create_resp = self._create_request()
        sr_id = create_resp.data["id"]
        response = self.client_api.post(f"/api/requests/{sr_id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CANCELLED")

    def test_client_cannot_cancel_other_client_request(self):
        self._auth_as_client()
        response = self.client_api.post(
            f"/api/requests/{self.other_request.id}/cancel/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_cannot_cancel_accepted_request(self):
        self._auth_as_client()
        sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Accepted", description="Desc",
            status=ServiceRequest.Status.ACCEPTED,
        )
        response = self.client_api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_technician_cannot_cancel(self):
        self._auth_as_technician()
        sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Pending", description="Desc",
        )
        response = self.client_api.post(f"/api/requests/{sr.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- Withdraw ----

    def test_client_can_withdraw_pending_request(self):
        self._auth_as_client()
        create_resp = self._create_request()
        sr_id = create_resp.data["id"]
        response = self.client_api.post(f"/api/requests/{sr_id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "WITHDRAWN")

    def test_client_cannot_withdraw_other_client_request(self):
        self._auth_as_client()
        response = self.client_api.post(
            f"/api/requests/{self.other_request.id}/withdraw/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_cannot_withdraw_accepted_request(self):
        self._auth_as_client()
        sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Accepted", description="Desc",
            status=ServiceRequest.Status.ACCEPTED,
        )
        response = self.client_api.post(f"/api/requests/{sr.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # ---- Nonexistent ----

    def test_nonexistent_request_detail_returns_404(self):
        self._auth_as_client()
        response = self.client_api.get(
            "/api/requests/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_cancel_returns_404(self):
        self._auth_as_client()
        response = self.client_api.post(
            "/api/requests/00000000-0000-0000-0000-000000000000/cancel/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- Malformed UUID ----

    def test_create_malformed_technician_uuid_returns_400(self):
        self._auth_as_client()
        response = self.client_api.post(
            "/api/requests/",
            {"technician": "not-a-uuid", "title": "Test", "description": "Desc"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
