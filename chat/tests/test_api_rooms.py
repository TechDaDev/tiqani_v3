"""Tests for chat room REST API endpoints."""

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatRoomAPITests(TestCase):
    """Test room list and create endpoints."""

    def setUp(self):
        self.client_api = APIClient()

        self.client_user = CustomUser.objects.create_user(
            username="client1", password="test123", email="client@test.com",
            role="client", phone_number="07500000001",
        )
        self.tech_user = CustomUser.objects.create_user(
            username="tech1", password="test123", email="tech@test.com",
            role="technician", phone_number="07500000002",
        )
        self.other_user = CustomUser.objects.create_user(
            username="other", password="test123", email="other@test.com",
            role="client", phone_number="07500000003",
        )

        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_profile = TechnicianProfile.objects.create(user=self.tech_user, approved=True)

        self.room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )

        # Generate tokens directly
        self.client_token = str(AccessToken.for_user(self.client_user))
        self.tech_token = str(AccessToken.for_user(self.tech_user))

    def _auth(self, token):
        self.client_api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_unauthenticated_denied(self):
        self.client_api.credentials()
        resp = self.client_api.get("/api/chat/rooms/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_can_list_rooms(self):
        self._auth(self.client_token)
        resp = self.client_api.get("/api/chat/rooms/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_technician_can_list_rooms(self):
        self._auth(self.tech_token)
        resp = self.client_api.get("/api/chat/rooms/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unrelated_user_cannot_see_room(self):
        other_token = str(AccessToken.for_user(self.other_user))
        self._auth(other_token)
        resp = self.client_api.get(f"/api/chat/rooms/{self.room.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_can_create_room(self):
        self._auth(self.client_token)
        resp = self.client_api.post("/api/chat/rooms/", {
            "technician_id": str(self.tech_profile.id),
            "initial_message": "I need your services!",
        }, format="json")
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_technician_cannot_create_room(self):
        self._auth(self.tech_token)
        resp = self.client_api.post("/api/chat/rooms/", {
            "technician_id": str(self.tech_profile.id),
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_can_retrieve_room(self):
        self._auth(self.client_token)
        resp = self.client_api.get(f"/api/chat/rooms/{self.room.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(str(resp.data["id"]), str(self.room.id))
