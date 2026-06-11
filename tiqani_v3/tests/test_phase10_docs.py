"""Tests for Phase 10 documentation and files."""

import os
from django.test import TestCase


class Phase10FilesExistTest(TestCase):

    def test_frontend_handoff_doc_exists(self):
        self.assertTrue(os.path.isfile('docs/FRONTEND_HANDOFF.md'),
                        'docs/FRONTEND_HANDOFF.md should exist')

    def test_qa_checklist_exists(self):
        self.assertTrue(os.path.isfile('docs/QA_CHECKLIST.md'),
                        'docs/QA_CHECKLIST.md should exist')

    def test_release_notes_exists(self):
        self.assertTrue(os.path.isfile('docs/RELEASE_NOTES_PHASE_1_TO_10.md'),
                        'docs/RELEASE_NOTES_PHASE_1_TO_10.md should exist')

    def test_complete_postman_collection_exists(self):
        self.assertTrue(os.path.isfile('postman/Tiqani_v3_Complete_Backend.postman_collection.json'),
                        'Complete Postman collection should exist')

    def test_seed_demo_data_command_exists(self):
        self.assertTrue(os.path.isfile('accounts/management/commands/seed_demo_data.py'),
                        'seed_demo_data command should exist')

    def test_final_backend_qa_command_exists(self):
        self.assertTrue(os.path.isfile('accounts/management/commands/final_backend_qa.py'),
                        'final_backend_qa command should exist')

    def test_export_api_routes_command_exists(self):
        self.assertTrue(os.path.isfile('accounts/management/commands/export_api_routes.py'),
                        'export_api_routes command should exist')

    def test_readme_references_frontend_handoff(self):
        readme_path = 'README.md'
        self.assertTrue(os.path.isfile(readme_path))
        with open(readme_path) as f:
            content = f.read()
        self.assertIn('FRONTEND_HANDOFF', content,
                      'README should reference FRONTEND_HANDOFF')
