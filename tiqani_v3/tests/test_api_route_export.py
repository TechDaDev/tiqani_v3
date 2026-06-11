"""Tests for the export_api_routes management command."""

import os
import tempfile
from io import StringIO
from django.core.management import call_command
from django.test import TestCase


class ExportApiRoutesTest(TestCase):

    def test_command_runs_without_error(self):
        out = StringIO()
        call_command('export_api_routes', stdout=out)
        output = out.getvalue()
        self.assertIn('API Routes', output)

    def test_command_writes_markdown_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_path = f.name
        try:
            call_command('export_api_routes', output=temp_path, stdout=StringIO())
            self.assertTrue(os.path.isfile(temp_path), 'Output file should exist')
            with open(temp_path) as f:
                content = f.read()
            self.assertIn('# API Routes', content)
            self.assertIn('API routes', content)
        finally:
            if os.path.isfile(temp_path):
                os.unlink(temp_path)
