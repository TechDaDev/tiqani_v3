"""
Tests for dealership background tasks — cash-out expiry, alerts.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from dealership.models import (
    DealershipProfile,
    DealershipClientCashout,
)
from dealership.tasks import expire_old_cashout_codes_task

User = get_user_model()


class CashoutExpiryTaskTest(TestCase):
    """Test the cash-out code expiry task."""

    def setUp(self):
        self.dealer_user = User.objects.create_user(
            username="dealer_expiry", password="test123", role="dealership",
        )
        self.profile = DealershipProfile.objects.create(
            user=self.dealer_user,
            business_name="Expiry Test",
            owner_name="Test",
            phone="07700000999",
            governorate="Baghdad",
            address="Test",
            status=DealershipProfile.Status.ACTIVE,
            active=True,
        )
        self.client_user = User.objects.create_user(
            username="client_expiry", password="test123", role="client",
        )

    def test_expires_past_due_codes(self):
        """Cashouts with expired codes are marked expired."""
        cashout = DealershipClientCashout.objects.create(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal("1000"),
            status=DealershipClientCashout.Status.CODE_ISSUED,
            code_expires_at=timezone.now() - timedelta(hours=1),
        )

        result = expire_old_cashout_codes_task()
        self.assertEqual(result["expired_count"], 1)

        cashout.refresh_from_db()
        self.assertEqual(cashout.status, DealershipClientCashout.Status.EXPIRED)

    def test_does_not_touch_valid_codes(self):
        """Cashouts with future expiry are not touched."""
        DealershipClientCashout.objects.create(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal("1000"),
            status=DealershipClientCashout.Status.CODE_ISSUED,
            code_expires_at=timezone.now() + timedelta(hours=1),
        )

        result = expire_old_cashout_codes_task()
        self.assertEqual(result["expired_count"], 0)

    def test_does_not_touch_completed_cashouts(self):
        """Completed cashouts are not affected."""
        DealershipClientCashout.objects.create(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal("1000"),
            status=DealershipClientCashout.Status.COMPLETED,
        )

        result = expire_old_cashout_codes_task()
        self.assertEqual(result["expired_count"], 0)

    def test_task_handles_empty_db(self):
        """Task runs safely with no cashouts."""
        result = expire_old_cashout_codes_task()
        self.assertEqual(result["expired_count"], 0)

    def test_dealership_tasks_import(self):
        """All dealership task functions can be imported."""
        from dealership.tasks import (
            expire_old_cashout_codes_task,
            send_dealership_threshold_alerts_task,
            send_dealership_guarantee_expiry_alerts_task,
        )
        self.assertIsNotNone(expire_old_cashout_codes_task)
        self.assertIsNotNone(send_dealership_threshold_alerts_task)
        self.assertIsNotNone(send_dealership_guarantee_expiry_alerts_task)
