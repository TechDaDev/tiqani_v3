"""
ASGI config for tiqani_v3 project.

Uses the ProtocolTypeRouter from ``routing.py`` to dispatch HTTP and
WebSocket requests. HTTP requests use Django's standard ASGI handler.
WebSocket requests use Channels consumers with JWT auth.

For more information:
    https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
    https://channels.readthedocs.io/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiqani_v3.settings.dev')

from .routing import application  # noqa: E402
