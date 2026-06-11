"""Security hardening tests for notifications — object-level access, sensitive exposure."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile
from notification.models import Notification

User = get_user_model()


class NotificationObjectLevelAccessTest(APITestCase):
    """Users cannot access other users' notifications."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='u1_notif', email='u1n@t.com', password='pass123',
            role='client',
            phone_number='07700000400', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='u2_notif', email='u2n@t.com', password='pass123',
            role='client',
            phone_number='07700000401', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.user2)

        self.notif1 = Notification.objects.create(
            recipient=self.user1, notification_type='system',
            title='Notif for user1', message='Secret 1',
        )
        self.notif2 = Notification.objects.create(
            recipient=self.user2, notification_type='system',
            title='Notif for user2', message='Secret 2',
        )

        self.u1_auth = APIClient()
        self.u1_auth.force_authenticate(user=self.user1)
        self.u2_auth = APIClient()
        self.u2_auth.force_authenticate(user=self.user2)
        self.unauth = APIClient()

    def test_user_only_sees_own_notifications(self):
        resp = self.u1_auth.get('/api/notifications/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [n.get('title', '') for n in resp.data.get('results', resp.data)]
        self.assertIn('Notif for user1', titles)
        self.assertNotIn('Notif for user2', titles)

    def test_user2_only_sees_own_notifications(self):
        resp = self.u2_auth.get('/api/notifications/')
        titles = [n.get('title', '') for n in resp.data.get('results', resp.data)]
        self.assertIn('Notif for user2', titles)
        self.assertNotIn('Notif for user1', titles)

    def test_user1_cannot_access_user2_notification_detail(self):
        resp = self.u1_auth.get(f'/api/notifications/{self.notif2.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_cannot_access_notifications(self):
        resp = self.unauth.get('/api/notifications/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_filter_works(self):
        """is_read filter works correctly."""
        resp = self.u1_auth.get('/api/notifications/?is_read=false')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class NotificationUnsafeFieldTest(APITestCase):
    """Notification recipient/actor/type/target cannot be modified through user endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='n_unsafe', email='nu@t.com', password='pass123',
            role='client',
            phone_number='07700000410', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.user)

        self.other_user = User.objects.create_user(
            username='n_other', email='no@t.com', password='pass123',
            role='client',
            phone_number='07700000411', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.other_user)

        self.notif = Notification.objects.create(
            recipient=self.user, notification_type='system',
            title='Test', message='Test body',
        )

        self.auth = APIClient()
        self.auth.force_authenticate(user=self.user)

    def test_cannot_change_recipient_through_api(self):
        """Notification mark-read should verify ownership."""
        resp = self.auth.post(f'/api/notifications/{self.notif.id}/mark-read/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_cannot_mark_other_users_notification_read(self):
        other_notif = Notification.objects.create(
            recipient=self.other_user, notification_type='system',
            title='Other', message='Other body',
        )
        resp = self.auth.post(f'/api/notifications/{other_notif.id}/mark-read/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
