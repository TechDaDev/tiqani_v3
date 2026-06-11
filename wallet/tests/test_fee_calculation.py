"""Tests for fee calculation engine."""

from decimal import Decimal
from django.test import TestCase
from wallet.models import PlatformFeeConfig
from wallet.services import calculate_contract_breakdown, get_active_fee_config


class FeeCalculationTest(TestCase):
    def setUp(self):
        self.config = PlatformFeeConfig.objects.create(
            name="Test 15%",
            technician_commission_rate=Decimal("10.00"),
            client_service_fee_rate=Decimal("5.00"),
        )

    def test_500000_breakdown(self):
        result = calculate_contract_breakdown(Decimal("500000"), self.config)
        self.assertEqual(result["technician_commission_amount"], Decimal("50000.00"))
        self.assertEqual(result["client_service_fee_amount"], Decimal("25000.00"))
        self.assertEqual(result["total_platform_fee"], Decimal("75000.00"))
        self.assertEqual(result["client_total_amount"], Decimal("525000.00"))
        self.assertEqual(result["technician_net_amount"], Decimal("450000.00"))

    def test_get_active_config_creates_default(self):
        PlatformFeeConfig.objects.all().delete()
        config = get_active_fee_config()
        self.assertIsNotNone(config)
        self.assertTrue(config.is_active)

    def test_changing_config_does_not_affect_existing_calc(self):
        result1 = calculate_contract_breakdown(Decimal("1000"), self.config)
        self.config.technician_commission_rate = Decimal("20.00")
        self.config.save()
        result2 = calculate_contract_breakdown(Decimal("1000"), self.config)
        self.assertNotEqual(result1["technician_commission_amount"], result2["technician_commission_amount"])

    def test_zero_amount(self):
        result = calculate_contract_breakdown(Decimal("0"), self.config)
        self.assertEqual(result["technician_commission_amount"], Decimal("0.00"))
        self.assertEqual(result["client_total_amount"], Decimal("0.00"))

    def test_small_amount_precision(self):
        result = calculate_contract_breakdown(Decimal("1"), self.config)
        self.assertEqual(result["technician_commission_amount"], Decimal("0.10"))
        self.assertEqual(result["client_service_fee_amount"], Decimal("0.05"))
