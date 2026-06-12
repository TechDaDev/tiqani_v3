"""
Tests for dealership models and financial formulas.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from dealership.models import (
    DealershipProfile,
    DealershipGuarantee,
    DealershipRechargeFeeConfig,
    DealershipClientRecharge,
    DealershipClientCashout,
    DealershipCreditLedger,
    DealershipSettlement,
)
from dealership.services import (
    calculate_total_guarantee,
    calculate_usable_credit_limit,
    calculate_net_exposure,
    calculate_available_recharge_capacity,
    calculate_recharge_fee,
    should_lock_dealership,
    create_recharge,
    create_cashout,
    confirm_cashout,
    generate_settlement,
    complete_settlement,
)

User = get_user_model()


class GuaranteeCalculationTest(TestCase):
    """Test guarantee total calculation and usable limit."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='dealership_test', password='test123', role='dealership',
        )
        self.profile = DealershipProfile.objects.create(
            user=self.user,
            business_name='Test Dealership',
            owner_name='Owner',
            phone='07700000001',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
            usage_limit_percent=Decimal('80.00'),
        )

    def test_total_guarantee_sum(self):
        """Total guarantee should be sum of all verified guarantees."""
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('1000000'),
            bank_check_amount=Decimal('2000000'),
            legal_document_amount=Decimal('500000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )
        expected = Decimal('3500000')
        result = calculate_total_guarantee(self.profile)
        self.assertEqual(result, expected)

    def test_total_guarantee_ignores_pending(self):
        """Only verified guarantees count toward total."""
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('1000000'),
            status=DealershipGuarantee.Status.PENDING,
        )
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('2000000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )
        result = calculate_total_guarantee(self.profile)
        self.assertEqual(result, Decimal('2000000'))

    def test_usable_credit_limit_calculation(self):
        """80% of 5M = 4M."""
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('5000000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )
        result = calculate_usable_credit_limit(self.profile)
        self.assertEqual(result, Decimal('4000000'))

    def test_net_exposure_starts_zero(self):
        """Fresh dealership has zero net exposure."""
        result = calculate_net_exposure(self.profile)
        self.assertEqual(result, Decimal('0.00'))

    def test_available_capacity_starts_as_limit(self):
        """Available = usable_limit - 0."""
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('5000000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )
        result = calculate_available_recharge_capacity(self.profile)
        self.assertEqual(result, Decimal('4000000'))


class RechargeFeeCalculationTest(TestCase):
    """Test fee calculation formulas."""

    def setUp(self):
        self.fee_config = DealershipRechargeFeeConfig.objects.create(
            fee_percent=Decimal('1.00'),
            default_fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            is_active=True,
        )

    def test_added_on_top_fee(self):
        """1M wallet credit, 1% fee = 10K fee, 1.01M cash received."""
        calc = calculate_recharge_fee(
            wallet_credit_amount=Decimal('1000000'),
            fee_config=self.fee_config,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
        )
        self.assertEqual(calc['wallet_credit_amount'], Decimal('1000000'))
        self.assertEqual(calc['dealership_fee_amount'], Decimal('10000'))
        self.assertEqual(calc['cash_received_amount'], Decimal('1010000'))
        self.assertEqual(calc['dealership_exposure_amount'], Decimal('1000000'))
        self.assertEqual(calc['fee_percent'], Decimal('1.00'))

    def test_deducted_from_deposit_fee(self):
        """1M cash received, 1% fee = 10K fee, 990K wallet credit."""
        calc = calculate_recharge_fee(
            cash_received_amount=Decimal('1000000'),
            fee_config=self.fee_config,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.DEDUCTED_FROM_DEPOSIT,
        )
        self.assertEqual(calc['cash_received_amount'], Decimal('1000000'))
        self.assertEqual(calc['dealership_fee_amount'], Decimal('10000'))
        self.assertEqual(calc['wallet_credit_amount'], Decimal('990000'))
        self.assertEqual(calc['dealership_exposure_amount'], Decimal('990000'))
        self.assertEqual(calc['fee_percent'], Decimal('1.00'))

    def test_fee_does_not_affect_exposure(self):
        """Exposure is always wallet_credit_amount, not including fee."""
        calc = calculate_recharge_fee(
            wallet_credit_amount=Decimal('500000'),
            fee_config=self.fee_config,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
        )
        self.assertEqual(calc['dealership_exposure_amount'], Decimal('500000'))
        self.assertNotEqual(calc['dealership_exposure_amount'], calc['cash_received_amount'])


class LockRuleTest(TestCase):
    """Test dealership financial lock at 80% threshold."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='lock_test', password='test123', role='dealership',
        )
        self.profile = DealershipProfile.objects.create(
            user=self.user,
            business_name='Lock Test',
            owner_name='Owner',
            phone='07700000002',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
            usage_limit_percent=Decimal('80.00'),
            single_cashout_limit=Decimal('10000000'),
            daily_cashout_limit=Decimal('50000000'),
        )
        # 10M verified guarantee → 8M usable limit
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('10000000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )

    def test_lock_at_threshold(self):
        """Adding 8M exposure should trigger lock."""
        will_lock, net, limit = should_lock_dealership(
            self.profile, Decimal('8000000')
        )
        self.assertTrue(will_lock)

    def test_no_lock_below_threshold(self):
        """Adding 7.9M exposure should not trigger lock."""
        will_lock, net, limit = should_lock_dealership(
            self.profile, Decimal('7900000')
        )
        self.assertFalse(will_lock)

    def test_cashout_reduces_exposure(self):
        """Processing a cashout reduces net exposure."""
        # Add 5M recharge exposure first
        from wallet.models import Wallet
        client = User.objects.create_user(
            username='client_lock', password='test123', role='client',
        )
        Wallet.objects.create(user=client, balance=Decimal('5000000'))

        recharge = create_recharge(
            dealership=self.profile,
            client=client,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            wallet_credit_amount=Decimal('5000000'),
            created_by=self.user,
        )

        net_before = calculate_net_exposure(self.profile)
        self.assertEqual(net_before, Decimal('5000000'))

        # Create and confirm cashout
        cashout, _ = create_cashout(
            dealership=self.profile,
            client=client,
            amount=Decimal('2000000'),
        )
        confirm_cashout(cashout, self.user)

        net_after = calculate_net_exposure(self.profile)
        self.assertEqual(net_after, Decimal('3000000'))

    def test_financial_lock_sets_flag_on_recharge(self):
        """Recharge that reaches limit sets financially_locked."""
        from wallet.models import Wallet
        client = User.objects.create_user(
            username='client_lock2', password='test123', role='client',
        )
        Wallet.objects.create(user=client, balance=Decimal('0'))

        # Recharge 8M (reaches the 8M limit)
        create_recharge(
            dealership=self.profile,
            client=client,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            wallet_credit_amount=Decimal('8000000'),
            created_by=self.user,
        )

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.financially_locked)


class RechargeFlowTest(TestCase):
    """Test full recharge flow."""

    def setUp(self):
        self.dealer_user = User.objects.create_user(
            username='dealer_recharge', password='test123', role='dealership',
        )
        self.profile = DealershipProfile.objects.create(
            user=self.dealer_user,
            business_name='Recharge Test',
            owner_name='Owner',
            phone='07700000003',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
            usage_limit_percent=Decimal('80.00'),
        )
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('10000000'),  # 10M → 8M limit
            status=DealershipGuarantee.Status.VERIFIED,
        )
        DealershipRechargeFeeConfig.objects.create(
            fee_percent=Decimal('1.00'),
            is_active=True,
        )
        self.client_user = User.objects.create_user(
            username='client_recharge', password='test123', role='client',
        )
        from wallet.models import Wallet
        Wallet.objects.create(user=self.client_user, balance=Decimal('0'))

    def test_recharge_increases_wallet(self):
        """Client wallet increases after recharge."""
        recharge, created = create_recharge(
            dealership=self.profile,
            client=self.client_user,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            wallet_credit_amount=Decimal('100000'),
            created_by=self.dealer_user,
        )
        self.assertTrue(created)
        self.assertEqual(recharge.status, DealershipClientRecharge.Status.COMPLETED)
        from wallet.models import Wallet
        wallet = Wallet.objects.get(user=self.client_user)
        self.assertEqual(wallet.balance, Decimal('100000'))

    def test_recharge_blocked_when_over_capacity(self):
        """Recharge exceeding available capacity is rejected."""
        # First recharge 8M (full limit)
        create_recharge(
            dealership=self.profile,
            client=self.client_user,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            wallet_credit_amount=Decimal('8000000'),
            created_by=self.dealer_user,
        )

        # Second recharge should be blocked
        with self.assertRaises(ValueError):
            create_recharge(
                dealership=self.profile,
                client=self.client_user,
                fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
                wallet_credit_amount=Decimal('1000'),
                created_by=self.dealer_user,
            )

    def test_idempotency_prevents_double_credit(self):
        """Same idempotency key returns existing recharge."""
        recharge1, created1 = create_recharge(
            dealership=self.profile,
            client=self.client_user,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            wallet_credit_amount=Decimal('50000'),
            created_by=self.dealer_user,
            idempotency_key='unique-key-123',
        )
        self.assertTrue(created1)

        recharge2, created2 = create_recharge(
            dealership=self.profile,
            client=self.client_user,
            fee_mode=DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP,
            wallet_credit_amount=Decimal('50000'),
            created_by=self.dealer_user,
            idempotency_key='unique-key-123',
        )
        self.assertFalse(created2)
        self.assertEqual(recharge1.id, recharge2.id)

        # Wallet should only be credited once
        from wallet.models import Wallet
        wallet = Wallet.objects.get(user=self.client_user)
        self.assertEqual(wallet.balance, Decimal('50000'))


class CashoutFlowTest(TestCase):
    """Test full cash-out flow."""

    def setUp(self):
        self.dealer_user = User.objects.create_user(
            username='dealer_cashout', password='test123', role='dealership',
        )
        self.profile = DealershipProfile.objects.create(
            user=self.dealer_user,
            business_name='Cashout Test',
            owner_name='Owner',
            phone='07700000004',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
            usage_limit_percent=Decimal('80.00'),
            cashout_enabled=True,
        )
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('10000000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )
        DealershipRechargeFeeConfig.objects.create(
            fee_percent=Decimal('1.00'),
            is_active=True,
        )
        self.client_user = User.objects.create_user(
            username='client_cashout', password='test123', role='client',
        )
        from wallet.models import Wallet
        Wallet.objects.create(user=self.client_user, balance=Decimal('500000'))

    def test_cashout_created_by_client(self):
        """Client can create a cash-out request."""
        cashout, created = create_cashout(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal('100000'),
        )
        self.assertTrue(created)
        self.assertEqual(cashout.status, DealershipClientCashout.Status.CODE_ISSUED)

    def test_cashout_insufficient_wallet_rejected(self):
        """Client without enough wallet balance is rejected."""
        with self.assertRaises(ValueError) as ctx:
            create_cashout(
                dealership=self.profile,
                client=self.client_user,
                amount=Decimal('999999999'),
            )
        self.assertIn('Insufficient', str(ctx.exception))

    def test_confirm_cashout_deducts_wallet(self):
        """Confirming cash-out deducts from client wallet."""
        cashout, _ = create_cashout(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal('200000'),
        )
        confirm_cashout(cashout, self.dealer_user)

        from wallet.models import Wallet
        wallet = Wallet.objects.get(user=self.client_user)
        self.assertEqual(wallet.balance, Decimal('300000'))

        cashout.refresh_from_db()
        self.assertEqual(cashout.status, DealershipClientCashout.Status.COMPLETED)

    def test_wrong_dealership_cannot_confirm(self):
        """Only the owning dealership can confirm cash-out."""
        other_user = User.objects.create_user(
            username='other_dealer', password='test123', role='dealership',
        )
        other_profile = DealershipProfile.objects.create(
            user=other_user,
            business_name='Other',
            owner_name='Other',
            phone='07700000005',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
        )

        cashout, _ = create_cashout(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal('100000'),
        )

        with self.assertRaises(ValueError):
            confirm_cashout(cashout, other_user)

    def test_expired_code_rejected(self):
        """Expired confirmation code is rejected."""
        cashout, _ = create_cashout(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal('100000'),
        )
        # Manually expire the code
        from django.utils import timezone
        from datetime import timedelta
        cashout.code_expires_at = timezone.now() - timedelta(minutes=1)
        cashout.save(update_fields=['code_expires_at'])

        with self.assertRaises(ValueError):
            confirm_cashout(cashout, self.dealer_user)

    def test_cashout_no_fee_charged(self):
        """Cash-out amount is exact amount, no dealership fee."""
        cashout, _ = create_cashout(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal('250000'),
        )
        confirm_cashout(cashout, self.dealer_user)

        from wallet.models import Wallet
        wallet = Wallet.objects.get(user=self.client_user)
        self.assertEqual(wallet.balance, Decimal('250000'))  # 500K - 250K

    def test_ledger_entry_created_for_cashout(self):
        """Cash-out creates a credit ledger entry."""
        cashout, _ = create_cashout(
            dealership=self.profile,
            client=self.client_user,
            amount=Decimal('100000'),
        )
        confirm_cashout(cashout, self.dealer_user)

        ledger_exists = DealershipCreditLedger.objects.filter(
            dealership=self.profile,
            transaction_type=DealershipCreditLedger.TransactionType.CLIENT_CASHOUT,
        ).exists()
        self.assertTrue(ledger_exists)


class SettlementTest(TestCase):
    """Test settlement generation and completion."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_settle', password='test123',
        )
        self.dealer_user = User.objects.create_user(
            username='dealer_settle', password='test123', role='dealership',
        )
        self.profile = DealershipProfile.objects.create(
            user=self.dealer_user,
            business_name='Settle Test',
            owner_name='Owner',
            phone='07700000006',
            governorate='Baghdad',
            address='Test',
            status=DealershipProfile.Status.ACTIVE,
            active=True,
            usage_limit_percent=Decimal('80.00'),            single_cashout_limit=Decimal('10000000'),
            daily_cashout_limit=Decimal('50000000'),        )
        DealershipGuarantee.objects.create(
            dealership=self.profile,
            cash_amount=Decimal('10000000'),
            status=DealershipGuarantee.Status.VERIFIED,
        )
        self.client_user = User.objects.create_user(
            username='client_settle', password='test123', role='client',
        )
        from wallet.models import Wallet
        Wallet.objects.create(user=self.client_user, balance=Decimal('10000000'))

    def test_generate_settlement(self):
        """Settlement can be generated for a dealership."""
        settlement = generate_settlement(
            dealership=self.profile,
            period_start='2026-01-01',
            period_end='2026-12-31',
            created_by=self.admin,
        )
        self.assertEqual(settlement.status, DealershipSettlement.Status.DRAFT)
        self.assertIsNotNone(settlement.net_amount)

    def test_complete_settlement(self):
        """Completing settlement updates status and creates ledger."""
        settlement = generate_settlement(
            dealership=self.profile,
            period_start='2026-01-01',
            period_end='2026-12-31',
            created_by=self.admin,
        )
        complete_settlement(settlement, self.admin)

        settlement.refresh_from_db()
        self.assertEqual(settlement.status, DealershipSettlement.Status.COMPLETED)
        self.assertIsNotNone(settlement.settled_at)
