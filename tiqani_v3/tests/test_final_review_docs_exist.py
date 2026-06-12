"""
Tests that Phase 17 final review documentation files exist.
"""

from pathlib import Path
from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class FinalReviewDocsExistTest(SimpleTestCase):
    """Verify that the final backend review documents were created."""

    def test_final_backend_review_exists(self):
        path = BASE_DIR / "docs" / "FINAL_BACKEND_REVIEW.md"
        self.assertTrue(path.exists(), "docs/FINAL_BACKEND_REVIEW.md not found")

    def test_backend_executive_summary_exists(self):
        path = BASE_DIR / "docs" / "BACKEND_EXECUTIVE_SUMMARY.md"
        self.assertTrue(path.exists(), "docs/BACKEND_EXECUTIVE_SUMMARY.md not found")

    def test_frontend_mobile_quickstart_exists(self):
        path = BASE_DIR / "docs" / "FRONTEND_MOBILE_QUICKSTART.md"
        self.assertTrue(path.exists(), "docs/FRONTEND_MOBILE_QUICKSTART.md not found")
