from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.test import override_settings


class HealthAPITest(APITestCase):
    """Tests for /api/health/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/health/"

    def test_health_returns_200(self):
        """GET /api/health/ returns 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_database_ok(self):
        """Health response includes database=ok."""
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(data["database"], "ok")

    def test_health_service_name(self):
        """Health response includes service=tiqani_v3."""
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(data["service"], "tiqani_v3")
