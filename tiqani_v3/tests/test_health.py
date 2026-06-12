"""Tests for health check endpoints (Phase 15)."""

from django.test import TestCase, override_settings


class HealthEndpointTests(TestCase):
    """Verify liveness, readiness, and deep health endpoints."""

    def test_liveness_returns_200(self):
        resp = self.client.get("/api/health/live/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "alive")

    def test_readiness_returns_200(self):
        resp = self.client.get("/api/health/ready/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "ok")

    def test_deep_returns_200(self):
        resp = self.client.get("/api/health/deep/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "tiqani_v3")
        self.assertEqual(data["database"], "ok")

    def test_deep_includes_celery_status(self):
        resp = self.client.get("/api/health/deep/")
        data = resp.json()
        # In test mode (CELERY_TASK_ALWAYS_EAGER=True), celery is "eager_mode"
        # Without Redis it may be "error"
        self.assertIn(data["celery"], ("eager_mode", "ok", "not_configured", "no_workers", "error"))

    def test_legacy_health_alias_works(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")
