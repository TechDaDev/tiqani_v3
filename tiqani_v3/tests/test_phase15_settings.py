"""Tests for Phase 15 settings additions (Sentry, logging, middleware)."""

from django.conf import settings
from django.test import SimpleTestCase


class Phase15SettingsTests(SimpleTestCase):
    def test_logging_has_sensitive_filters(self):
        """Verify LOGGING config includes sensitive-data filters."""
        LOGGING = settings.LOGGING
        self.assertIn("sensitive_redact", LOGGING.get("filters", {}))
        self.assertIn("sensitive_header_redact", LOGGING.get("filters", {}))

    def test_middleware_includes_request_id(self):
        self.assertIn(
            "tiqani_v3.middleware.RequestIDMiddleware",
            settings.MIDDLEWARE,
        )

    def test_health_urls_registered(self):
        from django.urls import resolve

        from tiqani_v3.views import health_live, health_ready, health_deep

        self.assertEqual(resolve("/api/health/live/").func, health_live)
        self.assertEqual(resolve("/api/health/ready/").func, health_ready)
        self.assertEqual(resolve("/api/health/deep/").func, health_deep)

    def test_sentry_env_vars_parsed(self):
        # Should be safe defaults
        self.assertIsNotNone(settings.SENTRY_DSN)
        self.assertIsNotNone(settings.SENTRY_ENVIRONMENT)
        self.assertIsNotNone(settings.SENTRY_TRACES_SAMPLE_RATE)
