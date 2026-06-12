"""
JWT WebSocket authentication middleware for Django Channels.

Authenticates WebSocket connections using a SimpleJWT access token
passed via the query string (?token=<access_token>).

Usage:
    application = JWTAuthMiddlewareStack(URLRouter(...))
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_str):
    """
    Validate a SimpleJWT access token and return the corresponding user.
    Returns AnonymousUser if token is invalid or user not found.
    """
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(token_str)
        user_id = token.payload.get("user_id")
        if user_id is None:
            logger.warning("WebSocket auth: token missing user_id")
            return AnonymousUser()
        User = get_user_model()
        user = User.objects.get(id=user_id)
        if not user.is_active:
            logger.warning("WebSocket auth: inactive user %s", user_id)
            return AnonymousUser()
        return user
    except Exception as exc:
        logger.debug("WebSocket auth failed: %s", exc)
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Middleware that authenticates WebSocket connections via JWT token
    in the query string.

    Reads the ``token`` query parameter, validates it as a SimpleJWT
    AccessToken, and sets ``scope["user"]`` accordingly.
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_str = params.get("token", [None])[0]

        if token_str:
            scope["user"] = await get_user_from_token(token_str)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Wraps ``JWTAuthMiddleware`` around the standard Channels
    ``AuthMiddlewareStack`` so both cookie-based session auth
    and JWT query-string auth are available.
    """
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
