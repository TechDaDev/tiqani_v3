"""Tests for performance_smoke_test management command (Phase 16)."""

import json
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class PerformanceSmokeCommandTests(SimpleTestCase):
    def test_command_runs_successfully(self):
        buf = StringIO()
        call_command("performance_smoke_test", "--iterations", "2", stdout=buf)
        output = buf.getvalue()
        self.assertIn("Performance Smoke Test", output)

    def test_json_output_parses(self):
        buf = StringIO()
        call_command("performance_smoke_test", "--iterations", "2", "--json", stdout=buf)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        self.assertIn("endpoint", data[0])
        self.assertIn("avg_ms", data[0])
        self.assertIn("max_ms", data[0])
