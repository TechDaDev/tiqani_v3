"""Focused Phase 11 review/reputation/notification service tests."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract
from dispute.models import ContractDispute, DisputeReason
from notification.models import Notification, NotificationPreference
from notification.services import create_notification_once
from ratereview.models import Review, UserReputationSnapshot
from ratereview.services import (
    create_contract_review,
    get_review_eligibility,
    recalculate_user_reputation,
)

User = get_user_model()


class Phase11ReviewServicesTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="p11_client", email="p11c@example.com", password="pass123",
            role="client", phone_number="07710000001", governorate="Baghdad", address="A",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)
        self.tech_user = User.objects.create_user(
            username="p11_tech", email="p11t@example.com", password="pass123",
            role="technician", phone_number="07710000002", governorate="Baghdad", address="A",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title="Network tech",
        )
        self.outsider = User.objects.create_user(
            username="p11_out", email="p11o@example.com", password="pass123",
            role="client", phone_number="07710000003", governorate="Basra", address="B",
        )
        ClientProfile.objects.create(user=self.outsider)
        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description="Install network",
            agreed_amount=Decimal("100000.00"),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=5,
            status="completed",
        )

    def test_client_and_technician_are_eligible_to_review_each_other(self):
        client_eligibility = get_review_eligibility(self.contract, self.client_user)
        tech_eligibility = get_review_eligibility(self.contract, self.tech_user)

        self.assertTrue(client_eligibility.eligible)
        self.assertEqual(client_eligibility.reviewee, self.tech_user)
        self.assertTrue(tech_eligibility.eligible)
        self.assertEqual(tech_eligibility.reviewee, self.client_user)

    def test_unrelated_user_is_denied(self):
        eligibility = get_review_eligibility(self.contract, self.outsider)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason_code, "NOT_PARTICIPANT")

    def test_unresolved_dispute_blocks_review(self):
        ContractDispute.objects.create(
            contract=self.contract,
            opened_by=self.client_user,
            respondent=self.tech_user,
            reason=DisputeReason.QUALITY_NOT_AS_AGREED,
            claimed_amount=Decimal("1000.00"),
        )

        eligibility = get_review_eligibility(self.contract, self.client_user)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason_code, "UNRESOLVED_DISPUTE")

    def test_create_contract_review_is_idempotent(self):
        first, created_first = create_contract_review(
            contract_id=self.contract.id,
            actor=self.client_user,
            rating=5,
            title="Great",
            comment="Strong work",
        )
        second, created_second = create_contract_review(
            contract_id=self.contract.id,
            actor=self.client_user,
            rating=1,
            title="Ignored",
            comment="Ignored",
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.id, second.id)
        self.assertEqual(Review.objects.count(), 1)

    def test_technician_review_targets_client_not_technician_rating(self):
        review, _ = create_contract_review(
            contract_id=self.contract.id,
            actor=self.tech_user,
            rating=4,
            title="Good client",
        )

        self.assertEqual(review.reviewee, self.client_user)
        self.assertIsNone(review.technician)
        self.tech_profile.refresh_from_db()
        self.assertEqual(self.tech_profile.rate, Decimal("0.00"))

    def test_reputation_snapshot_is_deterministic(self):
        create_contract_review(contract_id=self.contract.id, actor=self.client_user, rating=5)

        first = recalculate_user_reputation(self.tech_user, role="technician")
        second = recalculate_user_reputation(self.tech_user, role="technician")

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.average_rating, Decimal("5.00"))
        self.assertEqual(second.review_count, 1)
        self.assertEqual(second.rating_5_count, 1)
        self.assertEqual(second.completed_contract_count, 1)


class Phase11NotificationServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="p11_notif", email="p11n@example.com", password="pass123",
            role="client", phone_number="07710000011", governorate="Baghdad", address="A",
        )

    def test_create_notification_once_deduplicates(self):
        first = create_notification_once(
            recipient=self.user,
            notification_type="review_created",
            title="Review",
            deduplication_key="phase11:test",
        )
        second = create_notification_once(
            recipient=self.user,
            notification_type="review_created",
            title="Review duplicate",
            deduplication_key="phase11:test",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(Notification.objects.count(), 1)

    def test_notification_preferences_default_and_update(self):
        preferences, _ = NotificationPreference.objects.get_or_create(user=self.user)
        preferences.reviews = False
        preferences.save(update_fields=["reviews"])

        preferences.refresh_from_db()
        self.assertFalse(preferences.reviews)
        self.assertFalse(preferences.email_enabled)
        self.assertFalse(preferences.push_enabled)
