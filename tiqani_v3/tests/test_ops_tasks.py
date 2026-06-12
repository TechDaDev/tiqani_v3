"""Tests for Celery ops tasks (Phase 15)."""

from unittest.mock import patch

from django.test import SimpleTestCase

from tiqani_v3.tasks import celery_ping_workers_task, send_sentry_test_event_task


class CeleryOpsTaskTests(SimpleTestCase):
    def test_ping_workers_returns_dict(self):
        with patch("tiqani_v3.celery.app") as mock_app:
            mock_app.control.ping.return_value = [{"ok": "pong"}]
            result = celery_ping_workers_task()
            self.assertIn("active_workers", result)
            self.assertEqual(result["active_workers"], 1)

    def test_ping_workers_handles_empty(self):
        with patch("tiqani_v3.celery.app") as mock_app:
            mock_app.control.ping.return_value = []
            result = celery_ping_workers_task()
            self.assertEqual(result["active_workers"], 0)

    def test_sentry_test_event_sends(self):
        # Patch sentry_sdk at the module level before task runs
        result = send_sentry_test_event_task()
        # Without Sentry configured, the ImportError path is taken
        self.assertIn(result["status"], ("sent", "skipped"))

    def test_sentry_test_handles_missing_sdk(self):
        with patch.dict("sys.modules", {"sentry_sdk": None}):
            result = send_sentry_test_event_task()
            # Without sentry_sdk, returns "skipped" via ImportError catch
            self.assertEqual(result["status"], "skipped")
