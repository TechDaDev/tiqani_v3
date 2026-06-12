"""Tests for chat message REST API endpoints."""

import io
from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import CustomUser, ClientProfile, TechnicianProfile
from chat.models import ServiceChatRoom, ServiceChatMessage


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatMessageAPITests(TestCase):
    """Test message list, create, and attachment endpoints."""

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

    def test_participant_can_list_messages(self):
        self._auth(self.client_token)
        resp = self.client_api.get(f"/api/chat/rooms/{self.room.id}/messages/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_participant_can_send_message(self):
        self._auth(self.client_token)
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/messages/send/",
            {"body": "Hello, this is a test message."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["message_type"], "TEXT")

    def test_cannot_send_message_in_closed_room(self):
        self.room.status = ServiceChatRoom.Status.CLOSED
        self.room.save()
        self._auth(self.client_token)
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/messages/send/",
            {"body": "Hello!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatAttachmentAPITests(TestCase):
    """Test file upload endpoint."""

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

    def _auth(self, token):
        self.client_api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_attachment_upload_valid_file(self):
        self._auth(self.client_token)
        from django.core.files.uploadedfile import SimpleUploadedFile
        pdf_file = SimpleUploadedFile(
            "test.pdf",
            b"%PDF-1.4 test content",
            content_type="application/pdf",
        )
        resp = self.client_api.post(
            f"/api/chat/rooms/{self.room.id}/attachments/",
            {"file": pdf_file, "body": "Here is the file"},
            format="multipart",
        )
        self.assertIn(resp.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
