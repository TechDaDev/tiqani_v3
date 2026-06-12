"""Tests for chat realtime helper functions."""

from unittest.mock import patch, MagicMock
from decimal import Decimal

from django.test import TestCase, override_settings

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom, ServiceChatMessage
from chat import realtime


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatRealtimeHelperTests(TestCase):
    """Test realtime helper functions."""

    def setUp(self):
        self.client_user = CustomUser.objects.create_user(
            username="client1", password="test123", role="client",
            phone_number="07500000001",
        )
        self.tech_user = CustomUser.objects.create_user(
            username="tech1", password="test123", role="technician",
            phone_number="07500000002",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_profile = TechnicianProfile.objects.create(user=self.tech_user, approved=True)
        self.room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.message = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="Test message",
        )

    def test_get_chat_room_group_format(self):
        group = realtime.get_chat_room_group(self.room.id)
        expected = f"service_chat_room_{self.room.id}"
        self.assertEqual(group, expected)

    def test_send_chat_message_created_calls_group_send(self):
        with patch("chat.realtime._send_to_group") as mock_send:
            realtime.send_chat_message_created(self.message)
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            self.assertIn("chat.message.created", str(args[1]))

    def test_send_chat_typing_calls_group_send(self):
        with patch("chat.realtime._send_to_group") as mock_send:
            realtime.send_chat_typing(self.room.id, self.client_user, True)
            mock_send.assert_called_once()

    def test_send_chat_read_calls_group_send(self):
        with patch("chat.realtime._send_to_group") as mock_send:
            realtime.send_chat_read(self.room.id, self.client_user, str(self.message.id))
            mock_send.assert_called_once()

    def test_send_price_offer_created_calls_group_send(self):
        with patch("chat.realtime._send_to_group") as mock_send:
            realtime.send_price_offer_created(self.message)
            mock_send.assert_called_once()
