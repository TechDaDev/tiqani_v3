"""Tests for chat permission classes."""

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from accounts.models import CustomUser
from chat.permissions import (
    IsClientUser,
    IsTechnicianUser,
    CanCreateRoom,
)


class ChatPermissionTests(TestCase):
    """Test permission classes."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client_user = CustomUser.objects.create_user(
            username="client1", password="test123", role="client",
            phone_number="07500000001",
        )
        self.tech_user = CustomUser.objects.create_user(
            username="tech1", password="test123", role="technician",
            phone_number="07500000002",
        )

    def test_is_client_user_allows_client(self):
        request = self.factory.get("/")
        request.user = self.client_user
        perm = IsClientUser()
        self.assertTrue(perm.has_permission(request, None))

    def test_is_client_user_denies_technician(self):
        request = self.factory.get("/")
        request.user = self.tech_user
        perm = IsClientUser()
        self.assertFalse(perm.has_permission(request, None))

    def test_is_technician_user_allows_technician(self):
        request = self.factory.get("/")
        request.user = self.tech_user
        perm = IsTechnicianUser()
        self.assertTrue(perm.has_permission(request, None))

    def test_can_create_room_allows_client(self):
        request = self.factory.get("/")
        request.user = self.client_user
        perm = CanCreateRoom()
        self.assertTrue(perm.has_permission(request, None))

    def test_can_create_room_denies_technician(self):
        request = self.factory.get("/")
        request.user = self.tech_user
        perm = CanCreateRoom()
        self.assertFalse(perm.has_permission(request, None))
