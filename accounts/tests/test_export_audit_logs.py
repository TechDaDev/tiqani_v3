"""Tests for export_audit_logs management command (Phase 15)."""

import json

from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


class ExportAuditLogsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="audit_user",
            password="testpass123",
            email="audit@test.com",
        )

    def test_export_json_format(self):
        LogEntry.objects.log_action(
            user_id=self.user.pk,
            content_type_id=get_content_type_for_model(self.user).pk,
            object_id=str(self.user.pk),
            object_repr="test obj",
            action_flag=1,
        )
        import io
        buf = io.StringIO()
        call_command("export_audit_logs", "--days", "30", "--format", "json", stdout=buf)
        output = buf.getvalue()
        self.assertIn("admin_log", output)

    def test_export_csv_format(self):
        import io
        buf = io.StringIO()
        call_command("export_audit_logs", "--days", "30", "--format", "csv", stdout=buf)
        output = buf.getvalue()
        # CSV should have headers
        self.assertIn("source", output)
