"""Tests for chat notification integration.

Uses TestCase with captureOnCommitCallbacks so transaction.on_commit
callbacks fire without the FK truncation issues of TransactionTestCase.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.db import transaction

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom, ServiceChatMessage
from chat import services as svc
from notification.models import Notification


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatNotificationTests(TestCase):
    """Test that chat actions create notifications."""

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
        self.room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )

    def test_message_creates_notification_for_other_participant(self):
        # Service layer uses transaction.on_commit, so capture callbacks
        with transaction.atomic(), self.captureOnCommitCallbacks(execute=True):
            svc.create_message(room=self.room, sender=self.client_user, body="Hello!")

        # Check notification was created for technician
        notif = Notification.objects.filter(recipient=self.tech_user).first()
        self.assertIsNotNone(notif)
        self.assertIn("New message", notif.title)

    def test_price_offer_creates_notification_for_client(self):
        with transaction.atomic(), self.captureOnCommitCallbacks(execute=True):
            svc.create_price_offer(
                room=self.room,
                technician_user=self.tech_user,
                amount="75000.00",
            )

        notif = Notification.objects.filter(recipient=self.client_user).first()
        self.assertIsNotNone(notif)
        self.assertIn("Price offer", notif.title)

    def test_accepted_offer_notifies_technician(self):
        with transaction.atomic(), self.captureOnCommitCallbacks(execute=True):
            offer, _ = svc.create_price_offer(
                room=self.room,
                technician_user=self.tech_user,
                amount="75000.00",
            )
        with transaction.atomic(), self.captureOnCommitCallbacks(execute=True):
            svc.accept_price_offer(
                room=self.room,
                client_user=self.client_user,
                message_id=offer.id,
            )

        notif = Notification.objects.filter(recipient=self.tech_user).first()
        # Should have a notification about acceptance
        accepted_notifs = Notification.objects.filter(
            recipient=self.tech_user,
            notification_type=Notification.Type.CONTRACT_ACCEPTED,
        )
        self.assertGreaterEqual(accepted_notifs.count(), 1)
