"""Tests for contract activation."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contract.models import Contract
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class ActivationTestCase(TestCase):
    """Test contract activation rules."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client1', password='testpass123',
            email='client@test.com', role='client',
            phone_number='07701234567', governorate='Baghdad',
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username='tech1', password='testpass123',
            email='tech@test.com', role='technician',
            phone_number='07701234568', governorate='Basra',
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True,
            job_title='Plumber', about='Expert', years_of_expertise=5,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        self.contract = Contract.objects.create(
            client=self.client_profile,
            technician=self.tech_profile,
            work_description='Test work',
            agreed_amount=Decimal('100000.00'),
            stage_number=2,
            start_date=timezone.now().date(),
            duration_days=10,
            status='in_progress',
            escrow_amount=Decimal('100000.00'),
        )
        self.api_client = APIClient()

    def test_activate_requires_auth(self):
        resp = self.api_client.post(f'/api/contracts/{self.contract.id}/activate/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_activate_as_technician_fails(self):
        self.api_client.force_authenticate(user=self.tech_user)
        resp = self.api_client.post(f'/api/contracts/{self.contract.id}/activate/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_activate_needs_milestones(self):
        self.api_client.force_authenticate(user=self.client_user)
        resp = self.api_client.post(f'/api/contracts/{self.contract.id}/activate/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_success(self):
        from contract.models import ExecutionMilestone
        from wallet.models import PaymentIntent
        ExecutionMilestone.objects.create(
            contract=self.contract, sequence=1,
            title='First milestone', status='DRAFT',
        )
        PaymentIntent.objects.create(
            contract=self.contract,
            user=self.client_user,
            amount=self.contract.agreed_amount,
            status=PaymentIntent.Status.PAID,
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        )
        self.api_client.force_authenticate(user=self.client_user)
        resp = self.api_client.post(f'/api/contracts/{self.contract.id}/activate/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, 'active')
        self.assertIsNotNone(self.contract.activated_at)
