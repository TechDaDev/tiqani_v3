"""Tests for chat WebSocket consumer."""

import json
from channels.testing import WebsocketCommunicator
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom
from chat.consumers import ServiceChatConsumer
from tiqani_v3.routing import application


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatConsumerTests(TestCase):
    """Test WebSocket consumer behavior."""

    async def asyncSetUp(self):
        self.client_user = await get_user_model().objects.acreate(
            username="client1", password="test123", role="client",
            phone_number="07500000001",
        )
        self.tech_user = await get_user_model().objects.acreate(
            username="tech1", password="test123", role="technician",
            phone_number="07500000002",
        )

    def setUp(self):
        self.client_user = CustomUser.objects.create_user(
            username="client1", password="test123", email="client@test.com",
            role="client", phone_number="07500000001",
        )
        self.tech_user = CustomUser.objects.create_user(
            username="tech1", password="test123", email="tech@test.com",
            role="technician", phone_number="07500000002",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_profile = TechnicianProfile.objects.create(user=self.tech_user, approved=True)
        self.room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )

        # Generate a JWT token for the client user
        from rest_framework_simplejwt.tokens import AccessToken
        self.token = str(AccessToken.for_user(self.client_user))

    async def test_unauthenticated_rejected(self):
        """Unauthenticated user should be rejected."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/",
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_authenticated_participant_connects(self):
        """Authenticated participant should connect successfully."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/?token={self.token}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_ping_returns_pong(self):
        """Ping should return pong."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/?token={self.token}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "pong")

        await communicator.disconnect()

    async def test_connection_accepted_sent(self):
        """Connection should send connection.accepted."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/?token={self.token}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.connection.accepted")
        self.assertEqual(response["room_id"], str(self.room.id))

        await communicator.disconnect()
