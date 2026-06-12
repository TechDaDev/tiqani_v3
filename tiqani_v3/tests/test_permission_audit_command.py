"""Tests for audit_permissions management command (Phase 16)."""

import json
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class AuditPermissionsCommandTests(SimpleTestCase):
    def test_command_runs_successfully(self):
        buf = StringIO()
        call_command("audit_permissions", stdout=buf)
        output = buf.getvalue()
        self.assertIn("Permission Audit", output)

    def test_json_output_parses(self):
        buf = StringIO()
        call_command("audit_permissions", "--json", stdout=buf)
        data = json.loads(buf.getvalue())
        self.assertIn("permission_classes_importable", data)
        self.assertIn("sensitive_endpoints", data)
