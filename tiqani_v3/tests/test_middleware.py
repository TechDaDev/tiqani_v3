"""Tests for RequestIDMiddleware (Phase 15)."""

from django.test import TestCase, RequestFactory
from django.http import HttpResponse

from tiqani_v3.middleware import RequestIDMiddleware


def _dummy_view(request):
    return HttpResponse("ok")


class RequestIDMiddlewareTests(TestCase):
    def setUp(self):
        self.mw = RequestIDMiddleware(_dummy_view)
        self.factory = RequestFactory()

    def test_sets_request_id_on_response_header(self):
        request = self.factory.get("/api/health/")
        response = self.mw(request)
        self.assertIn("X-Request-ID", response)
        self.assertTrue(len(response["X-Request-ID"]) == 8)

    def test_request_id_is_unique(self):
        request1 = self.factory.get("/")
        request2 = self.factory.get("/")
        resp1 = self.mw(request1)
        resp2 = self.mw(request2)
        self.assertNotEqual(resp1["X-Request-ID"], resp2["X-Request-ID"])

    def test_respects_incoming_x_request_id(self):
        request = self.factory.get("/", HTTP_X_REQUEST_ID="client-id-123")
        response = self.mw(request)
        self.assertEqual(response["X-Request-ID"], "client-id-123")
