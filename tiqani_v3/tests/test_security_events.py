"""Tests for security event helpers (Phase 15)."""

import logging
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory

from tiqani_v3.security_events import log_security_event


class SecurityEventTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("tiqani_v3.security_events.logger")
    def test_logs_security_event(self, mock_logger):
        log_security_event(
            "auth.login.failed",
            user_id=1,
            email="test@example.com",
            detail="Invalid password",
        )
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        self.assertIn("security_event", call_kwargs.get("extra", {}))

    @patch("tiqani_v3.security_events.logger")
    def test_logs_with_request_metadata(self, mock_logger):
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4")
        log_security_event(
            "auth.suspicious_activity",
            user_id=2,
            request=request,
        )
        call_kwargs = mock_logger.warning.call_args[1]
        event = call_kwargs["extra"]["security_event"]
        self.assertEqual(event["ip"], "1.2.3.4")

    @patch("tiqani_v3.security_events.logger")
    def test_handles_none_request(self, mock_logger):
        log_security_event("test.event", user_id=None)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        event = call_kwargs["extra"]["security_event"]
        self.assertEqual(event["ip"], "unknown")
