from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile

User = get_user_model()


class ClientAPITest(APITestCase):
    """Tests for GET/PATCH /api/clients/me/."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/clients/me/"

        self.client_user = User.objects.create_user(
            username="clientuser", email="client@example.com",
            password="Testpass123", role="client",
            phone_number="07701234567", governorate="Baghdad", address="Addr",
        )
        ClientProfile.objects.create(user=self.client_user)

        self.technician_user = User.objects.create_user(
            username="techuser", email="tech@example.com",
            password="Testpass123", role="technician",
        )

    def test_anonymous_returns_401(self):
        """Anonymous GET /api/clients/me/ returns 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_can_get_own_profile(self):
        """Authenticated client can GET /api/clients/me/."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_client_cannot_access(self):
        """Non-client user (technician) cannot access client endpoint."""
        self.client.force_authenticate(user=self.technician_user)
        response = self.client.get(self.url)
        # Depending on permission config, may return 403 or 404
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
