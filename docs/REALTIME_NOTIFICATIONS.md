# Realtime Notifications — WebSocket API

## Overview

Realtime notifications use **Django Channels** with **Redis** as the channel layer backend. Authenticated users receive notification events via a persistent WebSocket connection.

## WebSocket URL

```
ws://<host>:8000/ws/notifications/?token=<access_token>
```

### Connection Authentication

WebSocket connections are authenticated via a **SimpleJWT access token** passed as a query string parameter:

```
ws://127.0.0.1:8000/ws/notifications/?token=eyJhbGciOiJIUzI1NiIs...
```

**Rules:**
- Only access tokens (not refresh tokens) are accepted.
- Expired or invalid tokens are rejected with code `4401`.
- Tokens are never logged.

### Getting an Access Token

```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

Response:
```json
{
    "access": "eyJhbGciOiJIUzI1NiIs...",
    "refresh": "..."
}
```

Use the `access` value as the `token` query parameter.

## Initial Payload

On successful connection, the server sends:

```json
{
    "type": "connection.accepted",
    "unread_count": 3,
    "message": "Connected to realtime notifications."
}
```

## Client → Server Messages

### Ping

Keep the connection alive:

```json
{"type": "ping"}
```

Response:
```json
{"type": "pong"}
```

### Get Unread Count

Request current unread count:

```json
{"type": "get.unread_count"}
```

Response:
```json
{"type": "notification.unread_count", "unread_count": 3}
```

## Server → Client Events

### Notification Created

```json
{
    "type": "notification.created",
    "payload": {
        "id": "uuid-string",
        "type": "contract_created",
        "title": "New contract request",
        "message": "A new contract has been created.",
        "is_read": false,
        "created_at": "2026-06-12T12:00:00+00:00",
        "target_type": "contract",
        "target_id": "uuid-string",
        "target_url": "/contracts/...",
        "actor_name": "John Doe"
    }
}
```

### Unread Count Update

```json
{"type": "notification.unread_count", "unread_count": 5}
```

### Notification Marked Read

```json
{"type": "notification.marked_read", "notification_id": "uuid-string"}
```

### Notification Marked Unread

```json
{"type": "notification.marked_unread", "notification_id": "uuid-string"}
```

### All Notifications Read

```json
{"type": "notification.bulk_read", "updated": 12}
```

### Dealership Alert

```json
{
    "type": "dealership.alert",
    "payload": {
        "alert_type": "threshold_warning",
        "message": "Dealership is approaching credit limit."
    }
}
```

## Reconnection Strategy

- Expect the connection to drop periodically.
- Reconnect immediately with the same token.
- If the token expires during a long session, obtain a new one via `/api/auth/login/` or `/api/auth/token/refresh/`.

## Mobile Considerations

- Mobile WebSocket clients can use the same `ws://` or `wss://` URL with the `?token=` parameter.
- For React Native: use the built-in `WebSocket` API.
- For Flutter: use the `web_socket_channel` package with query parameters.
- Tokens can be refreshed without reconnecting the WebSocket by obtaining a new token on the client side.

## Security Rules

1. **Authentication required** — Anonymous connections are rejected.
2. **Per-user isolation** — A user only receives events for their own notifications and alerts.
3. **Token validation** — Only valid, non-expired SimpleJWT access tokens.
4. **No token logging** — Tokens are never written to logs.
5. **No refresh tokens** — Only access tokens are accepted for WebSocket auth.

## Production Redis / Channel Layer Setup

In production, ensure `CHANNEL_LAYERS_REDIS_URL` points to a managed Redis instance. For high-availability setups, use Redis Sentinel or Redis Cluster hosts.

```env
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer
CHANNEL_LAYERS_REDIS_URL=redis://:password@redis-host:6379/2
```

## Testing with websocat

```bash
# Install websocat: https://github.com/vi/websocat
# 1. Get a token
TOKEN=$(curl -s http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['access'])")

# 2. Connect
websocat "ws://127.0.0.1:8000/ws/notifications/?token=$TOKEN"
```

## Testing with Python

```python
import asyncio
import json
import websockets

async def test():
    token = "your_access_token_here"
    uri = f"ws://127.0.0.1:8000/ws/notifications/?token={token}"

    async with websockets.connect(uri) as ws:
        # Receive initial payload
        initial = json.loads(await ws.recv())
        print("Connected:", initial["unread_count"])

        # Ping
        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await ws.recv())
        print("Pong:", pong)

asyncio.run(test())
```

## Known Limitations

- WebSocket connections are tied to a single server process in production. Use Redis channel layers and sticky sessions (or a single process) for multi-worker setups.
- Daphne or Uvicorn is required for WebSocket support (Gunicorn WSGI does not support WebSocket).
- `manage.py runserver` works for local development with Channels.
- The channel layer does not persist messages — if no client is connected when an event fires, the event is lost.
- For guaranteed delivery, combine WebSocket notifications with polling or use the REST notification API as a fallback.

## Docker / Production

For production, the Docker Compose `web` service uses **Daphne** as the ASGI server:

```bash
daphne -b 0.0.0.0 -p 8000 tiqani_v3.asgi:application
```

For HTTP-only deployments without WebSocket requirements, Gunicorn with the WSGI application can be used instead.
