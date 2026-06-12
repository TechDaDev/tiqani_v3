"""Tests for price offer REST API endpoints."""

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom, ServiceChatMessage


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatPriceOfferAPITests(TestCase):
    """Test price offer creation and acceptance."""

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
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_profile = TechnicianProfile.objects.create(user=self.tech_user, approved=True)

        self.room = ServiceChatRoom.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            created_by=self.client_user,
        )

        self.client_token = str(AccessToken.for_user(self.client_user))
        self.tech_token = str(AccessToken.for_user(self.tech_user))

    def _auth(self, token):
        self.client_api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_technician_can_send_price_offer(self):
        self._auth(self.tech_token)
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/price-offers/",
            {"amount": "75000.00", "currency": "IQD", "description": "Installation"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["message_type"], "PRICE_OFFER")

    def test_client_cannot_send_price_offer(self):
        self._auth(self.client_token)
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/price-offers/",
            {"amount": "75000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_can_accept_price_offer(self):
        offer = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.tech_user,
            message_type=ServiceChatMessage.MessageType.PRICE_OFFER,
            body="Installation",
            price_amount=Decimal("75000.00"),
            price_currency="IQD",
        )
        self._auth(self.client_token)
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/price-offers/{offer.id}/accept/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_technician_cannot_accept_own_offer(self):
        offer = ServiceChatMessage.objects.create(
            room=self.room,
            sender=self.tech_user,
            message_type=ServiceChatMessage.MessageType.PRICE_OFFER,
            body="Installation",
            price_amount=Decimal("75000.00"),
        )
        self._auth(self.tech_token)
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/price-offers/{offer.id}/accept/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
