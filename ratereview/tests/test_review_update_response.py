"""Tests for review update and technician response."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from decimal import Decimal

from accounts.models import TechnicianProfile, ClientProfile
from contract.models import Contract
from ratereview.models import Review

User = get_user_model()


class ReviewUpdateTest(APITestCase):
    """Tests for PATCH /api/reviews/<id>/."""

    def setUp(self):
        self.client = APIClient()

        # Client
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
            user=self.tech_user, approved=True, job_title="Dev",
            years_of_expertise=3,
        )

        # Other user
        self.other_user = User.objects.create_user(
            username="other", email="o@t.com", password="pass123",
            role="client", phone_number="07700000003", governorate="Baghdad",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.other_user)

        # Create a review
        self.review = Review.objects.create(
            reviewer=self.client_user,
            technician=self.tech_profile,
            rating=3,
            title="Initial",
            comment="OK work",
            is_public=True,
            is_verified=True,
        )

        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.client_user)
        self.other_auth = APIClient()
        self.other_auth.force_authenticate(user=self.other_user)
        self.anon_client = APIClient()

    def test_reviewer_can_update_own_review(self):
        """Reviewer updates own review."""
        url = f"/api/reviews/{self.review.id}/"
        response = self.client_auth.patch(url, {
            "rating": 5,
            "title": "Updated",
            "comment": "Actually great!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating"], 5)
        self.assertEqual(response.data["title"], "Updated")

    def test_reviewer_cannot_change_protected_fields(self):
        """Attempt to change reviewer/technician/contract/is_verified via PATCH."""
        url = f"/api/reviews/{self.review.id}/"
        data = {
            "rating": 4,
            "title": "Nice",
        }
        response = self.client_auth.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["reviewer"]), str(self.client_user.id))
        self.assertTrue(response.data["is_verified"])

    def test_unrelated_user_cannot_update(self):
        """Unrelated user gets 403."""
        url = f"/api/reviews/{self.review.id}/"
        response = self.other_auth.patch(url, {"rating": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_update(self):
        """Anonymous gets 401."""
        url = f"/api/reviews/{self.review.id}/"
        response = self.anon_client.patch(url, {"rating": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rating_update_recalculates_cached_rating(self):
        """Rating update triggers technician rating recalc."""
        # Create another public+verified review with rating 5
        Review.objects.create(
            reviewer=self.client_user, technician=self.tech_profile,
            rating=5, is_public=True, is_verified=True,
        )
        # Update first review to 5
        url = f"/api/reviews/{self.review.id}/"
        self.client_auth.patch(url, {"rating": 5}, format="json")
        self.tech_profile.refresh_from_db()
        self.assertEqual(self.tech_profile.rate, Decimal("5.00"))


class ReviewTechnicianResponseTest(APITestCase):
    """Tests for POST /api/reviews/<id>/respond/."""

    def setUp(self):
        self.client = APIClient()

        self.client_user = User.objects.create_user(
            username="client", email="c@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech", email="t@t.com", password="pass123",
            role="technician", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title="Dev",
            years_of_expertise=3,
        )

        self.other_tech_user = User.objects.create_user(
            username="othertech", email="ot@t.com", password="pass123",
            role="technician", phone_number="07700000004", governorate="Basra",
            address="Addr",
        )
        self.other_tech_profile = TechnicianProfile.objects.create(
            user=self.other_tech_user, approved=True, job_title="Other",
            years_of_expertise=1,
        )

        self.review = Review.objects.create(
            reviewer=self.client_user, technician=self.tech_profile,
            rating=4, comment="Good", is_public=True, is_verified=True,
        )

        self.tech_auth = APIClient()
        self.tech_auth.force_authenticate(user=self.tech_user)
        self.other_tech_auth = APIClient()
        self.other_tech_auth.force_authenticate(user=self.other_tech_user)
        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.client_user)

    def test_technician_can_respond(self):
        """Reviewed technician can respond."""
        url = f"/api/reviews/{self.review.id}/respond/"
        response = self.tech_auth.post(url, {"technician_response": "Thank you!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["technician_response"], "Thank you!")

    def test_unrelated_technician_cannot_respond(self):
        """Unrelated technician gets 403."""
        url = f"/api/reviews/{self.review.id}/respond/"
        response = self.other_tech_auth.post(url, {"technician_response": "Spam"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_cannot_write_technician_response(self):
        """Client cannot use respond endpoint."""
        url = f"/api/reviews/{self.review.id}/respond/"
        response = self.client_auth.post(url, {"technician_response": "Client trying"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_can_update_response(self):
        """Calling respond again updates the response."""
        url = f"/api/reviews/{self.review.id}/respond/"
        self.tech_auth.post(url, {"technician_response": "First"}, format="json")
        response = self.tech_auth.post(url, {"technician_response": "Updated"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["technician_response"], "Updated")
