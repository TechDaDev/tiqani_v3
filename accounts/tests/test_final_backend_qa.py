"""Tests for the final_backend_qa management command."""

from io import StringIO
from django.core.management import call_command
from django.test import TestCase


class FinalBackendQATest(TestCase):

    def test_command_runs_without_error(self):
        out = StringIO()
        call_command('final_backend_qa', stdout=out)
        output = out.getvalue()
        self.assertIn('Final Backend QA Checklist', output)

    def test_output_contains_key_checks(self):
        out = StringIO()
        call_command('final_backend_qa', stdout=out)
        output = out.getvalue()
        # The output should mention core checks
        self.assertIn('Django check', output)
        self.assertIn('Demo users', output)
