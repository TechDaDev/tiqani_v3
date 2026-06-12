"""Tests for Phase 16 documentation existence and structure."""

from pathlib import Path

from django.test import SimpleTestCase

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"

REQUIRED_DOCS = [
    "PERMISSION_MATRIX.md",
    "DATABASE_INDEX_REVIEW.md",
    "NGINX_REVERSE_PROXY.md",
    "BACKUP_RESTORE.md",
    "PERFORMANCE_SMOKE_TESTS.md",
    "LAUNCH_READINESS_CHECKLIST.md",
]


class Phase16DocsExistTests(SimpleTestCase):
    def test_all_required_docs_exist(self):
        for doc_name in REQUIRED_DOCS:
            with self.subTest(doc=doc_name):
                doc_path = DOCS_DIR / doc_name
                self.assertTrue(
                    doc_path.exists(),
                    msg=f"Missing required doc: docs/{doc_name}",
                )

    def test_launch_checklist_contains_critical_sections(self):
        path = DOCS_DIR / "LAUNCH_READINESS_CHECKLIST.md"
        if not path.exists():
            self.skipTest("LAUNCH_READINESS_CHECKLIST.md not found")
        content = path.read_text()
        for section in ["Environment", "Security", "Finance", "Operations", "Monitoring"]:
            with self.subTest(section=section):
                self.assertIn(section, content)
