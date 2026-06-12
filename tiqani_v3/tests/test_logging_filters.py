"""Tests for logging filters (Phase 15)."""

import logging

from django.test import SimpleTestCase

from tiqani_v3.logging_filters import (
    SensitiveDataFilter,
    SensitiveHeaderFilter,
    StructuredJSONFormatter,
)


def _make_record(name, level, msg, args=None):
    """Helper to create a LogRecord (compat with Python 3.12+ exc_info arg)."""
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=args or (),
        exc_info=None,
    )


class SensitiveDataFilterTests(SimpleTestCase):
    def setUp(self):
        self.filter = SensitiveDataFilter()

    def test_redacts_password_key(self):
        record = _make_record("test", logging.INFO, "Login %s", ({"password": "secret123"},))
        result = self.filter.filter(record)
        self.assertTrue(result)
        # After filtering, args should either be a tuple with redacted value
        # or the message itself should not contain the secret
        self.assertNotIn("secret123", record.getMessage())

    def test_allows_safe_keys(self):
        record = _make_record("test", logging.INFO, "User %s", ({"email": "test@example.com"},))
        result = self.filter.filter(record)
        self.assertTrue(result)
        self.assertIn("test@example.com", record.getMessage())


class SensitiveHeaderFilterTests(SimpleTestCase):
    def setUp(self):
        self.filter = SensitiveHeaderFilter()

    def test_redacts_authorization_header(self):
        record = _make_record("django.request", logging.WARNING,
                              "Authorization: Bearer some.jwt.token")
        self.filter.filter(record)
        self.assertIn("[REDACTED]", record.msg)
        self.assertNotIn("some.jwt.token", record.msg)


class StructuredJSONFormatterTests(SimpleTestCase):
    def setUp(self):
        self.fmt = StructuredJSONFormatter()

    def test_format_includes_message(self):
        record = _make_record("test", logging.INFO, "hello")
        output = self.fmt.format(record)
        self.assertIn("hello", output)
