"""Tests for production settings hardening (Phase 16)."""

from django.test import SimpleTestCase, override_settings


class ProdSettingsHardeningTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    def test_debug_false_in_prod(self):
        from django.conf import settings
        self.assertFalse(settings.DEBUG)

    def test_middleware_order_sane(self):
        from django.conf import settings
        MIDDLEWARE = settings.MIDDLEWARE
        # SecurityMiddleware should come before WhiteNoise when present
        if "whitenoise.middleware.WhiteNoiseMiddleware" in MIDDLEWARE:
            sec_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
            wn_idx = MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware")
            self.assertLess(sec_idx, wn_idx)

    def test_request_id_middleware_present(self):
        from django.conf import settings
        self.assertIn(
            "tiqani_v3.middleware.RequestIDMiddleware",
            settings.MIDDLEWARE,
        )

    def test_drf_schema_class_configured(self):
        from django.conf import settings
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"],
            "drf_spectacular.openapi.AutoSchema",
        )

    def test_spectacular_settings_present(self):
        from django.conf import settings
        self.assertIn("SPECTACULAR_SETTINGS", dir(settings))
        self.assertIn("TITLE", settings.SPECTACULAR_SETTINGS)
