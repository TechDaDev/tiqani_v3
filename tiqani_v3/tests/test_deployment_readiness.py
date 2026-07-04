"""Tests for deployment readiness — settings, health, and file existence."""

import os
from django.test import TestCase, override_settings
from django.urls import reverse


class HealthEndpointTest(TestCase):
    """Health endpoint works correctly."""

    def test_health_returns_200(self):
        resp = self.client.get('/api/health/')
        self.assertEqual(resp.status_code, 200)

    def test_health_returns_expected_keys(self):
        resp = self.client.get('/api/health/')
        data = resp.json()
        self.assertIn('status', data)
        self.assertIn('service', data)
        self.assertIn('database', data)
        self.assertNotIn('debug', data)
        self.assertEqual(data['service'], 'tiqani_v3')


class ProductionSettingsTest(TestCase):
    """Production settings can import when required env vars are set."""

    def test_prod_settings_import_with_env(self):
        """Prod settings should import when required vars are present."""
        with self.settings(DEBUG=False, SECRET_KEY='test-prod-secret'):
            from django.conf import settings
            self.assertFalse(settings.DEBUG)
            self.assertIsNotNone(settings.SECRET_KEY)


class DeploymentFilesExistTest(TestCase):
    """Key deployment files exist in the project."""

    def test_env_production_example_exists(self):
        self.assertTrue(os.path.isfile('.env.production.example'),
                        '.env.production.example should exist')

    def test_env_example_exists(self):
        self.assertTrue(os.path.isfile('.env.example'),
                        '.env.example should exist')

    def test_dockerfile_exists(self):
        self.assertTrue(os.path.isfile('Dockerfile'),
                        'Dockerfile should exist')

    def test_dockerignore_exists(self):
        self.assertTrue(os.path.isfile('.dockerignore'),
                        '.dockerignore should exist')

    def test_docker_compose_exists(self):
        self.assertTrue(os.path.isfile('docker-compose.yml'),
                        'docker-compose.yml should exist')

    def test_docker_compose_prod_exists(self):
        self.assertTrue(os.path.isfile('docker-compose.prod.yml'),
                        'docker-compose.prod.yml should exist')

    def test_entrypoint_exists(self):
        self.assertTrue(os.path.isfile('scripts/entrypoint.sh'),
                        'scripts/entrypoint.sh should exist')

    def test_ci_workflow_exists(self):
        self.assertTrue(os.path.isfile('.github/workflows/ci.yml'),
                        '.github/workflows/ci.yml should exist')

    def test_deployment_docs_exist(self):
        self.assertTrue(os.path.isfile('docs/DEPLOYMENT.md'),
                        'docs/DEPLOYMENT.md should exist')

    def test_production_checklist_exists(self):
        self.assertTrue(os.path.isfile('docs/PRODUCTION_CHECKLIST.md'),
                        'docs/PRODUCTION_CHECKLIST.md should exist')

    def test_api_overview_exists(self):
        self.assertTrue(os.path.isfile('docs/API_OVERVIEW.md'),
                        'docs/API_OVERVIEW.md should exist')

    def test_maintenance_docs_exist(self):
        self.assertTrue(os.path.isfile('docs/MAINTENANCE.md'),
                        'docs/MAINTENANCE.md should exist')

    def test_postman_docs_exist(self):
        self.assertTrue(os.path.isfile('docs/POSTMAN.md'),
                        'docs/POSTMAN.md should exist')

    def test_postman_readme_exists(self):
        self.assertTrue(os.path.isfile('postman/README.md'),
                        'postman/README.md should exist')
