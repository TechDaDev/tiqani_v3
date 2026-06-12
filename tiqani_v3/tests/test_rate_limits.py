"""Tests for DRF throttle settings (Phase 16)."""

from django.conf import settings
from django.test import SimpleTestCase


class RateLimitSettingsTests(SimpleTestCase):
    """Verify throttle scopes are configured."""

    def test_expected_throttle_scopes_exist(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        expected_scopes = [
            "anon",
            "user",
            "login",
            "password_reset",
            "otp",
            "dealership_finance",
            "wallet_finance",
            "reviews",
            "notifications",
            "schema",
        ]
        for scope in expected_scopes:
            with self.subTest(scope=scope):
                self.assertIn(scope, rates)
