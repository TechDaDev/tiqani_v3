"""Tests for notification integrations with contract, review, and wallet lifecycle."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import TechnicianProfile, ClientProfile
from contract.models import Contract
from notification.models import Notification, ActivityLog
from notification.services import (
    notify_contract_created, notify_contract_proposal_submitted,
    notify_contract_accepted, notify_contract_in_progress,
    notify_contract_canceled, notify_contract_completed,
    notify_stage_submitted, notify_stage_approved,
    notify_review_created, notify_review_responded,
)

User = get_user_model()


class ContractNotificationTest(TestCase):
    """Tests that contract events generate correct notifications."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client", email="c@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech", email="t@t.com", password="pass123",
            role="technician", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
        )

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Test",
            agreed_amount=Decimal("100000.00"),
            stage_number=1,
            start_date=timezone.now().date(),
            duration_days=7,
        )

    def test_contract_created_notifies_technician(self):
        """notify_contract_created sends to technician."""
        n = notify_contract_created(self.contract, self.client_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.tech_user)
        self.assertEqual(n.notification_type, 'contract_created')
        self.assertEqual(ActivityLog.objects.filter(verb='contract_created').count(), 1)

    def test_proposal_submitted_notifies_client(self):
        """notify_contract_proposal_submitted sends to client."""
        n = notify_contract_proposal_submitted(self.contract, self.tech_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.client_user)
        self.assertEqual(n.notification_type, 'contract_proposal_submitted')

    def test_contract_accepted_notifies_other_participant(self):
        """notify_contract_accepted notifies the other party."""
        n = notify_contract_accepted(self.contract, self.client_user, self.tech_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.tech_user)

    def test_contract_in_progress_notifies_both(self):
        """notify_contract_in_progress creates 2 notifications."""
        notify_contract_in_progress(self.contract)
        count = Notification.objects.filter(
            notification_type='contract_accepted',
            title="Contract in progress",
        ).count()
        self.assertEqual(count, 2)

    def test_contract_canceled_creates_activity(self):
        """notify_contract_canceled creates activity log."""
        notify_contract_canceled(self.contract, self.client_user, other_participant=self.tech_user)
        self.assertTrue(ActivityLog.objects.filter(verb='contract_canceled').exists())

    def test_contract_completed_creates_review_reminder(self):
        """notify_contract_completed includes review reminder."""
        notify_contract_completed(self.contract)
        review_reminder = Notification.objects.filter(
            recipient=self.client_user,
            title="Review your technician",
        ).count()
        self.assertEqual(review_reminder, 1)

    def test_stage_submitted_notifies_client(self):
        """notify_stage_submitted sends to client."""
        from contract.models import ContractStage
        stage = ContractStage.objects.create(
            contract=self.contract, stage_number=2,
            amount=Decimal("100000.00"),
        )
        n = notify_stage_submitted(stage, self.tech_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.client_user)

    def test_stage_approved_notifies_technician(self):
        """notify_stage_approved sends to technician."""
        from contract.models import ContractStage
        stage = ContractStage.objects.create(
            contract=self.contract, stage_number=2,
            amount=Decimal("100000.00"),
        )
        n = notify_stage_approved(stage, self.client_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.tech_user)


class ReviewNotificationTest(TestCase):
    """Tests that review events generate correct notifications."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client", email="c@t.com", password="pass123",
            role="client", phone_number="07700000001", governorate="Basra",
            address="Addr",
        )
        self.tech_user = User.objects.create_user(
            username="tech", email="t@t.com", password="pass123",
            role="technician", phone_number="07700000002", governorate="Basra",
            address="Addr",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
        )

        from ratereview.models import Review
        self.review = Review.objects.create(
            reviewer=self.client_user,
            technician=self.tech_profile,
            rating=5,
            comment="Great!",
            is_public=True,
            is_verified=True,
        )

    def test_review_created_notifies_technician(self):
        """notify_review_created sends to technician."""
        n = notify_review_created(self.review, self.client_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.tech_user)
        self.assertEqual(n.notification_type, 'review_created')

    def test_review_responded_notifies_reviewer(self):
        """notify_review_responded sends to reviewer."""
        n = notify_review_responded(self.review, self.tech_user)
        self.assertIsNotNone(n)
        self.assertEqual(n.recipient, self.client_user)
        self.assertEqual(n.notification_type, 'review_responded')
