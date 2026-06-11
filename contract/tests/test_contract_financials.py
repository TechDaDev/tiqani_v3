"""Tests for contract + fee integration."""

from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import ClientProfile, TechnicianProfile
from contract.models import Contract, ContractStage
from wallet.models import Wallet, ContractPaymentBreakdown, PaymentIntent, PlatformFeeConfig

User = get_user_model()


class ContractFinancialIntegrationTest(APITestCase):
    """When both accept, financial artifacts are created."""

    def setUp(self):
        self.client = APIClient()

        # Create fee config
        PlatformFeeConfig.objects.create(
            name="Test",
            technician_commission_rate=Decimal("10.00"),
            client_service_fee_rate=Decimal("5.00"),
        )

        # Client
        self.client_user = User.objects.create_user(
            username="client", email="c@test.com",
            password="pass", role="client",
            phone_number="07701234567", governorate="Baghdad", address="A",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        # Technician
        self.tech_user = User.objects.create_user(
            username="tech", email="t@test.com",
            password="pass", role="technician",
            phone_number="07701234568", governorate="Basra", address="B",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title="Dev",
            years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        # Fund wallets (enough for escrow + 10% fee on 500k = 550k client needs)
        for u in [self.client_user, self.tech_user]:
            wallet, _ = Wallet.objects.get_or_create(user=u)
        Wallet.objects.filter(user=self.client_user).update(balance=Decimal("600000"))
        Wallet.objects.filter(user=self.tech_user).update(balance=Decimal("60000"))

        # Create contract with all fields for pending_acceptance
        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Test", agreed_amount=Decimal("500000.00"),
            stage_number=3, start_date=timezone.now().date(),
            duration_days=15,
        )
        self.contract.save()  # triggers contract_duration calc + transition to pending_acceptance
        self.accept_url = f"/api/contracts/{self.contract.id}/accept/"

    def test_both_accept_creates_payment_breakdown(self):
        self.client.force_authenticate(user=self.client_user)
        self.client.post(self.accept_url)
        self.client.force_authenticate(user=self.tech_user)
        self.client.post(self.accept_url)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "in_progress")
        self.assertTrue(hasattr(self.contract, "payment_breakdown"))
        bd = self.contract.payment_breakdown
        self.assertEqual(bd.contract_amount, Decimal("500000.00"))
        self.assertEqual(bd.total_platform_fee, Decimal("75000.00"))

    def test_both_accept_creates_payment_intent(self):
        self.client.force_authenticate(user=self.client_user)
        self.client.post(self.accept_url)
        self.client.force_authenticate(user=self.tech_user)
        self.client.post(self.accept_url)
        intents = PaymentIntent.objects.filter(contract=self.contract)
        self.assertEqual(intents.count(), 1)

    def test_accept_twice_does_not_duplicate_breakdown(self):
        self.client.force_authenticate(user=self.client_user)
        self.client.post(self.accept_url)
        self.client.force_authenticate(user=self.tech_user)
        self.client.post(self.accept_url)
        count = ContractPaymentBreakdown.objects.filter(contract=self.contract).count()
        self.assertEqual(count, 1)


class StageFinancialTest(APITestCase):
    """Stage approval releases proportional amounts."""

    def setUp(self):
        self.client = APIClient()
        PlatformFeeConfig.objects.create(
            name="Test",
            technician_commission_rate=Decimal("10.00"),
            client_service_fee_rate=Decimal("5.00"),
        )

        self.client_user = User.objects.create_user(
            username="client", email="c@test.com", password="pass", role="client",
            phone_number="07701234567", governorate="Baghdad", address="A",
        )
        self.client_profile = ClientProfile.objects.create(user=self.client_user)

        self.tech_user = User.objects.create_user(
            username="tech", email="t@test.com", password="pass", role="technician",
            phone_number="07701234568", governorate="Basra", address="B",
        )
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.tech_user, approved=True, job_title="Dev",
            years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.tech_profile.pk).update(is_complete=True)

        for u in [self.client_user, self.tech_user]:
            wallet, _ = Wallet.objects.get_or_create(user=u)
        Wallet.objects.filter(user=self.client_user).update(balance=Decimal("600000"))
        Wallet.objects.filter(user=self.tech_user).update(balance=Decimal("60000"))

        self.contract = Contract.objects.create(
            client=self.client_profile, technician=self.tech_profile,
            work_description="Project", agreed_amount=Decimal("900.00"),
            stage_number=3, start_date=timezone.now().date(),
            duration_days=15, status="in_progress",
        )
        self.contract.save()
        if self.contract.stages.count() == 0:
            for i in range(1, 4):
                ContractStage.objects.create(
                    contract=self.contract, stage_number=i,
                    amount=Decimal("300.00"),
                    deadline=timezone.now().date() + timezone.timedelta(days=i * 5),
                )
        self.stage = self.contract.stages.first()
        self.stage.mark_complete()
        self.approve_url = f"/api/contracts/{self.contract.id}/stages/{self.stage.id}/approve/"

        # Ensure breakdown exists
        from wallet.services import ensure_contract_payment_breakdown
        ensure_contract_payment_breakdown(self.contract)

    def test_stage_approval_creates_platform_earnings(self):
        self.client.force_authenticate(user=self.client_user)
        resp = self.client.post(self.approve_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        from wallet.models import PlatformEarning
        earnings = PlatformEarning.objects.filter(contract=self.contract)
        self.assertGreater(earnings.count(), 0)
