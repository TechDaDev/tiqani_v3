"""Tests for review creation after completed contract."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from accounts.models import TechnicianProfile, ClientProfile
from contract.models import Contract
from ratereview.models import Review

User = get_user_model()


class ReviewCreationTest(APITestCase):
    """Tests for POST /api/reviews/."""

    def setUp(self):
        self.client = APIClient()

        # Client
        self.client_user = User.objects.create_user(
            username="client", email="c@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

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

        # Other client (unrelated)
        self.other_user = User.objects.create_user(
            username="other", email="o@t.com", password="pass123",
            role="client", phone_number="07700000003", governorate="Baghdad",
            address="Addr",
        )
        self.other_profile = ClientProfile.objects.create(user=self.other_user)

        # Create a completed contract
        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Test work",
            agreed_amount=Decimal("100000.00"),
            stage_number=1,
            start_date=timezone.now().date(),
            duration_days=7,
            client_accepted=True,
            technician_accepted=True,
            status="completed",
        )

        # Create an incomplete contract
        self.incomplete_contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Incomplete work",
            agreed_amount=Decimal("50000.00"),
            stage_number=1,
            start_date=timezone.now().date(),
            duration_days=7,
            client_accepted=False,
            technician_accepted=False,
            status="pending_acceptance",
        )

        self.create_url = "/api/reviews/"
        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.client_user)
        self.tech_auth = APIClient()
        self.tech_auth.force_authenticate(user=self.tech_user)
        self.other_auth = APIClient()
        self.other_auth.force_authenticate(user=self.other_user)

    def test_anonymous_cannot_create_review(self):
        """Anonymous users get 401."""
        response = self.client.post(self.create_url, {"contract_id": str(self.contract.id), "rating": 5}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_can_create_review_for_completed_contract(self):
        """Client can review a completed contract."""
        response = self.client_auth.post(self.create_url, {
            "contract_id": str(self.contract.id),
            "rating": 5,
            "work_quality_rating": 4,
            "communication_rating": 5,
            "title": "Great job",
            "comment": "Excellent work!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # rating is overridden by compute_overall_rating from sub-scores: (4+5)/2=4.5→4
        self.assertEqual(response.data["rating"], 4)
        self.assertTrue(response.data["is_verified"])
        review_id = response.data["id"]

        # Verify it appears in public list
        list_url = f"/api/reviews/technician/{self.tech_profile.id}/"
        resp = self.client.get(list_url)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(review_id, ids)

    def test_cannot_review_incomplete_contract(self):
        """Contract must be completed."""
        response = self.client_auth.post(self.create_url, {
            "contract_id": str(self.incomplete_contract.id),
            "rating": 4,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("completed", str(response.data).lower())

    def test_unrelated_client_cannot_review_others_contract(self):
        """Only the contract client can review."""
        response = self.other_auth.post(self.create_url, {
            "contract_id": str(self.contract.id),
            "rating": 4,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_technician_cannot_review_own_contract(self):
        """Technicians cannot review themselves (they lack client_profile)."""
        response = self.tech_auth.post(self.create_url, {
            "contract_id": str(self.contract.id),
            "rating": 5,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_review_rejected(self):
        """Only one review per contract."""
        Review.objects.create(
            contract=self.contract, reviewer=self.client_user,
            technician=self.tech_profile, rating=4,
            is_verified=True, is_public=True,
        )
        response = self.client_auth.post(self.create_url, {
            "contract_id": str(self.contract.id),
            "rating": 5,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_created_review_is_verified_for_completed_contract(self):
        """Review auto-verified when linked to completed contract."""
        response = self.client_auth.post(self.create_url, {
            "contract_id": str(self.contract.id),
            "rating": 4,
            "comment": "Verified work",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_verified"])

    def test_technician_rating_updates_after_create(self):
        """Cached rating recalculated."""
        self.assertIsNone(self.tech_profile.rate or None)
        self.client_auth.post(self.create_url, {
            "contract_id": str(self.contract.id),
            "rating": 4,
        }, format="json")
        self.tech_profile.refresh_from_db()
        self.assertEqual(self.tech_profile.rate, Decimal("4.00"))
