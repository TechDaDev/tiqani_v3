"""
Tests for dealership media security — sensitive file fields not exposed publicly.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from dealership.models import (
    DealershipProfile,
    DealershipGuarantee,
)
from wallet.models import Wallet

User = get_user_model()


class DealershipMediaSecurityTest(TestCase):
    """Verify sensitive dealership files are not exposed to unauthorized users."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin_media", password="admin123",
        )
        cls.dealer = User.objects.create_user(
            username="dealer_media", password="dealer123", role="dealership",
        )
        cls.profile = DealershipProfile.objects.create(
            user=cls.dealer,
            business_name="Media Test",
            owner_name="Test",
            phone="07700000999",
            governorate="Baghdad",
            address="Test",
            status=DealershipProfile.Status.ACTIVE,
            active=True,
        )
        cls.guarantee = DealershipGuarantee.objects.create(
            dealership=cls.profile,
            cash_amount=Decimal("100000"),
            status=DealershipGuarantee.Status.PENDING,
        )
        cls.client_user = User.objects.create_user(
            username="client_media", password="client123", role="client",
        )
        Wallet.objects.create(user=cls.client_user, balance=Decimal("1000000"))

    def setUp(self):
        self.client = APIClient()

    def test_admin_dealership_list_requires_auth(self):
        """Admin dealership list endpoint requires authentication."""
        resp = self.client.get("/api/admin/dealerships/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_cannot_access_guarantee_admin_actions(self):
        """Client user cannot access dealership guarantee admin endpoints."""
        self.client.force_authenticate(self.client_user)
        resp = self.client.post(
            f"/api/admin/dealership-guarantees/{self.guarantee.id}/verify/",
            {}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_finance_admin_can_see_guarantees(self):
        """Finance admin can access guarantee admin endpoints."""
        self.client.force_authenticate(self.admin)
        resp = self.client.get(
            f"/api/admin/dealerships/{self.profile.id}/guarantees/",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_sensitive_file_fields_not_in_list_serializer(self):
        """Admin list serializer does not expose sensitive document fields."""
        from dealership.serializers import AdminDealershipListSerializer
        serializer = AdminDealershipListSerializer(self.profile)
        data = serializer.data
        self.assertNotIn(
            "document_file", data,
            "Document file should not be in dealership list serializer",
        )
