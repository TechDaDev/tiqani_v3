"""Tests for ContractSettlement model."""
from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from contract.models import Contract
from wallet.models import ContractSettlement, ContractPaymentBreakdown

User = get_user_model()


class ContractSettlementModelTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")

    def test_create_settlement(self):
        """Basic creation succeeds."""
        s = ContractSettlement.objects.create(
            contract_id=self._make_contract().id,
            released_principal=Decimal("500000.00"),
            technician_net_amount=Decimal("450000.00"),
            technician_commission_amount=Decimal("50000.00"),
            client_service_fee_amount=Decimal("25000.00"),
            total_platform_fee=Decimal("75000.00"),
            status=ContractSettlement.Status.COMPLETED,
        )
        self.assertEqual(s.released_principal, Decimal("500000.00"))
        self.assertEqual(s.status, "completed")

    def test_unique_completed_settlement(self):
        """Only one completed settlement per contract."""
        c = self._make_contract()
        ContractSettlement.objects.create(
            contract=c,
            released_principal=Decimal("100.00"),
            technician_net_amount=Decimal("90.00"),
            technician_commission_amount=Decimal("10.00"),
            client_service_fee_amount=Decimal("5.00"),
            total_platform_fee=Decimal("15.00"),
            status=ContractSettlement.Status.COMPLETED,
        )
        with self.assertRaises(IntegrityError):
            ContractSettlement.objects.create(
                contract=c,
                released_principal=Decimal("100.00"),
                technician_net_amount=Decimal("90.00"),
                technician_commission_amount=Decimal("10.00"),
                client_service_fee_amount=Decimal("5.00"),
                total_platform_fee=Decimal("15.00"),
                status=ContractSettlement.Status.COMPLETED,
            )

    def test_multiple_noncompleted_allowed(self):
        """Multiple pending/processing settlements allowed."""
        c = self._make_contract()
        for _ in range(3):
            ContractSettlement.objects.create(
                contract=c,
                released_principal=Decimal("100.00"),
                technician_net_amount=Decimal("90.00"),
                technician_commission_amount=Decimal("10.00"),
                client_service_fee_amount=Decimal("5.00"),
                total_platform_fee=Decimal("15.00"),
                status=ContractSettlement.Status.PENDING,
            )
        self.assertEqual(ContractSettlement.objects.filter(contract=c).count(), 3)

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        return Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"), escrow_amount=Decimal("500000.00"),
            status="completed",
        )
