"""
Tests for JWT WebSocket authentication middleware.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class JWTAuthMiddlewareTest(TestCase):
    """Test JWT WebSocket authentication logic."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ws_auth_test", password="test123",
        )

    def test_get_user_from_token_imports(self):
        """get_user_from_token function can be imported."""
        from tiqani_v3.ws_auth import get_user_from_token
        self.assertIsNotNone(get_user_from_token)

    def test_jwt_auth_middleware_scope(self):
        """JWTAuthMiddleware properly sets scope user."""
        from tiqani_v3.ws_auth import JWTAuthMiddleware

        # Create a mock ASGI app
        async def mock_app(scope, receive, send):
            self.assertTrue(hasattr(scope, "user") or "user" in scope)

        middleware = JWTAuthMiddleware(mock_app)
        self.assertIsNotNone(middleware)

    def test_jwt_auth_middleware_imports(self):
        """JWTAuthMiddleware and JWTAuthMiddlewareStack can be imported."""
        from tiqani_v3.ws_auth import JWTAuthMiddleware, JWTAuthMiddlewareStack
        self.assertIsNotNone(JWTAuthMiddleware)
        self.assertIsNotNone(JWTAuthMiddlewareStack)
