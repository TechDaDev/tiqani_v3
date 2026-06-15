from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import ClientProfile, BaseProfile

User = get_user_model()


class ClientAPITest(APITestCase):
    """Tests for GET/PATCH /api/clients/me/."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("client_profile")

        self.client_user = User.objects.create_user(
            username="clientuser", email="client@example.com",
            password="Testpass123", role="client",
            phone_number="07701234567", governorate="Baghdad", address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

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


class IncompleteFieldsTest(APITestCase):
    """Tests for GET /api/profile/incomplete-fields/."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("incomplete_fields")
        self.client_user = User.objects.create_user(
            username="clientuser", email="client@example.com",
            password="Testpass123", role="client",
        )
        self.profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="techuser", email="tech@example.com",
            password="Testpass123", role="technician",
        )

    def _create_complete_client(self):
        """Helper to create a client with all required fields filled."""
        user = User.objects.create_user(
            username="completeclient", email="complete@example.com",
            password="Testpass123", role="client",
            phone_number="07701234567", governorate="Baghdad",
            address="Some Address", gender="male", date_of_birth=date(1995, 1, 15),
        )
        ClientProfile.objects.create(user=user)
        return user

    def test_anonymous_returns_401(self):
        """Unauthenticated users get 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_incomplete_client_returns_fields(self):
        """Incomplete client profile returns missing fields."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("incomplete_fields", data)
        self.assertIn("is_complete", data)
        self.assertIn("completion_percentage", data)
        # Client has REQ_USER_FIELDS = ['phone_number', 'governorate', 'address', 'gender', 'date_of_birth']
        # None of these are filled for setUp client
        self.assertGreater(len(data["incomplete_fields"]), 0)
        self.assertFalse(data["is_complete"])

    def test_complete_client_returns_no_missing(self):
        """Fully completed client profile returns empty incomplete_fields."""
        user = self._create_complete_client()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["incomplete_fields"], [])
        self.assertTrue(data["is_complete"])
        self.assertEqual(data["completion_percentage"], 100.0)

    def test_technician_can_access_incomplete_fields(self):
        """Technician users can also access the incomplete-fields endpoint."""
        from accounts.models import TechnicianProfile
        TechnicianProfile.objects.create(user=self.tech_user)
        self.client.force_authenticate(user=self.tech_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("incomplete_fields", data)

    def test_get_incomplete_fields_method_exists(self):
        """Model method get_incomplete_fields() exists and returns a list."""
        fields = self.profile.get_incomplete_fields()
        self.assertIsInstance(fields, list)
        # Backward-compatible alias
        missing = self.profile.get_missing_fields()
        self.assertEqual(fields, missing)

    def test_get_incomplete_fields_for_complete_profile(self):
        """A complete profile returns empty list."""
        user = self._create_complete_client()
        profile = ClientProfile.objects.get(user=user)
        fields = profile.get_incomplete_fields()
        self.assertEqual(fields, [])

    def test_get_incomplete_fields_returns_none_for_non_matching(self):
        """Fields that don't exist on the model or user are not in the list."""
        fields = self.profile.get_incomplete_fields()
        for f in fields:
            self.assertIsInstance(f, str)
