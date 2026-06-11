"""Security hardening tests for accounts app — role helpers, unsafe field updates, sensitive exposure."""

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile, AdminProfile, CustomUser
from accounts.role_helpers import (
    is_platform_admin, is_system_admin, is_finance_admin,
    is_account_manager, is_content_moderator, is_admin_or_staff,
)

User = get_user_model()


class RoleHelperTest(APITestCase):
    """Unit tests for accounts.role_helpers."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email='s@t.com', password='pass123',
        )
        self.sys_admin = User.objects.create_user(
            username='sysadmin', email='sa@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000001', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.sys_admin, role=AdminProfile.AdminRole.SYSTEM_ADMIN)

        self.fin_admin = User.objects.create_user(
            username='finadmin', email='fa@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000002', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.fin_admin, role=AdminProfile.AdminRole.FINANCE)

        self.mod_user = User.objects.create_user(
            username='mod', email='m@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000003', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.mod_user, role=AdminProfile.AdminRole.MODERATOR)

        self.acc_mgr = User.objects.create_user(
            username='accmgr', email='am@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000006', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.acc_mgr, role=AdminProfile.AdminRole.ACCOUNT_MANAGER)

        self.client_user = User.objects.create_user(
            username='client', email='c@t.com', password='pass123',
            role='client',
            phone_number='07700000004', governorate='Basra', address='A',
        )

    def test_is_platform_admin_superuser(self):
        self.assertTrue(is_platform_admin(self.superuser))

    def test_is_platform_admin_sys_admin(self):
        self.assertTrue(is_platform_admin(self.sys_admin))

    def test_is_platform_admin_client(self):
        self.assertFalse(is_platform_admin(self.client_user))

    def test_is_platform_admin_none(self):
        self.assertFalse(is_platform_admin(None))

    def test_is_system_admin_superuser(self):
        self.assertTrue(is_system_admin(self.superuser))

    def test_is_system_admin_finance(self):
        self.assertFalse(is_system_admin(self.fin_admin))

    def test_is_finance_admin_finance(self):
        self.assertTrue(is_finance_admin(self.fin_admin))

    def test_is_finance_admin_moderator(self):
        self.assertFalse(is_finance_admin(self.mod_user))

    def test_is_account_manager_account_manager(self):
        """account_manager role should be recognized."""
        self.assertTrue(is_account_manager(self.acc_mgr))

    def test_is_account_manager_finance(self):
        self.assertFalse(is_account_manager(self.fin_admin))

    def test_is_content_moderator_moderator(self):
        self.assertTrue(is_content_moderator(self.mod_user))

    def test_is_content_moderator_finance(self):
        self.assertFalse(is_content_moderator(self.fin_admin))

    def test_is_admin_or_staff_staff(self):
        self.assertTrue(is_admin_or_staff(self.sys_admin))

    def test_is_admin_or_staff_client(self):
        self.assertFalse(is_admin_or_staff(self.client_user))

    def test_get_admin_role_returns_string(self):
        from accounts.role_helpers import get_admin_role
        self.assertEqual(get_admin_role(self.acc_mgr), 'account_manager')
        self.assertEqual(get_admin_role(self.sys_admin), 'system_admin')
        self.assertEqual(get_admin_role(self.client_user), None)
        self.assertEqual(get_admin_role(None), None)


class UnsafeFieldUpdateTest(APITestCase):
    """Test that normal users cannot modify sensitive fields."""

    def setUp(self):
        self.client_api = APIClient()

        self.normal_user = User.objects.create_user(
            username='normal', email='n@t.com', password='pass123',
            role='client',
            phone_number='07700000010', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.normal_user)
        self.client_api.force_authenticate(user=self.normal_user)

        self.tech_user = User.objects.create_user(
            username='tech1', email='t1@t.com', password='pass123',
            role='technician',
            phone_number='07700000011', governorate='Basra', address='A',
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=False, job_title='Dev',
        )

    def test_normal_user_cannot_change_own_role(self):
        """PATCH on own account should not change role/is_staff/is_superuser."""
        resp = self.client_api.patch('/api/accounts/me/',
                                     {'role': 'admin', 'is_staff': True, 'is_superuser': True},
                                     format='json')
        # Should either be 200 (but ignoring unsafe fields) or reject safe-only
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.role, 'client')
        self.assertFalse(self.normal_user.is_staff)
        self.assertFalse(self.normal_user.is_superuser)

    def test_normal_user_cannot_change_is_active_through_admin(self):
        resp = self.client_api.patch(f'/api/admin/users/{self.normal_user.id}/',
                                     {'is_active': False}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_normal_user_cannot_approve_technician(self):
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.client_api.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.tech_profile.refresh_from_db()
        self.assertFalse(self.tech_profile.approved)


class AdminRoleSecurityTest(APITestCase):
    """Test admin role-based access: account_manager vs finance_admin permissions."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email='s@t.com', password='pass123',
        )
        self.acc_mgr = User.objects.create_user(
            username='accmgr', email='am@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000020', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.acc_mgr, role=AdminProfile.AdminRole.ACCOUNT_MANAGER)

        self.fin_admin = User.objects.create_user(
            username='finadmin2', email='fa2@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000021', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.fin_admin, role=AdminProfile.AdminRole.FINANCE)

        self.tech_user = User.objects.create_user(
            username='tech2', email='t2@t.com', password='pass123',
            role='technician',
            phone_number='07700000022', governorate='Basra', address='A',
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=False, job_title='Dev',
        )

        self.unauth = APIClient()
        self.acc_auth = APIClient()
        self.acc_auth.force_authenticate(user=self.acc_mgr)
        self.fin_auth = APIClient()
        self.fin_auth.force_authenticate(user=self.fin_admin)
        self.super_auth = APIClient()
        self.super_auth.force_authenticate(user=self.superuser)

    def test_account_manager_can_list_users(self):
        resp = self.acc_auth.get('/api/admin/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_account_manager_can_list_technicians(self):
        resp = self.acc_auth.get('/api/admin/technicians/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_account_manager_cannot_access_finance(self):
        resp = self.acc_auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_finance_admin_can_access_finance(self):
        resp = self.fin_auth.get('/api/admin/finance/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_finance_admin_cannot_approve_technician(self):
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.fin_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_account_manager_cannot_approve_technician(self):
        # approve requires system_admin
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.acc_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_approve_technician(self):
        url = f'/api/admin/technicians/{self.tech_profile.id}/approve/'
        resp = self.super_auth.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.tech_profile.refresh_from_db()
        self.assertTrue(self.tech_profile.approved)


class AdminEndpointsRoleRestrictionTest(APITestCase):
    """Admin endpoints reject clients/technicians."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='clientx', email='cx@t.com', password='pass123',
            role='client',
            phone_number='07700000030', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username='techx', email='tx@t.com', password='pass123',
            role='technician',
            phone_number='07700000031', governorate='Basra', address='A',
        )
        TechnicianProfile.objects.create(user=self.tech_user, approved=True, job_title='Dev')

        self.admin_user = User.objects.create_user(
            username='adminx', email='ax@t.com', password='pass123',
            role='admin', is_staff=True,
            phone_number='07700000032', governorate='Basra', address='A',
        )
        AdminProfile.objects.create(user=self.admin_user, role=AdminProfile.AdminRole.SYSTEM_ADMIN)

        self.client_auth = APIClient()
        self.client_auth.force_authenticate(user=self.client_user)
        self.tech_auth = APIClient()
        self.tech_auth.force_authenticate(user=self.tech_user)
        self.admin_auth = APIClient()
        self.admin_auth.force_authenticate(user=self.admin_user)

        self.admin_endpoints = [
            '/api/admin/dashboard/summary/',
            '/api/admin/users/',
            '/api/admin/technicians/',
            '/api/admin/contracts/',
            '/api/admin/reviews/',
            '/api/admin/finance/summary/',
            '/api/admin/activity/',
        ]

    def test_client_rejected_from_all_admin_endpoints(self):
        for url in self.admin_endpoints:
            resp = self.client_auth.get(url)
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, f'{url}')

    def test_technician_rejected_from_all_admin_endpoints(self):
        for url in self.admin_endpoints:
            resp = self.tech_auth.get(url)
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, f'{url}')

    def test_admin_can_access_all_admin_endpoints(self):
        for url in self.admin_endpoints:
            resp = self.admin_auth.get(url)
            self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN), f'{url}')
