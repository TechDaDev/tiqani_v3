"""Tests for full contract escrow release."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from contract.models import Contract, ContractAuditEvent
from wallet.models import (
    ContractSettlement, Wallet, WalletTransaction,
    PlatformWallet, PlatformEarning,
)
from wallet.settlement_services import settle_completed_contract

User = get_user_model()


class ContractSettlementTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username="client", password="pass", role="client")
        self.tech_user = User.objects.create_user(username="tech", password="pass", role="technician")
        Wallet.objects.get_or_create(user=self.client_user)
        Wallet.objects.get_or_create(user=self.tech_user)
        self.contract = self._make_contract()
        self.platform_wallet = PlatformWallet.get_global_wallet()

    def test_successful_settlement(self):
        """Full release credits technician, records fees, reduces escrow."""
        tech_wallet = self.tech_user.wallet
        initial_tech = tech_wallet.balance
        initial_platform = self.platform_wallet.balance

        settlement = settle_completed_contract(
            contract_id=str(self.contract.id),
            actor=self.client_user,
        )

        self.assertEqual(settlement.status, ContractSettlement.Status.COMPLETED)
        # Technician credited
        tech_wallet.refresh_from_db()
        self.assertGreater(tech_wallet.balance, initial_tech)
        # Escrow reduced
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.escrow_amount, Decimal("0.00"))
        # Platform credited
        self.platform_wallet.refresh_from_db()
        self.assertGreater(self.platform_wallet.balance, initial_platform)
        # Audit event created
        self.assertTrue(ContractAuditEvent.objects.filter(contract=self.contract).exists())

    def test_duplicate_settlement_raises(self):
        """Second release attempt raises ValueError."""
        settle_completed_contract(contract_id=str(self.contract.id), actor=self.client_user)
        with self.assertRaises(ValueError):
            settle_completed_contract(contract_id=str(self.contract.id), actor=self.client_user)

    def test_idempotency_key(self):
        """Same key returns existing settlement."""
        s1 = settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user, idempotency_key="key-1",
        )
        s2 = settle_completed_contract(
            contract_id=str(self.contract.id), actor=self.client_user, idempotency_key="key-1",
        )
        self.assertEqual(s1.id, s2.id)

    def test_technician_self_release_denied(self):
        """Technician cannot release escrow via service."""
        from wallet.settlement_services import check_settlement_eligibility
        eligible, _ = check_settlement_eligibility(self.contract, self.tech_user)
        self.assertFalse(eligible)

    def test_audit_event_created(self):
        """Settlement creates audit event with correct metadata."""
        settle_completed_contract(contract_id=str(self.contract.id), actor=self.client_user)
        events = ContractAuditEvent.objects.filter(contract=self.contract)
        self.assertTrue(events.exists())
        payload = events.first().payload
        self.assertIn("released_principal", payload)

    def _make_contract(self):
        from accounts.models import ClientProfile, TechnicianProfile
        cp = ClientProfile.objects.create(user=self.client_user)
        tp = TechnicianProfile.objects.create(user=self.tech_user)
        c = Contract.objects.create(
            client=cp, technician=tp,
            agreed_amount=Decimal("500000.00"),
            escrow_amount=Decimal("500000.00"),
            status="completed",
        )
        from wallet.models import PaymentIntent
        PaymentIntent.objects.create(
            contract=c, user=self.client_user,
            amount=Decimal("525000.00"),
            purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
            status=PaymentIntent.Status.PAID,
        )
        from wallet.services import create_contract_payment_breakdown
        create_contract_payment_breakdown(c)
        return c
