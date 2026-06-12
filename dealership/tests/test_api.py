"""
Tests for dealership API endpoints.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from dealership.models import (
    DealershipProfile,
    DealershipGuarantee,
    DealershipRechargeFeeConfig,
    DealershipClientRecharge,
    DealershipClientCashout,
    DealershipSettlement,
)
from dealership.services import hash_confirmation_code

User = get_user_model()


class DealershipAPITestBase(TestCase):
    """Base setup for dealership API tests."""

    @classmethod
    def setUpTestData(cls):
        # Admin user (system_admin)
        cls.admin = User.objects.create_superuser(
            username='admin_user', password='admin123',
            role='admin',
        )

        # Dealership user
        cls.dealer_user = User.objects.create_user(
            username='dealer_api', password='dealer123', role='dealership',
        )
        cls.profile = DealershipProfile.objects.create(
            user=cls.dealer_user,
            business_name='API Test Dealership',
            owner_name='API Owner',
            phone='07700000100',
            governorate='Baghdad',
            address='API Test Address',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
            usage_limit_percent=Decimal('80.00'),
            recharge_enabled=True,
            cashout_enabled=True,
        )
        DealershipGuarantee.objects.create(
            dealership=cls.profile,
            cash_amount=Decimal('10000000'),  # 10M → 8M limit
            status=DealershipGuarantee.Status.VERIFIED,
        )

        # Client user
        cls.client_user = User.objects.create_user(
            username='client_api', password='client123', role='client',
        )
        from wallet.models import Wallet
        Wallet.objects.create(user=cls.client_user, balance=Decimal('500000'))

        # Fee config
        DealershipRechargeFeeConfig.objects.create(
            fee_percent=Decimal('1.00'),
            default_fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            is_active=True,
        )

        # Content moderator (should be denied)
        cls.moderator = User.objects.create_user(
            username='mod_api', password='mod123', role='admin', is_staff=True,
        )
        from accounts.models import AdminProfile
        AdminProfile.objects.create(user=cls.moderator, role=AdminProfile.AdminRole.MODERATOR)

    def setUp(self):
        self.client = APIClient()


class DealershipSummaryAPITest(DealershipAPITestBase):
    """Test dealership summary endpoint."""

    def test_summary_returns_financials(self):
        """GET /api/dealership/me/summary/ returns financial details."""
        self.client.force_authenticate(self.dealer_user)
        response = self.client.get('/api/dealership/me/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['business_name'], 'API Test Dealership')
        self.assertEqual(response.data['currency'], 'IQD')
        self.assertIn('usable_credit_limit', response.data)
        self.assertIn('net_exposure', response.data)
        self.assertIn('available_recharge_capacity', response.data)

    def test_summary_requires_dealership_role(self):
        """Client user cannot access dealership summary."""
        self.client.force_authenticate(self.client_user)
        response = self.client.get('/api/dealership/me/summary/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_summary_requires_auth(self):
        """Unauthenticated request is rejected."""
        response = self.client.get('/api/dealership/me/summary/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RechargePreviewAPITest(DealershipAPITestBase):
    """Test recharge preview endpoint."""

    def test_recharge_preview_added_on_top(self):
        """Preview calculates added_on_top fees correctly."""
        self.client.force_authenticate(self.dealer_user)
        response = self.client.post('/api/dealership/recharges/preview/', {
            'client_id': str(self.client_user.id),
            'fee_mode': 'added_on_top',
            'wallet_credit_amount': '1000000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['currency'], 'IQD')
        self.assertEqual(response.data['wallet_credit_amount'], '1000000.00')
        self.assertEqual(response.data['dealership_fee_amount'], '10000.00')

    def test_recharge_preview_deducted_from_deposit(self):
        """Preview calculates deducted_from_deposit correctly."""
        self.client.force_authenticate(self.dealer_user)
        response = self.client.post('/api/dealership/recharges/preview/', {
            'client_id': str(self.client_user.id),
            'fee_mode': 'deducted_from_deposit',
            'cash_received_amount': '1000000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['wallet_credit_amount'], '990000.00')
        self.assertEqual(response.data['dealership_fee_amount'], '10000.00')

    def test_recharge_preview_client_not_required(self):
        """Client user cannot access recharge preview."""
        self.client.force_authenticate(self.client_user)
        response = self.client.post('/api/dealership/recharges/preview/', {
            'client_id': str(self.client_user.id),
            'fee_mode': 'added_on_top',
            'wallet_credit_amount': '1000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RechargeCreateAPITest(DealershipAPITestBase):
    """Test recharge creation endpoint."""

    def test_create_recharge_success(self):
        """Dealership can create recharge via API."""
        self.client.force_authenticate(self.dealer_user)
        response = self.client.post('/api/dealership/recharges/create/', {
            'client_id': str(self.client_user.id),
            'fee_mode': 'added_on_top',
            'wallet_credit_amount': '50000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'completed')

    def test_create_recharge_blocked_when_over_capacity(self):
        """Recharge over capacity is rejected."""
        self.client.force_authenticate(self.dealer_user)
        response = self.client.post('/api/dealership/recharges/create/', {
            'client_id': str(self.client_user.id),
            'fee_mode': 'added_on_top',
            'wallet_credit_amount': '999999999',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_idempotency_prevents_double_credit(self):
        """Idempotency-Key header prevents double wallet credit."""
        self.client.force_authenticate(self.dealer_user)
        payload = {
            'client_id': str(self.client_user.id),
            'fee_mode': 'added_on_top',
            'wallet_credit_amount': '100000',
            'idempotency_key': 'recharge-dup-key',
        }
        response1 = self.client.post(
            '/api/dealership/recharges/create/', payload, format='json',
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(
            '/api/dealership/recharges/create/', payload, format='json',
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Wallet should be credited only once
        from wallet.models import Wallet
        wallet = Wallet.objects.get(user=self.client_user)
        self.assertEqual(wallet.balance, Decimal('600000'))  # 500K + 100K

    def test_normal_client_denied_recharge(self):
        """Normal client user cannot create recharge."""
        self.client.force_authenticate(self.client_user)
        response = self.client.post('/api/dealership/recharges/create/', {
            'client_id': str(self.client_user.id),
            'fee_mode': 'added_on_top',
            'wallet_credit_amount': '1000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CashoutAPITest(DealershipAPITestBase):
    """Test cash-out API endpoints."""

    def test_cashout_create_by_client(self):
        """Client can create cash-out request."""
        self.client.force_authenticate(self.client_user)
        response = self.client.post('/api/dealership/cashouts/create/', {
            'dealership_id': str(self.profile.id),
            'amount': '100000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('code_issued', response.data['status'])

    def test_cashout_insufficient_wallet_rejected(self):
        """Client without sufficient balance is rejected."""
        self.client.force_authenticate(self.client_user)
        response = self.client.post('/api/dealership/cashouts/create/', {
            'dealership_id': str(self.profile.id),
            'amount': '999999999',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_cashout_by_dealership(self):
        """Dealership can confirm cash-out with correct code."""
        # Client creates cashout
        self.client.force_authenticate(self.client_user)
        create_resp = self.client.post('/api/dealership/cashouts/create/', {
            'dealership_id': str(self.profile.id),
            'amount': '100000',
        }, format='json')
        cashout_id = create_resp.data['id']

        # Dealership confirms
        self.client.force_authenticate(self.dealer_user)

        # Get the confirmation code from the cashout (for testing, we access the model)
        cashout = DealershipClientCashout.objects.get(id=cashout_id)
        # We need to find the code — in production it's sent via notification
        # For test, let's generate and set a known code
        cashout.confirmation_code_hash = hash_confirmation_code('123456')
        cashout.save(update_fields=['confirmation_code_hash'])

        response = self.client.post(
            f'/api/dealership/cashouts/{cashout_id}/confirm-code/',
            {'confirmation_code': '123456'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')

    def test_wrong_dealership_cannot_confirm(self):
        """Wrong dealership cannot confirm cash-out."""
        other_dealer = User.objects.create_user(
            username='other_dealer2', password='test123', role='dealership',
        )
        DealershipProfile.objects.create(
            user=other_dealer,
            business_name='Other Dealer',
            owner_name='Other',
            phone='07700000101',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
        )

        self.client.force_authenticate(self.client_user)
        create_resp = self.client.post('/api/dealership/cashouts/create/', {
            'dealership_id': str(self.profile.id),
            'amount': '100000',
        }, format='json')
        cashout_id = create_resp.data['id']

        # Other dealer tries to confirm
        self.client.force_authenticate(other_dealer)
        response = self.client.post(
            f'/api/dealership/cashouts/{cashout_id}/confirm-code/',
            {'confirmation_code': '000000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_expired_code_rejected(self):
        """Expired confirmation code is rejected."""
        self.client.force_authenticate(self.client_user)
        create_resp = self.client.post('/api/dealership/cashouts/create/', {
            'dealership_id': str(self.profile.id),
            'amount': '100000',
        }, format='json')
        cashout_id = create_resp.data['id']

        # Expire the code
        from django.utils import timezone
        from datetime import timedelta
        cashout = DealershipClientCashout.objects.get(id=cashout_id)
        cashout.code_expires_at = timezone.now() - timedelta(minutes=5)
        cashout.confirmation_code_hash = hash_confirmation_code('123456')
        cashout.save(update_fields=['code_expires_at', 'confirmation_code_hash'])

        self.client.force_authenticate(self.dealer_user)
        response = self.client.post(
            f'/api/dealership/cashouts/{cashout_id}/confirm-code/',
            {'confirmation_code': '123456'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminDealershipAPITest(DealershipAPITestBase):
    """Test admin dealership endpoints."""

    def test_admin_list_dealerships(self):
        """Admin can list dealerships."""
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/admin/dealerships/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_admin_approve_dealership(self):
        """Admin can approve a pending dealership."""
        pending_dealer = User.objects.create_user(
            username='pending_dealer', password='test123', role='dealership',
        )
        pending_profile = DealershipProfile.objects.create(
            user=pending_dealer,
            business_name='Pending Dealer',
            owner_name='Pending',
            phone='07700000102',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.PENDING_REVIEW,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f'/api/admin/dealerships/{pending_profile.id}/approve/',
            {}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')

    def test_admin_suspend_dealership(self):
        """Admin can suspend a dealership."""
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f'/api/admin/dealerships/{self.profile.id}/suspend/',
            {'reason': 'Test suspend'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.suspended)

    def test_admin_block_dealership(self):
        """Admin can block a dealership."""
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f'/api/admin/dealerships/{self.profile.id}/block/',
            {}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.blocked)
        self.assertFalse(self.profile.active)

    def test_admin_unlock_dealership(self):
        """Admin can unlock a financially locked dealership."""
        self.profile.financially_locked = True
        self.profile.save(update_fields=['financially_locked'])

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f'/api/admin/dealerships/{self.profile.id}/unlock/',
            {}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.financially_locked)

    def test_content_moderator_denied(self):
        """Content moderator cannot access admin dealership endpoints."""
        self.client.force_authenticate(self.moderator)
        response = self.client.get('/api/admin/dealerships/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_verify_guarantee(self):
        """Admin can verify a guarantee."""
        guarantee = DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('5000000'),
            status=DealershipGuarantee.Status.PENDING,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f'/api/admin/dealership-guarantees/{guarantee.id}/verify/',
            {}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        guarantee.refresh_from_db()
        self.assertEqual(guarantee.status, DealershipGuarantee.Status.VERIFIED)


class DashboardSummaryTest(DealershipAPITestBase):
    """Test dashboard summary includes dealership metrics."""

    def test_dashboard_includes_dealership_metrics(self):
        """Dashboard summary includes dealership section."""
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/admin/dashboard/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('dealerships', response.data)
        self.assertIn('total_dealerships', response.data['dealerships'])
        self.assertIn('active_dealerships', response.data['dealerships'])
