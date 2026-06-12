"""Tests for OpenAPI schema and API docs endpoints (Phase 16)."""

from django.test import TestCase, override_settings


@override_settings(ALLOWED_HOSTS=["testserver", "*"])
class SchemaDocsTests(TestCase):
    """Verify /api/schema/, /api/docs/, /api/redoc/ endpoints."""

    def test_schema_endpoint_returns_200(self):
        resp = self.client.get("/api/schema/")
        self.assertEqual(resp.status_code, 200)

    def test_schema_contains_title_and_version(self):
        resp = self.client.get("/api/schema/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"info", resp.content)
        self.assertIn(b"Tiqani API", resp.content)
        self.assertIn(b"16.0.0", resp.content)

    def test_swagger_docs_endpoint_returns_200(self):
        resp = self.client.get("/api/docs/")
        self.assertEqual(resp.status_code, 200)

    def test_redoc_endpoint_returns_200(self):
        resp = self.client.get("/api/redoc/")
        self.assertEqual(resp.status_code, 200)
