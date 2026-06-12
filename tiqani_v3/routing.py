"""
ASGI routing — HTTP + WebSocket URL dispatch.

WebSocket paths are routed to consumers via URLRouter.
HTTP requests fall through to the standard Django ASGI handler.
"""

from django.core.asgi import get_asgi_application
from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter

from tiqani_v3.ws_auth import JWTAuthMiddlewareStack
from notification.consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
