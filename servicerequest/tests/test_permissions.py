"""Permission and IDOR tests for ServiceRequest — cross-client, cross-technician, role enforcement."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest

User = get_user_model()


class ServiceRequestIDORTest(APITestCase):
    """
    Test object-level authorization to prevent Insecure Direct Object Reference.

    Proves:
    - Client A cannot view/act on Client B requests.
    - Technician A cannot view/act on Technician B requests.
    - Clients cannot call technician actions.
    - Technicians cannot call client actions.
    """

    def setUp(self):
        self.api = APIClient()

        # Client A
        self.client_a_user = User.objects.create_user(
            username="idor_ca", email="idor_ca@t.com", password="pass123",
            role="client", phone_number="07500000800", governorate="Baghdad",
            address="Addr",
        )
        self.client_a = ClientProfile.objects.create(user=self.client_a_user)

        # Client B
        self.client_b_user = User.objects.create_user(
            username="idor_cb", email="idor_cb@t.com", password="pass123",
            role="client", phone_number="07500000801", governorate="Baghdad",
            address="Addr",
        )
        self.client_b = ClientProfile.objects.create(user=self.client_b_user)

        # Technician A
        self.tech_a_user = User.objects.create_user(
            username="idor_ta", email="idor_ta@t.com", password="pass123",
            role="technician", phone_number="07500000802", governorate="Baghdad",
            address="Addr",
        )
        self.tech_a = TechnicianProfile.objects.create(
            user=self.tech_a_user, job_title="TA", about="Tech A",
            years_of_expertise=3, approved=True, is_available=True,
        )

        # Technician B
        self.tech_b_user = User.objects.create_user(
            username="idor_tb", email="idor_tb@t.com", password="pass123",
            role="technician", phone_number="07500000803", governorate="Baghdad",
            address="Addr",
        )
        self.tech_b = TechnicianProfile.objects.create(
            user=self.tech_b_user, job_title="TB", about="Tech B",
            years_of_expertise=5, approved=True, is_available=True,
        )

        # Requests
        self.ca_req = ServiceRequest.objects.create(
            client=self.client_a, technician=self.tech_a,
            title="CA Request", description="Client A to Tech A",
        )
        self.cb_req = ServiceRequest.objects.create(
            client=self.client_b, technician=self.tech_b,
            title="CB Request", description="Client B to Tech B",
        )
        self.ca_to_tb_req = ServiceRequest.objects.create(
            client=self.client_a, technician=self.tech_b,
            title="CA to TB", description="Client A to Tech B",
        )

    # ---- Client A access boundaries ----

    def test_client_a_can_view_own_request(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.get(f"/api/requests/{self.ca_req.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_client_a_cannot_view_client_b_request(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.get(f"/api/requests/{self.cb_req.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_a_cannot_cancel_client_b_request(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.post(f"/api/requests/{self.cb_req.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_a_cannot_withdraw_client_b_request(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.post(f"/api/requests/{self.cb_req.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- Technician A access boundaries ----

    def test_tech_a_can_view_assigned_request(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.get(f"/api/technician/requests/{self.ca_req.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tech_a_cannot_view_tech_b_request(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.get(f"/api/technician/requests/{self.cb_req.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tech_a_cannot_accept_tech_b_request(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.post(
            f"/api/technician/requests/{self.cb_req.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tech_a_cannot_decline_tech_b_request(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.post(
            f"/api/technician/requests/{self.cb_req.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- Cross-role enforcement ----

    def test_client_cannot_access_technician_inbox(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.get("/api/technician/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_accept_request(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.post(
            f"/api/technician/requests/{self.ca_req.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_decline_request(self):
        self.api.force_authenticate(user=self.client_a_user)
        response = self.api.post(
            f"/api/technician/requests/{self.ca_req.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_cannot_create_request(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.post(
            "/api/requests/",
            {
                "technician": str(self.tech_b_user.id),
                "title": "Test",
                "description": "Desc",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_cannot_list_client_requests(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.get("/api/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_cannot_cancel(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.post(f"/api/requests/{self.ca_req.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_cannot_withdraw(self):
        self.api.force_authenticate(user=self.tech_a_user)
        response = self.api.post(f"/api/requests/{self.ca_req.id}/withdraw/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- Anonymous ----

    def test_anonymous_cannot_access_any_protected_endpoint(self):
        endpoints = [
            ("GET", "/api/requests/"),
            ("POST", "/api/requests/"),
            ("GET", f"/api/requests/{self.ca_req.id}/"),
            ("POST", f"/api/requests/{self.ca_req.id}/cancel/"),
            ("POST", f"/api/requests/{self.ca_req.id}/withdraw/"),
            ("GET", "/api/technician/requests/"),
            ("GET", f"/api/technician/requests/{self.ca_req.id}/"),
            ("POST", f"/api/technician/requests/{self.ca_req.id}/accept/"),
            ("POST", f"/api/technician/requests/{self.ca_req.id}/decline/"),
        ]
        for method, url in endpoints:
            response = getattr(self.api, method.lower())(url)
            self.assertEqual(
                response.status_code, status.HTTP_401_UNAUTHORIZED,
                f"{method} {url} returned {response.status_code}, expected 401",
            )
