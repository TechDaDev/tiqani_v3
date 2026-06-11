"""Tests for notification API endpoints."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from notification.models import Notification

User = get_user_model()


class NotificationAPITest(APITestCase):
    """Tests for notification CRUD and read/unread."""

    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username="user1", email="u1@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        self.user2 = User.objects.create_user(
            username="user2", email="u2@t.com", password="pass123",
            role="client", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )

        # Create notifications for user1
        for i in range(3):
            Notification.objects.create(
                recipient=self.user1,
                notification_type=Notification.Type.SYSTEM,
                title=f"Notification {i}",
                is_read=(i == 0),
            )
        # Notification for user2
        Notification.objects.create(
            recipient=self.user2,
            notification_type=Notification.Type.SYSTEM,
            title="User2 only",
        )

        self.auth1 = APIClient()
        self.auth1.force_authenticate(user=self.user1)
        self.auth2 = APIClient()
        self.auth2.force_authenticate(user=self.user2)

    def test_anonymous_cannot_list_notifications(self):
        """Anonymous gets 401."""
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_list_own_notifications(self):
        """User lists own notifications."""
        response = self.auth1.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_user_cannot_access_another_users_notification(self):
        """User gets 403 for another user's notification."""
        n = Notification.objects.filter(recipient=self.user2).first()
        url = f"/api/notifications/{n.id}/"
        response = self.auth1.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unread_count_returns_correct_value(self):
        """Unread count is correct."""
        response = self.auth1.get("/api/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 2)

    def test_mark_read_works(self):
        """Mark notification as read."""
        n = Notification.objects.filter(recipient=self.user1, is_read=False).first()
        url = f"/api/notifications/{n.id}/mark-read/"
        response = self.auth1.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertTrue(n.is_read)
        self.assertIsNotNone(n.read_at)

    def test_mark_unread_works(self):
        """Mark notification as unread."""
        n = Notification.objects.filter(recipient=self.user1, is_read=True).first()
        url = f"/api/notifications/{n.id}/mark-unread/"
        response = self.auth1.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertFalse(n.is_read)

    def test_mark_all_read_works(self):
        """Mark all as read."""
        response = self.auth1.post("/api/notifications/mark-all-read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 2)  # 2 unread
        unread = Notification.objects.filter(recipient=self.user1, is_read=False).count()
        self.assertEqual(unread, 0)

    def test_filter_is_read(self):
        """Filter by is_read."""
        response = self.auth1.get("/api/notifications/?is_read=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for n in response.data["results"]:
            self.assertTrue(n["is_read"])

    def test_anonymous_cannot_access_mark_read(self):
        """Anonymous cannot mark read."""
        n = Notification.objects.first()
        url = f"/api/notifications/{n.id}/mark-read/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_access_unread_count(self):
        """Anonymous cannot get unread count."""
        response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ActivityLogAPITest(APITestCase):
    """Tests for activity log API."""

    def setUp(self):
        self.client = APIClient()

        self.admin_user = User.objects.create_superuser(
            username="admin", email="a@t.com", password="admin123",
        )
        self.normal_user = User.objects.create_user(
            username="normal", email="n@t.com", password="pass123",
            role="client", phone_number="07700000005", governorate="Basra",
            address="Addr",
        )

        from notification.models import ActivityLog
        ActivityLog.objects.create(verb="test_event", audience="admin")

        self.admin_auth = APIClient()
        self.admin_auth.force_authenticate(user=self.admin_user)
        self.normal_auth = APIClient()
        self.normal_auth.force_authenticate(user=self.normal_user)

    def test_non_admin_cannot_access_activity(self):
        """Non-admin gets 403."""
        response = self.normal_auth.get("/api/notifications/activity/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_activity(self):
        """Admin can access activity feed."""
        response = self.admin_auth.get("/api/notifications/activity/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_access_activity(self):
        """Anonymous gets 401."""
        response = self.client.get("/api/notifications/activity/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
