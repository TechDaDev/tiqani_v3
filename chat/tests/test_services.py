"""Tests for chat service layer."""

from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.db import transaction

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom, ServiceChatMessage, ServiceChatReadState
from chat import services as svc


class ChatServiceTests(TestCase):
    """Test chat service functions."""

    def setUp(self):
        self.client_user = CustomUser.objects.create_user(
            username="client1", password="test123", email="client@test.com",
            role="client", phone_number="07500000001",
        )
        self.tech_user = CustomUser.objects.create_user(
            username="tech1", password="test123", email="tech@test.com",
            role="technician", phone_number="07500000002",
        )
        self.other_client = CustomUser.objects.create_user(
            username="otherclient", password="test123", email="other@test.com",
            role="client", phone_number="07500000003",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_profile = TechnicianProfile.objects.create(user=self.tech_user, approved=True)
        ClientProfile.objects.create(user=self.other_client)

    def test_client_creates_room(self):
        room, created = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertTrue(created)
        self.assertEqual(room.status, ServiceChatRoom.Status.OPEN)

    def test_existing_room_returned(self):
        room1, created1 = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertTrue(created1)
        room2, created2 = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertFalse(created2)
        self.assertEqual(room1.id, room2.id)

    def test_create_message_updates_last_message_at(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        self.assertIsNone(room.last_message_at)
        message, created = svc.create_message(
            room=room,
            sender=self.client_user,
            body="Hello!",
        )
        self.assertTrue(created)
        room.refresh_from_db()
        self.assertIsNotNone(room.last_message_at)

    def test_technician_sends_price_offer(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        message, created = svc.create_price_offer(
            room=room,
            technician_user=self.tech_user,
            amount="75000.00",
            currency="IQD",
            description="Installation service",
        )
        self.assertTrue(created)
        self.assertEqual(message.message_type, ServiceChatMessage.MessageType.PRICE_OFFER)
        self.assertEqual(message.price_amount, Decimal("75000.00"))

        room.refresh_from_db()
        self.assertEqual(room.status, ServiceChatRoom.Status.PROPOSAL_CREATED)

    def test_client_accepts_price_offer(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        offer, _ = svc.create_price_offer(
            room=room,
            technician_user=self.tech_user,
            amount="75000.00",
        )
        offer_msg, accept_msg = svc.accept_price_offer(
            room=room,
            client_user=self.client_user,
            message_id=offer.id,
        )
        self.assertEqual(accept_msg.message_type, ServiceChatMessage.MessageType.PRICE_ACCEPTED)
        self.assertEqual(accept_msg.price_amount, Decimal("75000.00"))

    def test_link_contract_validates_participants(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        from contract.models import Contract
        contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            agreed_amount=Decimal("75000.00"),
        )
        svc.link_contract_to_room(room, contract, self.client_user)
        room.refresh_from_db()
        self.assertEqual(room.status, ServiceChatRoom.Status.CONTRACT_LINKED)
        self.assertEqual(room.linked_contract, contract)

    def test_close_room_prevents_messages(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        svc.close_room(room, self.client_user)
        room.refresh_from_db()
        self.assertEqual(room.status, ServiceChatRoom.Status.CLOSED)
        self.assertFalse(room.can_send(self.client_user))

    def test_mark_room_read_updates_state(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        svc.create_message(room=room, sender=self.tech_user, body="Hi client!")
        svc.mark_room_read(room, self.client_user)
        read_state = ServiceChatReadState.objects.get(room=room, user=self.client_user)
        self.assertEqual(read_state.unread_count, 0)
        self.assertIsNotNone(read_state.last_read_at)

    def test_technician_cannot_initiate_room(self):
        with self.assertRaises(ValueError):
            svc.get_or_create_chat_room(
                client_user=self.tech_user,
                technician_profile=self.tech_profile,
                created_by=self.tech_user,
            )

    def test_unread_count_increments(self):
        room, _ = svc.get_or_create_chat_room(
            client_user=self.client_user,
            technician_profile=self.tech_profile,
            created_by=self.client_user,
        )
        # Client sends a message - tech should have unread
        svc.create_message(room=room, sender=self.client_user, body="Hello tech!")
        tech_read = ServiceChatReadState.objects.get(room=room, user=self.tech_user)
        self.assertEqual(tech_read.unread_count, 1)

        # Tech sends a message - client should have unread
        svc.create_message(room=room, sender=self.tech_user, body="Hi client!")
        client_read = ServiceChatReadState.objects.get(room=room, user=self.client_user)
        self.assertEqual(client_read.unread_count, 1)
