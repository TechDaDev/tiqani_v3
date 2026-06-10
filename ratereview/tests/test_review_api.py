from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.test import override_settings

from accounts.models import TechnicianProfile, ClientProfile
from ratereview.models import Review

User = get_user_model()


class ReviewAPITest(APITestCase):
    """Tests for public review endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Create reviewer (client)
        self.reviewer = User.objects.create_user(
            username="reviewer", email="reviewer@example.com",
            password="Testpass123", role="client",
            phone_number="07701234567", governorate="Baghdad", address="Addr",
            first_name="John", last_name="Doe",
        )
        ClientProfile.objects.create(user=self.reviewer)

        # Create technician
        self.tech_user = User.objects.create_user(
            username="tech", email="tech@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234568", governorate="Basra", address="Addr2",
        )
        self.technician = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
        )

        # Create public review
        self.public_review = Review.objects.create(
            reviewer=self.reviewer,
            technician=self.technician,
            rating=5,
            comment="Great work!",
            is_public=True,
        )

        # Create private review
        self.private_review = Review.objects.create(
            reviewer=self.reviewer,
            technician=self.technician,
            rating=3,
            comment="Not shared",
            is_public=False,
        )

    def test_public_reviews_appear_in_technician_list(self):
        """Public reviews appear in technician review list."""
        url = f"/api/reviews/technician/{self.technician.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(self.public_review.id), ids)

    def test_private_reviews_do_not_appear(self):
        """Private reviews do not appear in technician review list."""
        url = f"/api/reviews/technician/{self.technician.id}/"
        response = self.client.get(url)
        ids = [r["id"] for r in response.data["results"]]
        self.assertNotIn(str(self.private_review.id), ids)

    def test_review_detail_public(self):
        """Review detail returns 200 for public review."""
        url = f"/api/reviews/{self.public_review.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["comment"], "Great work!")

    def test_review_detail_private_returns_404(self):
        """Review detail returns 404 for private review."""
        url = f"/api/reviews/{self.private_review.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
