"""Security tests for ServiceRequest — private field exposure, safe error responses."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from servicerequest.models import ServiceRequest

User = get_user_model()


class ServiceRequestSecurityTest(APITestCase):
    """Verify no private fields leak through any API response."""

    PRIVATE_KEYS = ["email", "phone", "phone_number", "password",
                    "identification_documents", "is_superuser", "is_staff",
                    "last_login", "date_joined", "user_permissions", "groups"]

    def setUp(self):
        self.api = APIClient()

        self.client_user = User.objects.create_user(
            username="sec_client", email="sec_c@t.com", password="secret123",
            role="client", phone_number="07500000900", governorate="Baghdad",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="sec_tech", email="sec_t@t.com", password="secret456",
            role="technician", phone_number="07500000901", governorate="Baghdad",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, job_title="SecTech", about="Security test",
            years_of_expertise=5, approved=True, is_available=True,
        )

        self.sr = ServiceRequest.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            title="Security Test", description="Testing field exposure",
            service_address="Private Address",
        )

    def _check_no_private_keys(self, data, path=""):
        """Recursively check that no private keys appear in the response."""
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{path}.{key}" if path else key
                lower_key = key.lower()
                for pk in self.PRIVATE_KEYS:
                    if pk in lower_key:
                        self.fail(f"Private key '{full_key}' exposed in response")
                self._check_no_private_keys(value, full_key)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._check_no_private_keys(item, f"{path}[{i}]")

    def _auth_client(self):
        self.api.force_authenticate(user=self.client_user)

    def _auth_tech(self):
        self.api.force_authenticate(user=self.tech_user)

    def test_client_list_no_private_fields(self):
        self._auth_client()
        response = self.api.get("/api/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_no_private_keys(response.data)

    def test_client_detail_no_private_fields(self):
        self._auth_client()
        response = self.api.get(f"/api/requests/{self.sr.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_no_private_keys(response.data)

    def test_client_create_response_no_private_fields(self):
        self._auth_client()
        response = self.api.post(
            "/api/requests/",
            {
                "technician": str(self.tech_user.id),
                "title": "New Request",
                "description": "Test desc",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._check_no_private_keys(response.data)

    def test_technician_inbox_no_private_fields(self):
        self._auth_tech()
        response = self.api.get("/api/technician/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_no_private_keys(response.data)

    def test_technician_detail_no_private_fields(self):
        self._auth_tech()
        response = self.api.get(f"/api/technician/requests/{self.sr.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_no_private_keys(response.data)

    def test_technician_accept_response_no_private_fields(self):
        self._auth_tech()
        response = self.api.post(
            f"/api/technician/requests/{self.sr.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_no_private_keys(response.data)

    def test_error_response_does_not_leak_details(self):
        """404 responses should not reveal why or expose internals."""
        self._auth_client()
        response = self.api.get(
            "/api/requests/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        body = str(response.data)
        self.assertNotIn("Traceback", body)
        self.assertNotIn("DoesNotExist", body)

    def test_no_password_in_any_response(self):
        """Ensure raw password NEVER appears in responses."""
        self._auth_client()
        response = self.api.get("/api/requests/")
        body_str = str(response.data)
        self.assertNotIn("secret123", body_str)
        self.assertNotIn("secret456", body_str)
