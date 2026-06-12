"""Tests for audit_api_consistency management command (Phase 16)."""

import json
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class AuditApiConsistencyCommandTests(SimpleTestCase):
    def test_command_runs_successfully(self):
        buf = StringIO()
        call_command("audit_api_consistency", stdout=buf)
        output = buf.getvalue()
        self.assertIn("API Consistency Audit", output)

    def test_json_output_parses(self):
        buf = StringIO()
        call_command("audit_api_consistency", "--json", stdout=buf)
        data = json.loads(buf.getvalue())
        self.assertIn("url_prefixes_found", data)
        self.assertIn("resolvable_endpoints", data)
