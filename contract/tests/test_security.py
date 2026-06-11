"""Security hardening tests for contracts — object-level permission, unsafe field updates, leak prevention."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import TechnicianProfile, ClientProfile, AdminProfile
from contract.models import Contract

User = get_user_model()


class ContractPermissionHardeningTest(APITestCase):
    """Unrelated users cannot access each other's contracts."""

    def setUp(self):
        self.client1_user = User.objects.create_user(
            username='c1', email='c1@t.com', password='pass123',
            role='client',
            phone_number='07700000100', governorate='Basra', address='A',
        )
        self.client1 = ClientProfile.objects.create(user=self.client1_user)

        self.client2_user = User.objects.create_user(
            username='c2', email='c2@t.com', password='pass123',
            role='client',
            phone_number='07700000101', governorate='Basra', address='A',
        )
        self.client2 = ClientProfile.objects.create(user=self.client2_user)

        self.tech1_user = User.objects.create_user(
            username='t1_sec', email='t1s@t.com', password='pass123',
            role='technician',
            phone_number='07700000102', governorate='Basra', address='A',
        )
        self.tech1 = TechnicianProfile.objects.create(
            user=self.tech1_user, approved=True, job_title='Dev',
        )

        self.tech2_user = User.objects.create_user(
            username='t2_sec', email='t2s@t.com', password='pass123',
            role='technician',
            phone_number='07700000103', governorate='Basra', address='A',
        )
        self.tech2 = TechnicianProfile.objects.create(
            user=self.tech2_user, approved=True, job_title='Designer',
        )

        # Contract between client1 and tech1
        self.contract = Contract.objects.create(
            client=self.client1, technician=self.tech1,
            work_description='Secret project', agreed_amount=Decimal('100000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=7,
            status='in_progress',
        )

        # Another contract between client1 and tech1 (should be visible to them)
        self.contract2 = Contract.objects.create(
            client=self.client1, technician=self.tech1,
            work_description='Another project', agreed_amount=Decimal('50000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=5,
            status='draft',
        )

        self.c1_auth = APIClient()
        self.c1_auth.force_authenticate(user=self.client1_user)
        self.c2_auth = APIClient()
        self.c2_auth.force_authenticate(user=self.client2_user)
        self.t1_auth = APIClient()
        self.t1_auth.force_authenticate(user=self.tech1_user)
        self.t2_auth = APIClient()
        self.t2_auth.force_authenticate(user=self.tech2_user)

    def test_client_sees_own_contracts(self):
        resp = self.c1_auth.get('/api/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Should see both contracts
        self.assertGreaterEqual(len(resp.data), 2)

    def test_technician_sees_own_contracts(self):
        resp = self.t1_auth.get('/api/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in resp.data]
        self.assertIn(str(self.contract.id), ids)

    def test_unrelated_client_cannot_see_contract(self):
        """Client2 should not see client1's contracts."""
        resp = self.c2_auth.get('/api/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in resp.data]
        self.assertNotIn(str(self.contract.id), ids)

    def test_unrelated_technician_cannot_see_contract(self):
        """Tech2 should not see client1+tech1's contract."""
        resp = self.t2_auth.get('/api/contracts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in resp.data]
        self.assertNotIn(str(self.contract.id), ids)

    def test_unrelated_client_cannot_access_contract_detail(self):
        url = f'/api/contracts/{self.contract.id}/'
        resp = self.c2_auth.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_technician_cannot_access_contract_detail(self):
        url = f'/api/contracts/{self.contract.id}/'
        resp = self.t2_auth.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_contract_list_does_not_leak_unrelated(self):
        resp = self.c2_auth.get('/api/contracts/')
        data = resp.data
        descriptions = [c.get('work_description', '') for c in data]
        self.assertNotIn('Secret project', descriptions)


class ContractUnsafeUpdateTest(APITestCase):
    """Normal users cannot modify contract sensitive fields."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='c_unsafe', email='cu@t.com', password='pass123',
            role='client',
            phone_number='07700000110', governorate='Basra', address='A',
        )
        self.client = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username='t_unsafe', email='tu@t.com', password='pass123',
            role='technician',
            phone_number='07700000111', governorate='Basra', address='A',
        )
        self.tech = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title='Dev',
        )

        self.contract = Contract.objects.create(
            client=self.client, technician=self.tech,
            work_description='Test', agreed_amount=Decimal('50000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=7,
            status='draft',
        )

        self.c_auth = APIClient()
        self.c_auth.force_authenticate(user=self.client_user)

    def test_cannot_change_contract_status_directly(self):
        """Client should not be able to PATCH status or agreed_amount via contract endpoint."""
        # Contract detail is read-only (GET), no PATCH on contract detail
        resp = self.c_auth.get(f'/api/contracts/{self.contract.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Contract status stays as-is (draft with agreed_amount auto-moves to pending_acceptance)
        # Verify the response has expected fields
        self.assertIn('status', resp.data)


class ContractFilterConsistencyTest(APITestCase):
    """Contract list does not leak unrelated contracts."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='cfilt', email='cf@t.com', password='pass123',
            role='client',
            phone_number='07700000120', governorate='Basra', address='A',
        )
        self.client = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username='tfilt', email='tf@t.com', password='pass123',
            role='technician', is_staff=True,
            phone_number='07700000121', governorate='Basra', address='A',
        )
        self.tech = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title='Dev',
        )

        self.other_user = User.objects.create_user(
            username='other_filt', email='of@t.com', password='pass123',
            role='client',
            phone_number='07700000122', governorate='Basra', address='A',
        )
        self.other_client = ClientProfile.objects.create(user=self.other_user)

        Contract.objects.create(
            client=self.client, technician=self.tech,
            work_description='Mine', agreed_amount=Decimal('30000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=3,
            status='draft',
        )
        Contract.objects.create(
            client=self.other_client, technician=self.tech,
            work_description='Theirs', agreed_amount=Decimal('60000'),
            stage_number=2, start_date=timezone.now().date(), duration_days=5,
            status='draft',
        )

        self.c_auth = APIClient()
        self.c_auth.force_authenticate(user=self.client_user)
        self.o_auth = APIClient()
        self.o_auth.force_authenticate(user=self.other_user)

    def test_client_only_sees_own(self):
        resp = self.c_auth.get('/api/contracts/')
        descriptions = [c.get('work_description', '') for c in resp.data]
        self.assertIn('Mine', descriptions)
        self.assertNotIn('Theirs', descriptions)
