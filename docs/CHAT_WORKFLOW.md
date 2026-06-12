# Chat & Communication Workflow — tiqani_v3

## Overview

Tiqani does **not yet have a real-time chat/messaging system**. This document covers:

1. **Current communication mechanisms** — how clients and technicians communicate today
2. **Planned chat architecture** — how a real-time chat feature should be built using the existing infrastructure
3. **Implementation order** — recommended steps for building chat

---

## 1. Current Communication Mechanisms

Without a dedicated chat system, the platform uses these channels for communication:

### Contract Stage-Based Communication

The primary communication channel is the **contract stage workflow**:

```
Client creates draft contract
        │
        ▼
Technician accepts (or negotiates)
        │
        ▼
In Progress — stage-by-stage delivery
        │
        ├── Technician submits stage (with description + optional attachment)
        │       POST /api/contracts/{id}/stages/{sid}/submit/
        │
        └── Client approves stage
                POST /api/contracts/{id}/stages/{sid}/approve/
                        │
                        ▼
                (funds released from escrow)
```

Each stage submission includes:
- `description` — text describing completed work
- `attachment` — optional file (screenshot, document)
- Status tracking: `pending` → `submitted` → `approved`

**This is not real-time messaging.** It is a structured deliverable workflow.

### Extension Requests

When a contract needs timeline changes:

```
Technician requests extension
        POST /api/contracts/{id}/extension-requests/create/
        │
        ▼
Client approves or rejects
        POST .../extension-requests/{id}/approve/
        POST .../extension-requests/{id}/reject/
```

### System Notifications

Every platform event generates a notification stored in the database and optionally pushed via WebSocket:

| Notification Type | Trigger |
|---|---|
| `contract_created` | Client creates draft contract |
| `contract_accepted` | Technician accepts contract |
| `stage_submitted` | Technician submits a stage |
| `stage_approved` | Client approves a stage |
| `extension_requested` | Technician requests extension |
| `review_created` | Client leaves a review |
| `wallet_transaction` | Financial event |
| `system` | Admin broadcast |

Notifications are:
- Stored in the `Notification` model (`notification/models.py`)
- Viewable via `GET /api/notifications/`
- Pushed in real-time via WebSocket (`ws://<host>:8000/ws/notifications/?token=<token>`)
- Tagged with `target_type` + `target_id` to link to the relevant object

### Reviews

Post-contract, clients can leave reviews with text feedback and ratings. Technicians can respond. This is archival communication, not conversational.

---

## 2. Communication Flow Diagrams

### Current Flow (No Chat)

```
Client                              Technician
  │                                      │
  │── POST /api/contracts/ ──────────────┤  Create draft
  │                                      │
  │── POST .../accept/ ←─────────────────┤  Accept
  │                                      │
  │     Stage 1                           │
  │                                      │── POST .../stages/1/submit/
  │── POST .../stages/1/approve/ ────────┤
  │                                      │
  │     Stage 2                           │
  │                                      │── POST .../stages/2/submit/
  │── POST .../stages/2/approve/ ────────┤
  │                                      │
  │     (Optional extension)              │
  │                                      │── POST .../extension-requests/
  │── POST ...extension/approve/ ────────┤
  │                                      │
  │── POST /api/reviews/ ────────────────┤  Post-contract review
```

### Future Flow (With Chat)

```
Client                              Technician          Chat Server (Channels)
  │                                      │                      │
  │── ws://chat/?token=<jwt> ───────────┼──────────────────────┤  Connect
  │                                      │── ws/chat/ ─────────┤  Connect
  │                                      │                      │
  │── {"type":"message", "text":"..."} ──┼──────────────────────┤  Send msg
  │                                      │                      │── store in DB
  │                                      │                      │── push to recipient
  │                                      │←─ notification ─────┤
  │                                      │←─ {"type":"message"} ┤
  │                                      │                      │
  │── {"type":"typing"} ─────────────────┼──────────────────────┤  Typing indicator
  │── {"type":"read_receipt"} ───────────┼──────────────────────┤  Read receipt
```

---

## 3. Chat Infrastructure — Already Available

The platform already has the necessary infrastructure for chat:

| Component | Status | Details |
|---|---|---|
| **Channels** | ✅ Installed | `channels>=4.1` in requirements |
| **Redis** | ✅ Configured | `channels_redis` as channel layer backend |
| **Daphne** | ✅ Installed | ASGI server with WebSocket support |
| **ASGI Routing** | ✅ Working | `tiqani_v3/routing.py` — ProtocolTypeRouter |
| **JWT Auth Middleware** | ✅ Working | `tiqani_v3/ws_auth.py` — `JWTAuthMiddlewareStack` |
| **Notification Consumer** | ✅ Working | `notification/consumers.py` — proven WebSocket pattern |
| **Docker Compose** | ✅ Configured | Redis + Daphne already in docker-compose |
| **WS URL** | ✅ Documented | `ws://<host>:8000/ws/notifications/?token=<token>` |

---

## 4. Recommended Chat Architecture

### Database Model

Create a new `chat` Django app with:

```python
class Conversation(models.Model):
    """A conversation thread between two or more participants."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL)
    contract = models.ForeignKey(Contract, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    """An individual message within a conversation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
```

### WebSocket Consumer

Extend the Channels pattern already used by `NotificationConsumer`:

```python
class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time chat consumer per conversation.

    Connected users can:
        - Send messages to conversation participants
        - Receive messages in real-time
        - See typing indicators
        - Get read receipts
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user.is_authenticated:
            await self.close(code=4401)
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        # Verify user is participant
        # Add user to conversation group
        await self.channel_layer.group_add(
            f"chat_{self.conversation_id}",
            self.channel_name
        )
        await self.accept()
```

### Routing

```python
# tiqani_v3/routing.py
websocket_urlpatterns = [
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
    re_path(r"ws/chat/(?P<conversation_id>[a-f0-9-]+)/$", ChatConsumer.as_asgi()),
]
```

### REST API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/chat/conversations/` | List user's conversations |
| `POST` | `/api/chat/conversations/` | Create a new conversation |
| `GET` | `/api/chat/conversations/{id}/` | Conversation detail with participants |
| `GET` | `/api/chat/conversations/{id}/messages/` | Paginated message history |
| `POST` | `/api/chat/conversations/{id}/messages/` | Send a message (REST fallback) |
| `POST` | `/api/chat/conversations/{id}/read/` | Mark all as read |
| `GET` | `/api/chat/conversations/{id}/unread-count/` | Unread count for conversation |

### WebSocket Events

**Client → Server:**

| Type | Payload | Description |
|---|---|---|
| `message.send` | `{"text": "..."}` | Send a text message |
| `typing.start` | `{}` | User started typing |
| `typing.stop` | `{}` | User stopped typing |
| `messages.read` | `{"message_ids": [...]}` | Mark messages as read |
| `ping` | `{}` | Keepalive |

**Server → Client:**

| Type | Payload | Description |
|---|---|---|
| `message.new` | `{"id", "sender_id", "text", "created_at"}` | New message delivered |
| `typing` | `{"user_id", "username", "status": "typing"}` | Typing indicator |
| `messages.read` | `{"user_id", "conversation_id"}` | Messages read notification |
| `conversation.updated` | `{"conversation_id", "last_message"}` | Conversation list update |
| `error` | `{"message": "..."}` | Error response |

---

## 5. Integration with Existing Features

### Contract Integration

When a contract is created, a `Conversation` is automatically created between the client and technician:

```python
# In contract creation service
conversation = Conversation.objects.create(contract=contract)
conversation.participants.add(client.user, technician.user)
```

This links the chat thread to the contract, so participants can reference the contract from the chat UI.

### Notification Integration

New chat messages also create a `Notification` record so users get notified via the existing notification system:

```python
# When a message is sent via WebSocket or REST
create_notification(
    recipient=message.conversation.get_other_participant(message.sender),
    notification_type='chat_message',
    title=f"New message from {message.sender.username}",
    message=message.text[:100],
    target_type='conversation',
    target_id=str(message.conversation.id),
)
```

---

## 6. Security Considerations

| Concern | Mitigation |
|---|---|
| **Unauthorized access to conversations** | Verify user is participant before connecting to WebSocket group |
| **Message injection** | Sanitize text on display (frontend responsibility) |
| **File upload abuse** | Limit file types and sizes (same as existing media upload limits) |
| **Rate limiting** | Apply rate limits to message sending (e.g., 30 messages/min) |
| **History access** | REST endpoints require authentication + conversation participant check |
| **WebSocket flood** | Add message rate limiting in the consumer |

---

## 7. Rate Limits (Future)

| Scope | Suggested Rate |
|---|---|
| Message send (WebSocket) | 30 messages/min |
| Message send (REST) | 20 requests/min |
| Conversation creation | 10/hour |
| Typing indicators | 10/min (throttled client-side) |

---

## 8. Known Limitations (Pre-Chat)

These are the limitations of the current communication system:

- **No real-time messaging** — All communication is stage-based and asynchronous
- **No conversational UI** — No chat interface, no message history in conversation format
- **No typing indicators** — Users cannot see when the other party is composing
- **No read receipts** — No way to know if the other party has seen a notification
- **No media sharing in conversation** — Attachments are limited to contract stages
- **No group conversations** — Only one-to-one contract relationships
- **No chat persistence** — Stage descriptions are not designed as a searchable message log

---

## 9. Recommended Implementation Order

| Step | Task | Dependencies |
|---|---|---|
| 1 | Create `chat` Django app with Conversation + Message models | None |
| 2 | Create chat migration and register in admin | Step 1 |
| 3 | Create REST endpoints (conversations CRUD, messages, read status) | Step 1 |
| 4 | Write tests for REST endpoints | Step 3 |
| 5 | Create `ChatConsumer` WebSocket consumer | Step 1 |
| 6 | Add chat URL to `routing.py` | Step 5 |
| 7 | Wire auto-creation of conversation on contract creation | Steps 1, existing contract service |
| 8 | Add notification dispatch on new messages | Steps 5, existing notification service |
| 9 | Add Postman collection for chat endpoints | Steps 3-8 |
| 10 | Document in `docs/FRONTEND_HANDOFF.md` and `docs/CHAT_WORKFLOW.md` | Steps 1-9 |

---

## 10. Conclusion

The current platform relies on **contract stage submissions** and **system notifications** for communication. A real-time chat feature is the most requested improvement (documented in PRDs and known limitations). The infrastructure (Channels, Redis, Daphne, JWT auth) is already in place — what is missing is the chat application layer (models, consumer, REST endpoints).

When implemented, chat should:
- Use the same WS authentication as notifications (`JWTAuthMiddlewareStack`)
- Auto-create conversations when contracts are formed
- Send notifications through the existing notification system
- Store messages in PostgreSQL for persistence and history
- Use Redis channel layer for real-time delivery
