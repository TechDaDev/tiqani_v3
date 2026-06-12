"""Tests for chat models."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState


class ServiceChatRoomModelTests(TestCase):
    """Test ServiceChatRoom model constraints and helpers."""

    def setUp(self):
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

    def test_client_can_participate(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertTrue(room.can_participate(self.client_user))

    def test_technician_can_participate(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertTrue(room.can_participate(self.tech_user))

    def test_unrelated_user_cannot_participate(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertFalse(room.can_participate(self.other_user))

    def test_other_participant_returns_correct_user(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertEqual(room.other_participant(self.client_user), self.tech_user)
        self.assertEqual(room.other_participant(self.tech_user), self.client_user)

    def test_can_send_in_open_room(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertTrue(room.can_send(self.client_user))
        self.assertTrue(room.can_send(self.tech_user))

    def test_cannot_send_in_closed_room(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
            status=ServiceChatRoom.Status.CLOSED,
        )
        self.assertFalse(room.can_send(self.client_user))

    def test_cannot_send_in_blocked_room(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
            status=ServiceChatRoom.Status.BLOCKED,
        )
        self.assertFalse(room.can_send(self.tech_user))

    def test_mark_contract_linked_updates_status(self):
        room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        # We'll mock a contract
        from contract.models import Contract
        contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            agreed_amount=Decimal("100000.00"),
        )
        room.mark_contract_linked(contract)
        room.refresh_from_db()
        self.assertEqual(room.status, ServiceChatRoom.Status.CONTRACT_LINKED)
        self.assertEqual(room.linked_contract, contract)

    def test_active_room_uniqueness_per_pair(self):
        """Client can have multiple closed rooms but only one active."""
        ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
            status=ServiceChatRoom.Status.CLOSED,
        )
        # Creating another open room should be fine (previous is closed)
        room2 = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertEqual(room2.status, ServiceChatRoom.Status.OPEN)


class ServiceChatMessageModelTests(TestCase):
    """Test ServiceChatMessage validation and helpers."""

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

    def test_text_message_requires_body(self):
        msg = ServiceChatMessage(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="",
        )
        with self.assertRaises(ValidationError):
            msg.save()

    def test_text_message_valid_with_body(self):
        msg = ServiceChatMessage(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="Hello, this is a test message.",
        )
        msg.save()
        self.assertIsNotNone(msg.id)

    def test_price_offer_requires_amount(self):
        msg = ServiceChatMessage(
            room=self.room,
            sender=self.tech_user,
            message_type=ServiceChatMessage.MessageType.PRICE_OFFER,
            body="",
            price_amount=None,
        )
        with self.assertRaises(ValidationError):
            msg.save()

    def test_price_offer_valid_with_amount(self):
        msg = ServiceChatMessage(
            room=self.room,
            sender=self.tech_user,
            message_type=ServiceChatMessage.MessageType.PRICE_OFFER,
            body="My offer",
            price_amount=Decimal("75000.00"),
        )
        msg.save()
        self.assertIsNotNone(msg.id)

    def test_body_max_length(self):
        long_text = "x" * 2001
        msg = ServiceChatMessage(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body=long_text,
        )
        with self.assertRaises(ValidationError):
            msg.save()

    def test_can_edit_within_one_hour(self):
        msg = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="Original message",
        )
        self.assertTrue(msg.can_edit(self.client_user))

    def test_cannot_edit_others_message(self):
        msg = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.tech_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="Tech message",
        )
        self.assertFalse(msg.can_edit(self.client_user))

    def test_can_delete_as_sender(self):
        msg = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="Message to delete",
        )
        self.assertTrue(msg.can_delete(self.client_user))

    def test_safe_preview_shows_deleted(self):
        msg = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.client_user,
            message_type=ServiceChatMessage.MessageType.TEXT,
            body="Original",
            is_deleted=True,
        )
        self.assertEqual(msg.safe_preview(), "[deleted]")


class ServiceChatReadStateModelTests(TestCase):
    """Test ServiceChatReadState uniqueness and behavior."""

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

    def test_unique_together_room_user(self):
        ServiceChatReadState.objects.create(room=self.room, user=self.client_user)
        with self.assertRaises(Exception):
            ServiceChatReadState.objects.create(room=self.room, user=self.client_user)
