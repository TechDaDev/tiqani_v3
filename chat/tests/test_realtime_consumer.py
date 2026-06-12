"""Tests for chat WebSocket consumer.

Uses TransactionTestCase with available_apps so that DB flush is
limited to chat and accounts tables only.  This avoids PostgreSQL FK
cascade errors from unrelated tables (contract, wallet) while giving
each async WebSocket test a fresh, committed DB state visible to the
WebsocketCommunicator's async event loop.
"""

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom
from tiqani_v3.routing import application


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatConsumerTests(TransactionTestCase):
    """Test WebSocket consumer behavior."""

    available_apps = ["chat", "accounts"]

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
        try:
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
        finally:
            await communicator.disconnect()

    async def test_authenticated_participant_connects(self):
        """Authenticated participant should connect successfully."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/?token={self.token}",
        )
        try:
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
        finally:
            await communicator.disconnect()

    async def test_ping_returns_pong(self):
        """Ping should return pong."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/?token={self.token}",
        )
        try:
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Drain the connection.accepted message first, then send ping
            welcome = await communicator.receive_json_from()
            self.assertEqual(welcome["type"], "chat.connection.accepted")

            await communicator.send_json_to({"type": "ping"})
            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "pong")
        finally:
            await communicator.disconnect()

    async def test_connection_accepted_sent(self):
        """Connection should send connection.accepted."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/rooms/{self.room.id}/?token={self.token}",
        )
        try:
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "chat.connection.accepted")
            self.assertEqual(response["room_id"], str(self.room.id))
        finally:
            await communicator.disconnect()
