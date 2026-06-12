"""
Tests for accounts background tasks — email sending, OTP cleanup.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.models import OTPVerification
from accounts.tasks import cleanup_expired_otps_task

User = get_user_model()


class CleanupExpiredOtpsTaskTest(TestCase):
    """Test the expired OTP cleanup task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="otp_cleanup", password="test123",
        )

    def test_task_runs_safely_with_no_otps(self):
        """Task handles empty database without error."""
        result = cleanup_expired_otps_task()
        self.assertEqual(result["task"], "cleanup_expired_otps")
        self.assertEqual(result["expired_count"], 0)
        self.assertEqual(result["marked_count"], 0)

    def test_task_marks_expired_otps(self):
        """OTPs older than retention days are marked as used."""
        from django.utils import timezone
        from datetime import timedelta

        # Create an OTP that appears old
        otp = OTPVerification.objects.create(
            user=self.user,
            otp_code="123456",
        )
        # Manually backdate it
        OTPVerification.objects.filter(id=otp.id).update(
            created_at=timezone.now() - timedelta(days=30),
        )

        result = cleanup_expired_otps_task()
        self.assertEqual(result["expired_count"], 1)
        self.assertEqual(result["marked_count"], 1)

        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_task_does_not_touch_recent_otps(self):
        """Recent active OTPs are not affected."""
        OTPVerification.objects.create(
            user=self.user,
            otp_code="654321",
        )
        result = cleanup_expired_otps_task()
        self.assertEqual(result["expired_count"], 0)


class EmailTaskTest(TestCase):
    """Test email tasks (basic import and signature)."""

    def test_send_otp_email_task_imports(self):
        """send_otp_email_task can be imported."""
        from accounts.tasks import send_otp_email_task
        self.assertIsNotNone(send_otp_email_task)

    def test_send_password_reset_email_task_imports(self):
        """send_password_reset_email_task can be imported."""
        from accounts.tasks import send_password_reset_email_task
        self.assertIsNotNone(send_password_reset_email_task)

    def test_send_generic_email_task_imports(self):
        """send_generic_email_task can be imported."""
        from accounts.tasks import send_generic_email_task
        self.assertIsNotNone(send_generic_email_task)
