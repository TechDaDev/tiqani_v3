from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import TechnicianProfile, BaseProfile
from category.models import Category

User = get_user_model()


class TechnicianAPITest(APITestCase):
    """Tests for /api/technicians/ endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("technician_list")
        self.me_url = reverse("technician_profile")
        self.skills_url = reverse("technician_skills")
        self.incomplete_url = reverse("incomplete_fields")

        # Create an approved technician
        self.approved_user = User.objects.create_user(
            username="approvedtech", email="approved@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234567", governorate="Baghdad", address="Addr",
            first_name="Approved", last_name="Tech",
        )
        self.approved_profile = TechnicianProfile.objects.create(
            user=self.approved_user, approved=True,
            job_title="Plumber", about="Expert plumber",
            years_of_expertise=5,
        )
        # Mark profile complete (bypass FileField requirement for tests)
        TechnicianProfile.objects.filter(pk=self.approved_profile.pk).update(is_complete=True)
        self.approved_profile.refresh_from_db()

        # Create an unapproved technician
        self.unapproved_user = User.objects.create_user(
            username="unapprovedtech", email="unapproved@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234568", governorate="Basra", address="Addr2",
        )
        self.unapproved_profile = TechnicianProfile.objects.create(
            user=self.unapproved_user, approved=False,
        )

        # Create a non-technician user
        self.client_user = User.objects.create_user(
            username="clientuser", email="client@example.com",
            password="Testpass123", role="client",
        )

    def test_public_list_returns_200(self):
        """Public GET /api/technicians/ returns 200."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_approved_technician_in_public_list(self):
        """Approved technician appears in public list."""
        response = self.client.get(self.list_url)
        results = response.data["results"]
        user_ids = [r["user_id"] for r in results]
        self.assertIn(str(self.approved_user.id), user_ids)

    def test_unapproved_technician_not_in_public_list(self):
        """Unapproved technician does not appear in public list."""
        response = self.client.get(self.list_url)
        results = response.data["results"]
        user_ids = [r["user_id"] for r in results]
        self.assertNotIn(str(self.unapproved_user.id), user_ids)

    def test_technician_can_get_own_profile(self):
        """Technician can GET /api/technicians/me/."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_can_patch_own_profile(self):
        """Technician can PATCH /api/technicians/me/."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.patch(self.me_url, {"job_title": "Senior Plumber"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.approved_profile.refresh_from_db()
        self.assertEqual(self.approved_profile.job_title, "Senior Plumber")

    def test_anonymous_me_returns_401(self):
        """Anonymous GET /api/technicians/me/ returns 401."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_technician_profile_rejects_client_user(self):
        """Client user cannot access technician profile endpoint."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.me_url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_technician_get_incomplete_fields(self):
        """Incomplete technician returns missing fields, no 500."""
        self.client.force_authenticate(user=self.unapproved_user)
        response = self.client.get(self.incomplete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("incomplete_fields", data)
        self.assertIn("is_complete", data)
        # Unapproved tech has minimal profile
        self.assertGreater(len(data["incomplete_fields"]), 0)
        self.assertFalse(data["is_complete"])

    def test_technician_skills_get(self):
        """Technician can GET own skills."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.get(self.skills_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_skills_rejects_client(self):
        """Client user cannot access technician skills endpoint."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.skills_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_can_patch_skills(self):
        """Technician can PATCH skills with valid data."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.patch(self.skills_url, {"categories": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
