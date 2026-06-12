"""Verify Phase 18 documentation files exist."""

import os
from pathlib import Path

from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Phase18DocsExistTests(SimpleTestCase):
    """Verify Phase 18 deliverables exist."""

    def test_chat_workflow_doc_exists(self):
        path = BASE_DIR / "docs" / "CHAT_WORKFLOW.md"
        self.assertTrue(path.exists(), "docs/CHAT_WORKFLOW.md not found")

    def test_postman_collection_exists(self):
        path = BASE_DIR / "postman" / "Tiqani_v3_Phase_18_Chat.postman_collection.json"
        self.assertTrue(path.exists(), "Postman collection not found")

    def test_chat_app_exists(self):
        path = BASE_DIR / "chat" / "__init__.py"
        self.assertTrue(path.exists(), "chat/__init__.py not found")

    def test_chat_models_exist(self):
        path = BASE_DIR / "chat" / "models.py"
        self.assertTrue(path.exists(), "chat/models.py not found")

    def test_chat_services_exist(self):
        path = BASE_DIR / "chat" / "services.py"
        self.assertTrue(path.exists(), "chat/services.py not found")
