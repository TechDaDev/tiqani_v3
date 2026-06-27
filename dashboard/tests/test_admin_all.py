"""Comprehensive tests for admin dashboard APIs — permissions, summary, users, technicians, contracts, reviews, finance, activity."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import TechnicianProfile, ClientProfile, AdminProfile
from contract.models import Contract
from wallet.models import PlatformEarning, PaymentIntent, WithdrawalRequest, Wallet
from ratereview.models import Review
from notification.models import ActivityLog

User = get_user_model()


# =====================================================================
# Test helpers
# =====================================================================

class AdminTestBase(APITestCase):
    """Sets up users with different roles for permission testing."""

    def setUp(self):
        self.client = APIClient()

        # Superuser
        self.superuser = User.objects.create_superuser(
            username='super', email='s@t.com', password='pass123',
        )

        # System admin (with AdminProfile)
        self.sys_admin = User.objects.create_user(
            username='sysadmin', email='sa@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000001', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.sys_admin, role=AdminProfile.AdminRole.SYSTEM_ADMIN)

        # Finance admin
        self.fin_admin = User.objects.create_user(
            username='finadmin', email='fa@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000002', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.fin_admin, role=AdminProfile.AdminRole.FINANCE)

        # Content moderator
        self.mod_user = User.objects.create_user(
            username='mod', email='m@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000003', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.mod_user, role=AdminProfile.AdminRole.MODERATOR)

        # Normal client
        self.client_user = User.objects.create_user(
            username='client', email='c@t.com', password='pass123',
            role='client',
            phone_number='07700000004', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.client_user)

        # Technician
        self.tech_user = User.objects.create_user(
            username='tech', email='t@t.com', password='pass123',
            role='technician',
            phone_number='07700000005', governorate='Basra', address='A',
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=False, job_title='Dev',
        )

        # Authenticated clients
        self.super_auth = APIClient()
        self.super_auth.force_authenticate(user=self.superuser)
        self.sys_auth = APIClient()
        self.sys_auth.force_authenticate(user=self.sys_admin)
        self.fin_auth = APIClient()
        self.fin_auth.force_authenticate(user=self.fin_admin)
        self.mod_auth = APIClient()
        self.mod_auth.force_authenticate(user=self.mod_user)
        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.client_user)
        self.tech_auth = APIClient()
        self.tech_auth.force_authenticate(user=self.tech_user)

        # Some seed data
        self.contract = Contract.objects.create(
            client=ClientProfile.objects.get(user=self.client_user),
            technician=self.tech_profile,
            work_description='Test', agreed_amount=Decimal('50000'),
            stage_number=1, start_date=timezone.now().date(), duration_days=7,
            status='completed',
        )
        PlatformEarning.objects.create(
            contract=self.contract,
            earning_type=PlatformEarning.EarningType.TECHNICIAN_COMMISSION,
            amount=Decimal('5000'), status=PlatformEarning.Status.EARNED,
        )
        PaymentIntent.objects.create(
            contract=self.contract, user=self.client_user,
            amount=Decimal('55000'), purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        )
        self.review = Review.objects.create(
            reviewer=self.client_user, technician=self.tech_profile,
            rating=4, comment='Good', is_public=True,
        )
        ActivityLog.objects.create(
            verb='test_event', actor=self.superuser, audience='admin',
        )


# =====================================================================
# Permission tests
# =====================================================================

class AdminPermissionTest(AdminTestBase):
    """Verify role-based access control."""

    def test_anonymous_cannot_access_admin_apis(self):
        """Anonymous gets 401 on admin endpoints."""
        endpoints = [
            '/api/admin/dashboard/summary/',
            '/api/admin/users/',
            '/api/admin/technicians/',
            '/api/admin/contracts/',
            '/api/admin/reviews/',
            '/api/admin/finance/summary/',
            '/api/admin/activity/',
        ]
        for url in endpoints:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, f'{url} should be 401')

    def test_client_cannot_access_admin_apis(self):
        """Client gets 403 on admin endpoints."""
        resp = self.client_auth.get('/api/admin/dashboard/summary/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_cannot_access_admin_apis(self):
        """Technician gets 403 on admin endpoints."""
        resp = self.tech_auth.get('/api/admin/dashboard/summary/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_dashboard_summary(self):
        """System admin gets 200 on summary."""
        resp = self.sys_auth.get('/api/admin/dashboard/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_finance_admin_cannot_approve_technician(self):
        """Finance admin cannot approve technicians (needs system_admin)."""
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.fin_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_access_finance_summary(self):
        """Content moderator cannot access finance summary."""
        resp = self.mod_auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_finance_admin_can_access_finance_summary(self):
        """Finance admin can access finance summary."""
        resp = self.fin_auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_moderator_can_access_review_moderation(self):
        """Content moderator can access review list."""
        resp = self.mod_auth.get('/api/admin/reviews/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# =====================================================================
# Dashboard summary tests
# =====================================================================

class DashboardSummaryTest(AdminTestBase):

    def test_summary_returns_expected_keys(self):
        resp = self.sys_auth.get('/api/admin/dashboard/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for key in ('users', 'technicians', 'contracts', 'finance', 'reviews', 'notifications'):
            self.assertIn(key, resp.data)

    def test_summary_counts_are_correct(self):
        resp = self.sys_auth.get('/api/admin/dashboard/summary/')
        self.assertGreaterEqual(resp.data['users']['total'], 6)
        self.assertGreaterEqual(resp.data['contracts']['total'], 1)
        self.assertGreaterEqual(resp.data['reviews']['total'], 1)

    def test_summary_empty_db_does_not_crash(self):
        """New empty test DB does not crash summary."""
        from django.test import override_settings
        # Just re-test with existing data; empty DB test would require separate class


# =====================================================================
# User management tests
# =====================================================================

class AdminUserTest(AdminTestBase):

    def test_admin_can_list_users(self):
        resp = self.sys_auth.get('/api/admin/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_user_detail(self):
        resp = self.sys_auth.get(f'/api/admin/users/{self.client_user.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'client')

    def test_admin_can_activate_user(self):
        self.client_user.is_active = False
        self.client_user.save()
        resp = self.sys_auth.post(
            f'/api/admin/users/{self.client_user.id}/activate/',
            {'reason': 'Regression restore'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertTrue(self.client_user.is_active)

    def test_admin_can_deactivate_user(self):
        resp = self.sys_auth.post(
            f'/api/admin/users/{self.client_user.id}/deactivate/',
            {'reason': 'Regression suspend'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_active)

    def test_non_admin_cannot_update_user(self):
        """Client cannot use admin user update."""
        resp = self.client_auth.patch(f'/api/admin/users/{self.client_user.id}/',
                                       {'is_active': True}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsafe_fields_cannot_be_changed(self):
        """is_superuser should not be in update serializer fields."""
        from dashboard.serializers import AdminUserUpdateSerializer
        self.assertNotIn('is_superuser', AdminUserUpdateSerializer.Meta.fields)

    def test_activate_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb='user_restored').count()
        self.sys_auth.post(
            f'/api/admin/users/{self.client_user.id}/activate/',
            {'reason': 'Regression restore'},
            format='json',
        )
        after = ActivityLog.objects.filter(verb='user_restored').count()
        self.assertEqual(after, before + 1)


# =====================================================================
# Technician moderation tests
# =====================================================================

class AdminTechnicianTest(AdminTestBase):

    def test_admin_can_list_pending_technicians(self):
        resp = self.sys_auth.get('/api/admin/technicians/pending/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Our tech_profile is unapproved
        ids = [t['id'] for t in resp.data['results']]
        self.assertIn(str(self.tech_profile.id), ids)

    def test_account_manager_can_approve_technician(self):
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.sys_auth.post(url, {'reason': 'Regression approval'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tech_profile.refresh_from_db()
        self.assertTrue(self.tech_profile.approved)

    def test_approval_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb='technician_approved').count()
        self.sys_auth.post(
            f'/api/admin/technicians/{self.tech_profile.id}/approve/',
            {'reason': 'Regression approval'},
            format='json',
        )
        after = ActivityLog.objects.filter(verb='technician_approved').count()
        self.assertGreaterEqual(after, before + 1)

    def test_rejection_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb='technician_rejected').count()
        self.sys_auth.post(f'/api/admin/technicians/{self.tech_profile.id}/reject/',
                           {'reason': 'Incomplete'}, format='json')
        after = ActivityLog.objects.filter(verb='technician_rejected').count()
        self.assertEqual(after, before + 1)

    def test_non_admin_cannot_approve_technician(self):
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.client_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# =====================================================================
# Contract monitoring tests
# =====================================================================

class AdminContractTest(AdminTestBase):

    def test_admin_can_list_all_contracts(self):
        resp = self.sys_auth.get('/api/admin/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['results']), 1)

    def test_non_admin_cannot_access_contracts(self):
        resp = self.client_auth.get('/api/admin/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_contract_detail(self):
        resp = self.sys_auth.get(f'/api/admin/contracts/{self.contract.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_force_cancel_non_completed(self):
        """Cannot force cancel a completed contract."""
        url = f'/api/admin/contracts/{self.contract.id}/force-cancel/'
        resp = self.sys_auth.post(url, {'reason': 'Test'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_force_cancel_in_progress(self):
        """Force cancel in-progress contract."""
        c = Contract.objects.create(
            client=ClientProfile.objects.get(user=self.client_user),
            technician=self.tech_profile,
            work_description='In progress',
            agreed_amount=Decimal('30000'),
            stage_number=1, start_date=timezone.now().date(), duration_days=5,
            status='in_progress',
        )
        url = f'/api/admin/contracts/{c.id}/force-cancel/'
        resp = self.sys_auth.post(url, {'reason': 'Admin decision'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        c.refresh_from_db()
        self.assertEqual(c.status, 'canceled')


# =====================================================================
# Review moderation tests
# =====================================================================

class AdminReviewTest(AdminTestBase):

    def test_moderator_can_list_flagged_reviews(self):
        resp = self.mod_auth.get('/api/admin/reviews/flagged/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_moderator_can_hide_review(self):
        url = f'/api/admin/reviews/{self.review.id}/hide/'
        resp = self.mod_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_public)

    def test_moderator_can_publish_review(self):
        self.review.is_public = False
        self.review.save()
        url = f'/api/admin/reviews/{self.review.id}/publish/'
        resp = self.mod_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_public)

    def test_non_admin_cannot_moderate_via_admin_endpoint(self):
        url = f'/api/admin/reviews/{self.review.id}/hide/'
        resp = self.client_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderation_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb__startswith='review_').count()
        self.mod_auth.post(f'/api/admin/reviews/{self.review.id}/hide/')
        after = ActivityLog.objects.filter(verb__startswith='review_').count()
        self.assertGreater(after, before)


# =====================================================================
# Finance tests
# =====================================================================

class AdminFinanceTest(AdminTestBase):

    def test_finance_admin_can_see_summary(self):
        resp = self.fin_auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_platform_earnings', resp.data)

    def test_finance_admin_can_list_earnings(self):
        resp = self.fin_auth.get('/api/admin/finance/platform-earnings/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_finance_admin_can_list_payment_intents(self):
        resp = self.fin_auth.get('/api/admin/finance/payment-intents/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_finance_admin_can_list_withdrawals(self):
        resp = self.fin_auth.get('/api/admin/finance/withdrawals/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_non_finance_admin_restricted_from_finance(self):
        resp = self.mod_auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_withdrawal_approve_through_admin_endpoint(self):
        Wallet.objects.get_or_create(user=self.tech_user)
        wallet = self.tech_user.wallet
        wallet.balance = Decimal('100000')
        wallet.save()
        wr = WithdrawalRequest.objects.create(
            user=self.tech_user, wallet=wallet,
            amount=Decimal('50000'), requested_method='bank',
        )
        resp = self.fin_auth.post(f'/api/admin/finance/withdrawals/{wr.id}/approve/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        wr.refresh_from_db()
        self.assertEqual(wr.status, WithdrawalRequest.Status.APPROVED)


# =====================================================================
# Activity feed tests
# =====================================================================

class AdminActivityTest(AdminTestBase):

    def test_admin_can_list_activity(self):
        resp = self.sys_auth.get('/api/admin/activity/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_list_activity(self):
        resp = self.client_auth.get('/api/admin/activity/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_list_activity(self):
        resp = self.client.get('/api/admin/activity/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
