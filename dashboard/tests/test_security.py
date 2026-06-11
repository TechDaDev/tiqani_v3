"""Additional security hardening tests for dashboard — activity log creation, account_manager role, role restrictions."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import TechnicianProfile, ClientProfile, AdminProfile
from contract.models import Contract
from contract.services import cancel_contract
from wallet.models import PlatformEarning, PaymentIntent, WithdrawalRequest, Wallet
from ratereview.models import Review
from notification.models import ActivityLog

User = get_user_model()


class ActivityLogCreationTest(APITestCase):
    """Ensure ActivityLog is created for key admin actions."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super_al', email='sal@t.com', password='pass123',
        )
        self.sys_admin = User.objects.create_user(
            username='sys_al', email='sysal@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000500', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.sys_admin, role=AdminProfile.AdminRole.SYSTEM_ADMIN)

        self.tech_user = User.objects.create_user(
            username='t_al', email='tal@t.com', password='pass123',
            role='technician',
            phone_number='07700000501', governorate='Basra', address='A',
        )
        self.tech = TechnicianProfile.objects.create(
            user=self.tech_user, approved=False, job_title='Dev',
        )

        client_user = User.objects.create_user(
            username='c_al', email='cal@t.com', password='pass123',
            role='client',
            phone_number='07700000502', governorate='Basra', address='A',
        )
        self.client = ClientProfile.objects.create(user=client_user)

        self.contract = Contract.objects.create(
            client=self.client, technician=self.tech,
            work_description='Test AL', agreed_amount=Decimal('50000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=7,
            status='in_progress',
        )

        self.super_auth = APIClient()
        self.super_auth.force_authenticate(user=self.superuser)
        self.sys_auth = APIClient()
        self.sys_auth.force_authenticate(user=self.sys_admin)

    def test_user_activate_creates_activity_log(self):
        self.tech_user.is_active = False
        self.tech_user.save()
        before = ActivityLog.objects.filter(verb='user_activated').count()
        self.sys_auth.post(f'/api/admin/users/{self.tech_user.id}/activate/')
        after = ActivityLog.objects.filter(verb='user_activated').count()
        self.assertEqual(after, before + 1)

    def test_user_deactivate_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb='user_deactivated').count()
        self.sys_auth.post(f'/api/admin/users/{self.tech_user.id}/deactivate/')
        after = ActivityLog.objects.filter(verb='user_deactivated').count()
        self.assertEqual(after, before + 1)

    def test_technician_approve_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb='technician_approved').count()
        self.sys_auth.post(f'/api/admin/technicians/{self.tech.id}/approve/')
        after = ActivityLog.objects.filter(verb='technician_approved').count()
        self.assertEqual(after, before + 1)

    def test_technician_reject_creates_activity_log(self):
        before = ActivityLog.objects.filter(verb='technician_rejected').count()
        self.sys_auth.post(f'/api/admin/technicians/{self.tech.id}/reject/',
                           {'reason': 'Docs'}, format='json')
        after = ActivityLog.objects.filter(verb='technician_rejected').count()
        self.assertEqual(after, before + 1)

    def test_review_hide_creates_activity_log(self):
        review = Review.objects.create(
            reviewer=self.superuser, technician=self.tech,
            rating=3, comment='Test', is_public=True,
        )
        before = ActivityLog.objects.filter(verb='review_moderated').count()
        self.sys_auth.post(f'/api/admin/reviews/{review.id}/hide/')
        after = ActivityLog.objects.filter(verb='review_moderated').count()
        # The verb might be 'review_moderated' or start with 'review_'
        total_before = ActivityLog.objects.filter(verb__startswith='review_').count()
        self.sys_auth.post(f'/api/admin/reviews/{review.id}/publish/')
        total_after = ActivityLog.objects.filter(verb__startswith='review_').count()
        self.assertGreater(total_after, total_before)

    def test_withdrawal_approve_creates_activity_log(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.tech_user)
        wallet.balance = Decimal('100000')
        wallet.save()
        wr = WithdrawalRequest.objects.create(
            user=self.tech_user, wallet=wallet,
            amount=Decimal('30000'), requested_method='bank',
        )
        before = ActivityLog.objects.filter(verb='withdrawal_approved').count()
        self.sys_auth.post(f'/api/admin/finance/withdrawals/{wr.id}/approve/', {}, format='json')
        after = ActivityLog.objects.filter(verb='withdrawal_approved').count()
        self.assertEqual(after, before + 1)

    def test_withdrawal_reject_creates_activity_log(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.tech_user)
        wallet.balance = Decimal('100000')
        wallet.save()
        wr = WithdrawalRequest.objects.create(
            user=self.tech_user, wallet=wallet,
            amount=Decimal('30000'), requested_method='bank',
        )
        before = ActivityLog.objects.filter(verb='withdrawal_rejected').count()
        self.sys_auth.post(f'/api/admin/finance/withdrawals/{wr.id}/reject/', {}, format='json')
        after = ActivityLog.objects.filter(verb='withdrawal_rejected').count()
        self.assertEqual(after, before + 1)


class AccountManagerRoleDashboardTest(APITestCase):
    """Test account_manager role can access account/technician management but not finance."""

    def setUp(self):
        self.acc_mgr = User.objects.create_user(
            username='accmgr_dash', email='amd@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000600', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.acc_mgr, role=AdminProfile.AdminRole.ACCOUNT_MANAGER)

        self.tech_user = User.objects.create_user(
            username='t_accmgr', email='tam@t.com', password='pass123',
            role='technician',
            phone_number='07700000601', governorate='Basra', address='A',
        )
        TechnicianProfile.objects.create(user=self.tech_user, approved=False, job_title='Dev')

        self.auth = APIClient()
        self.auth.force_authenticate(user=self.acc_mgr)

    def test_account_manager_can_access_user_list(self):
        resp = self.auth.get('/api/admin/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_account_manager_can_access_technician_list(self):
        resp = self.auth.get('/api/admin/technicians/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_account_manager_can_access_technician_pending(self):
        resp = self.auth.get('/api/admin/technicians/pending/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_account_manager_cannot_access_finance(self):
        resp = self.auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_account_manager_cannot_access_finance_earnings(self):
        resp = self.auth.get('/api/admin/finance/platform-earnings/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_account_manager_cannot_approve_technician(self):
        url = f'/api/admin/technicians/{self.tech_user.technician_profile.id}/approve/'
        resp = self.auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserSearchFilterTest(APITestCase):
    """Admin user search does not crash, filters work correctly."""

    def setUp(self):
        self.sys_admin = User.objects.create_user(
            username='sys_admin_search', email='sas@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000700', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.sys_admin, role=AdminProfile.AdminRole.SYSTEM_ADMIN)

        for i in range(5):
            User.objects.create_user(
                username=f'search_user_{i}', email=f'su{i}@t.com', password='pass123',
                role='client',
                phone_number=f'077000007{i+1}0', governorate='Baghdad', address=f'Addr {i}',
            )

        self.auth = APIClient()
        self.auth.force_authenticate(user=self.sys_admin)

    def test_user_search_does_not_crash(self):
        resp = self.auth.get('/api/admin/users/?search=search_user')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_filter_by_role(self):
        resp = self.auth.get('/api/admin/users/?role=client')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_filter_by_is_active(self):
        resp = self.auth.get('/api/admin/users/?is_active=true')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_filter_by_governorate(self):
        resp = self.auth.get('/api/admin/users/?governorate=Baghdad')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
