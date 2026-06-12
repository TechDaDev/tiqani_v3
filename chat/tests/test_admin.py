"""Tests for chat admin configuration."""

from django.test import TestCase
from django.contrib.admin import site

from chat.models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState
from chat.admin import ServiceChatRoomAdmin, ServiceChatMessageAdmin, ServiceChatReadStateAdmin


class ChatAdminTests(TestCase):
    """Test that admin classes are registered."""

    def test_chat_room_admin_registered(self):
        self.assertIn(ServiceChatRoom, site._registry)

    def test_chat_message_admin_registered(self):
        self.assertIn(ServiceChatMessage, site._registry)

    def test_chat_read_state_admin_registered(self):
        self.assertIn(ServiceChatReadState, site._registry)
