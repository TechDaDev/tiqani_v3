"""Shared test base for Phase 7 funding tests."""
from decimal import Decimal
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from wallet.models import Wallet, PaymentIntent, WalletTransaction, ContractPaymentBreakdown, PlatformFeeConfig
from contract.models import Contract
from accounts.models import ClientProfile, TechnicianProfile

User = get_user_model()


class FundingTestBase(APITestCase):
    """Sets up client, technician, contract, and Wallet."""

    def setUp(self):
        self.client_api = APIClient()

        # Users
        self.client_user = User.objects.create_user(
            username="fund_client", email="fc@test.com", password="pass",
            role="client", phone_number="07701234001", governorate="Baghdad", address="A",
        )
        self.tech_user = User.objects.create_user(
            username="fund_tech", email="ft@test.com", password="pass",
            role="technician", phone_number="07701234002", governorate="Basra", address="B",
        )
        self.other_client = User.objects.create_user(
            username="other_client", email="oc@test.com", password="pass",
            role="client", phone_number="07701234003", governorate="Erbil", address="C",
        )
        User.objects.create_user(
            username="fund_admin", email="fa@test.com", password="pass",
            is_staff=True, role="admin",
        )

        # Profiles
        self.cp = ClientProfile.objects.create(user=self.client_user)
        self.tp = TechnicianProfile.objects.create(user=self.tech_user, approved=True)
        self.ocp = ClientProfile.objects.create(user=self.other_client)

        # Wallets
        Wallet.objects.get_or_create(user=self.client_user, defaults={"balance": Decimal("0")})
        Wallet.objects.get_or_create(user=self.tech_user, defaults={"balance": Decimal("0")})
        Wallet.objects.get_or_create(user=self.other_client, defaults={"balance": Decimal("0")})

        # Contract — in_progress, with agreed_amount
        self.contract = Contract.objects.create(
            client=self.cp, technician=self.tp,
            agreed_amount=Decimal("500000.00"),
            currency="IQD",
            status="in_progress",
            start_date=timezone.now().date(),
            duration_days=10,
        )

        # Ensure fee config exists
        PlatformFeeConfig.get_active_config()

    def _fund_contract(self, contract):
        """Helper: create a PAID payment intent + WalletTransaction to mark contract funded."""
        intent = PaymentIntent.objects.create(
            contract=contract,
            user=self.client_user,
            amount=Decimal("525000.00"),
            currency="IQD",
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PAID,
            paid_at=timezone.now(),
        )
        wallet = self.client_user.wallet
        wallet.balance += intent.amount
        wallet.save(update_fields=["balance"])
        WalletTransaction.objects.create(
            wallet=wallet, contract=contract,
            transaction_type=WalletTransaction.Type.DEPOSIT,
            amount=intent.amount,
            description=f"Funding deposit – {contract.contract_reference}",
        )
        WalletTransaction.objects.create(
            wallet=wallet, contract=contract,
            transaction_type=WalletTransaction.Type.ESCROW,
            amount=contract.agreed_amount,
            description=f"Escrow – {contract.contract_reference}",
        )
        contract.escrow_amount = contract.agreed_amount
        contract.save(update_fields=["escrow_amount"])
        return intent

    def _ensure_breakdown(self, contract):
        """Ensure ContractPaymentBreakdown exists."""
        from wallet.services import ensure_contract_payment_breakdown
        return ensure_contract_payment_breakdown(contract)
