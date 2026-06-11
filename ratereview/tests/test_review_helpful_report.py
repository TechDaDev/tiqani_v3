"""Tests for helpful and report actions on reviews."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import TechnicianProfile, ClientProfile
from ratereview.models import Review, ReviewHelpful, ReviewReport

User = get_user_model()


class ReviewHelpfulTest(APITestCase):
    """Tests for POST /api/reviews/<id>/helpful/."""

    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username="user1", email="u1@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username="user2", email="u2@t.com", password="pass123",
            role="client", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.user2)

        self.tech_user = User.objects.create_user(
            username="tech", email="t@t.com", password="pass123",
            role="technician", phone_number="07700000003", governorate="Basra",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
        )

        self.review = Review.objects.create(
            reviewer=self.user1, technician=self.tech_profile,
            rating=5, comment="Excellent!", is_public=True, is_verified=True,
        )

        self.auth1 = APIClient()
        self.auth1.force_authenticate(user=self.user1)
        self.auth2 = APIClient()
        self.auth2.force_authenticate(user=self.user2)

    def test_authenticated_user_can_mark_helpful(self):
        """User marks review helpful."""
        url = f"/api/reviews/{self.review.id}/helpful/"
        response = self.auth1.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["helpful_count"], 1)

    def test_duplicate_helpful_does_not_increment(self):
        """Same user cannot increment twice."""
        url = f"/api/reviews/{self.review.id}/helpful/"
        self.auth1.post(url)
        response = self.auth1.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["helpful_count"], 1)

    def test_multiple_users_can_mark_helpful(self):
        """Different users each increment."""
        url = f"/api/reviews/{self.review.id}/helpful/"
        self.auth1.post(url)
        response = self.auth2.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["helpful_count"], 2)

    def test_anonymous_cannot_mark_helpful(self):
        """Anonymous gets 401."""
        url = f"/api/reviews/{self.review.id}/helpful/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReviewReportTest(APITestCase):
    """Tests for POST /api/reviews/<id>/report/."""

    REPORT_THRESHOLD = 3

    def setUp(self):
        self.client = APIClient()

        self.reviewer = User.objects.create_user(
            username="reviewer", email="r@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.reviewer)

        self.tech_user = User.objects.create_user(
            username="tech", email="t@t.com", password="pass123",
            role="technician", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
        )

        self.review = Review.objects.create(
            reviewer=self.reviewer, technician=self.tech_profile,
            rating=4, comment="Review content", is_public=True,
        )

        self.reporters = []
        self.auth_clients = []
        for i in range(5):
            u = User.objects.create_user(
                username=f"reporter{i}", email=f"r{i}@t.com", password="pass123",
                role="client", phone_number=f"0770000000{i+3}", governorate="Basra",
                address="Addr",
            )
            ClientProfile.objects.create(user=u)
            self.reporters.append(u)
            auth = APIClient()
            auth.force_authenticate(user=u)
            self.auth_clients.append(auth)

    def test_authenticated_user_can_report(self):
        """User can report a review."""
        url = f"/api/reviews/{self.review.id}/report/"
        response = self.auth_clients[0].post(url, {"reason": "spam"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["reported"])
        self.assertEqual(response.data["reported_count"], 1)

    def test_duplicate_report_does_not_increment(self):
        """Same user cannot report twice."""
        url = f"/api/reviews/{self.review.id}/report/"
        self.auth_clients[0].post(url, {"reason": "spam"}, format="json")
        response = self.auth_clients[0].post(url, {"reason": "abuse"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["reported"])
        self.assertEqual(response.data["reported_count"], 1)

    def test_flagged_at_set_after_threshold(self):
        """Review is flagged after enough reports."""
        url = f"/api/reviews/{self.review.id}/report/"
        # 3 different reporters
        for i in range(self.REPORT_THRESHOLD):
            self.auth_clients[i].post(url, {"reason": "spam"}, format="json")

        self.review.refresh_from_db()
        self.assertEqual(self.review.reported_count, self.REPORT_THRESHOLD)
        self.assertIsNotNone(self.review.flagged_at)

    def test_anonymous_cannot_report(self):
        """Anonymous gets 401."""
        url = f"/api/reviews/{self.review.id}/report/"
        response = self.client.post(url, {"reason": "spam"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
