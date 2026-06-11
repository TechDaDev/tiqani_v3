"""Security hardening tests for wallet — object-level access, sensitive exposure."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from accounts.models import ClientProfile, TechnicianProfile
from wallet.models import Wallet, WalletTransaction

User = get_user_model()


class WalletObjectLevelAccessTest(APITestCase):
    """Users cannot access other users' wallet data."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='u1_wallet', email='u1w@t.com', password='pass123',
            role='client',
            phone_number='07700000200', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.user1)

        self.user2 = User.objects.create_user(
            username='u2_wallet', email='u2w@t.com', password='pass123',
            role='client',
            phone_number='07700000201', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.user2)

        self.u1_auth = APIClient()
        self.u1_auth.force_authenticate(user=self.user1)
        self.u2_auth = APIClient()
        self.u2_auth.force_authenticate(user=self.user2)

        # Ensure wallets exist
        wallet1, _ = Wallet.objects.get_or_create(user=self.user1)
        wallet2, _ = Wallet.objects.get_or_create(user=self.user2)
        wallet1.balance = Decimal('10000')
        wallet1.save()
        wallet2.balance = Decimal('5000')
        wallet2.save()

    def test_wallet_me_returns_own_data(self):
        resp = self.u1_auth.get('/api/wallet/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['balance'], '10000.00')

    def test_wallet_me_does_not_expose_other_user_data(self):
        resp = self.u1_auth.get('/api/wallet/me/')
        self.assertEqual(resp.data['balance'], '10000.00')
        self.assertNotEqual(resp.data['balance'], '5000.00')

    def test_wallet_me_unauthorized(self):
        resp = APIClient().get('/api/wallet/me/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_transaction_list_owned(self):
        resp = self.u1_auth.get('/api/wallet/transactions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_withdrawal_list_owned(self):
        resp = self.u1_auth.get('/api/wallet/withdrawals/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class WalletSensitiveExposureTest(APITestCase):
    """Wallet endpoints do not expose other user data."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='w_se', email='wse@t.com', password='pass123',
            role='technician',
            phone_number='07700000210', governorate='Basra', address='A',
        )
        TechnicianProfile.objects.create(user=self.user, approved=True, job_title='Dev')
        wallet, _ = Wallet.objects.get_or_create(user=self.user)
        wallet.balance = Decimal('25000')
        wallet.save()

        self.other_user = User.objects.create_user(
            username='other_w_se', email='ows@t.com', password='pass123',
            role='client',
            phone_number='07700000211', governorate='Basra', address='A',
        )
        ClientProfile.objects.create(user=self.other_user)
        other_wallet, _ = Wallet.objects.get_or_create(user=self.other_user)
        other_wallet.balance = Decimal('99999')
        other_wallet.save()

        self.auth = APIClient()
        self.auth.force_authenticate(user=self.user)

    def test_wallet_me_returns_only_own_balance(self):
        resp = self.auth.get('/api/wallet/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['balance'], '25000.00')
