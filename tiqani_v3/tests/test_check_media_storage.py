"""
Tests for the check_media_storage management command.
"""

from io import StringIO
from django.test import TestCase
from django.core.management import call_command


class CheckMediaStorageCommandTest(TestCase):
    """Test check_media_storage command output."""

    def test_command_runs_in_local_mode(self):
        """Command runs without errors in local mode."""
        out = StringIO()
        call_command("check_media_storage", stdout=out)
        output = out.getvalue()
        self.assertIn("Media Storage Check", output)
        self.assertIn("Local filesystem", output)

    def test_command_shows_upload_limits(self):
        """Command prints upload limits."""
        out = StringIO()
        call_command("check_media_storage", stdout=out)
        output = out.getvalue()
        self.assertIn("Max profile image", output)
        self.assertIn("Max category icon", output)
        self.assertIn("Max document", output)
        self.assertIn("Max proof file", output)

    def test_command_exits_cleanly(self):
        """Command exits with status 0."""
        out = StringIO()
        try:
            call_command("check_media_storage", stdout=out)
        except SystemExit as e:
            self.assertEqual(e.code, 0)
