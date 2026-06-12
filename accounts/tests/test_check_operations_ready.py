"""Tests for check_operations_ready management command (Phase 15)."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings


class CheckOperationsReadyCommandTests(TestCase):
    def test_command_returns_success_output(self):
        buf = StringIO()
        call_command("check_operations_ready", stdout=buf)
        output = buf.getvalue()
        self.assertIn("Operations Readiness Check", output)
        self.assertIn("Database reachable", output)

    def test_command_reports_sentry_warning_when_not_set(self):
        buf = StringIO()
        with override_settings(SENTRY_DSN=""):
            call_command("check_operations_ready", stdout=buf)
        output = buf.getvalue()
        self.assertIn("SENTRY_DSN not set", output)

    def test_command_reports_sentry_ok_when_set(self):
        buf = StringIO()
        with override_settings(SENTRY_DSN="https://key@o123.ingest.sentry.io/123"):
            call_command("check_operations_ready", stdout=buf)
        output = buf.getvalue()
        self.assertIn("SENTRY_DSN configured", output)
