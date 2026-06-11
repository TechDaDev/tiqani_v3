"""Tests for admin moderation endpoints."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import TechnicianProfile, ClientProfile
from ratereview.models import Review

User = get_user_model()


class ReviewModerationTest(APITestCase):
    """Tests for moderation endpoints."""

    def setUp(self):
        self.client = APIClient()

        # Client reviewer
        self.client_user = User.objects.create_user(
            username="client", email="c@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.client_user)

        # Technician
        self.tech_user = User.objects.create_user(
            username="tech", email="t@t.com", password="pass123",
            role="technician", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
        )

        # Admin
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@t.com", password="admin123",
        )

        # Normal user (non-admin)
        self.normal_user = User.objects.create_user(
            username="normal", email="n@t.com", password="pass123",
            role="client", phone_number="07700000003", governorate="Baghdad",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.normal_user)

        # Create review
        self.review = Review.objects.create(
            reviewer=self.client_user, technician=self.tech_profile,
            rating=4, comment="Test review", is_public=True, is_verified=True,
        )

        self.admin_auth = APIClient()
        self.admin_auth.force_authenticate(user=self.admin_user)
        self.normal_auth = APIClient()
        self.normal_auth.force_authenticate(user=self.normal_user)

    def test_admin_can_hide_review(self):
        """Admin hides review."""
        url = f"/api/reviews/{self.review.id}/moderate/hide/"
        response = self.admin_auth.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify DB reflects the change
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_public)

        # Should be hidden from public
        detail_url = f"/api/reviews/{self.review.id}/"
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_publish_review(self):
        """Admin publishes hidden review."""
        self.review.is_public = False
        self.review.save()
        url = f"/api/reviews/{self.review.id}/moderate/publish/"
        response = self.admin_auth.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_public)

    def test_admin_can_verify_review(self):
        """Admin verifies review."""
        self.review.is_verified = False
        self.review.save()
        url = f"/api/reviews/{self.review.id}/moderate/verify/"
        response = self.admin_auth.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_verified"])

    def test_admin_can_unverify_review(self):
        """Admin unverifies review."""
        url = f"/api/reviews/{self.review.id}/moderate/unverify/"
        response = self.admin_auth.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_verified"])

    def test_non_admin_cannot_moderate(self):
        """Non-admin gets 403 on moderation endpoints."""
        urls = [
            f"/api/reviews/{self.review.id}/moderate/hide/",
            f"/api/reviews/{self.review.id}/moderate/publish/",
            f"/api/reviews/{self.review.id}/moderate/verify/",
            f"/api/reviews/{self.review.id}/moderate/unverify/",
        ]
        for url in urls:
            response = self.normal_auth.post(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                             f"Expected 403 for {url}")

    def test_hidden_review_does_not_appear_in_list(self):
        """Hidden review excluded from public list."""
        self.review.is_public = False
        self.review.save()
        list_url = f"/api/reviews/technician/{self.tech_profile.id}/"
        response = self.client.get(list_url)
        ids = [r["id"] for r in response.data["results"]]
        self.assertNotIn(str(self.review.id), ids)
