# Chat & Communication Workflow — tiqani_v3

## Overview

The chat system enables **pre-contract negotiation** between clients and technicians.
Chat comes **before** contract creation — participants discuss project details, share
files, negotiate pricing, and only create a contract once they reach agreement.

This replaces the previous stage-based communication for pre-contract discussion.

---

## Business Purpose

- Clients browse technician profiles and initiate contact
- Pre-contract discussion of project details, requirements, timeline, and budget
- Technicians send price offers for the client to accept
- Once the price is accepted, a contract can be created and linked to the chat room
- All messages, files, and price offers are preserved as an audit trail

---

## Who Can Start a Chat

- **Only clients** can initiate a chat room with a technician
- Technicians cannot initiate first contact
- One active room per client+technician pair (previous rooms must be closed)

---

## Room Lifecycle

```
OPEN → PROPOSAL_CREATED → CONTRACT_LINKED → CLOSED
  ↓         ↓                                    ↓
BLOCKED   CLOSED                              (terminal)
```

- **OPEN**: Room created, participants can exchange messages
- **PROPOSAL_CREATED**: Technician has sent a price offer
- **CONTRACT_LINKED**: A contract has been linked to the room
- **CLOSED**: Room closed by participant (no new messages)
- **BLOCKED**: Room blocked by admin/moderation

---

## REST API Endpoints

Base path: `/api/chat/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rooms/` | List current user's chat rooms |
| POST | `/rooms/` | Client creates a room with a technician |
| GET | `/rooms/{id}/` | Get room details |
| GET | `/rooms/{id}/messages/` | List messages (paginated) |
| POST | `/rooms/{id}/messages/send/` | Send text message |
| POST | `/rooms/{id}/attachments/` | Upload file attachment |
| POST | `/rooms/{id}/price-offers/` | Technician sends price offer |
| POST | `/rooms/{id}/price-offers/{mid}/accept/` | Client accepts offer |
| POST | `/rooms/{id}/mark-read/` | Mark room as read |
| POST | `/rooms/{id}/close/` | Close room |
| POST | `/rooms/{id}/link-contract/` | Link contract to room |
| GET | `/rooms/unread-summary/` | Get unread counts |

---

## WebSocket Endpoint

```
ws://host/ws/chat/rooms/{room_id}/?token={access_token}
```

### Client-to-Server Messages

```json
{"type": "ping"}
{"type": "chat.message.send", "body": "Hello!"}
{"type": "chat.typing.start"}
{"type": "chat.typing.stop"}
{"type": "chat.read", "message_id": "..."}
{"type": "chat.price_offer.send", "amount": "75000", "currency": "IQD", "description": "..."}
```

### Server-to-Client Events

```json
{"type": "chat.connection.accepted", "room_id": "...", "unread_count": 0}
{"type": "chat.message.created", "payload": {...}}
{"type": "chat.typing", "user_id": "...", "username": "...", "is_typing": true}
{"type": "chat.read", "user_id": "...", "message_id": "..."}
{"type": "chat.price_offer.created", "payload": {...}}
{"type": "chat.price_accepted", "payload": {...}}
{"type": "chat.contract_linked", "room_id": "...", "contract_id": "...", "contract_reference": "..."}
{"type": "chat.room.closed", "room_id": "...", "closed_by_id": "...", "closed_at": "..."}
{"type": "pong"}
{"type": "error", "message": "..."}
```

---

## Message Types

| Type | Description | Requires |
|------|-------------|----------|
| `TEXT` | Plain text message | `body` (non-empty) |
| `FILE` | File attachment | `attachment` uploaded via REST |
| `PRICE_OFFER` | Technician's price quote | `price_amount` |
| `PRICE_ACCEPTED` | Client accepts the offer | System-generated |
| `CONTRACT_LINKED` | Contract linked notification | System-generated |
| `SYSTEM` | System-generated messages | Created by service layer |

---

## Price Offer Workflow

1. Participants discuss project requirements via text messages
2. Technician sends a price offer via `POST /price-offers/` or WebSocket
3. Room status changes to `PROPOSAL_CREATED`
4. Client reviews the offer in context
5. Client accepts the offer via `POST /price-offers/{id}/accept/`
6. A `PRICE_ACCEPTED` message is created with the offer details
7. Client can now create a contract based on the accepted offer
8. Contract is linked to the room via `POST /link-contract/`

---

## Contract Linking

After a contract is created via the existing contract endpoints:

```http
POST /api/chat/rooms/{room_id}/link-contract/
Content-Type: application/json
Authorization: Bearer <token>

{"contract_id": "..."}
```

The system validates:
- Contract client matches room client
- Contract technician matches room technician
- Room is not closed or blocked

On success:
- Room status → `CONTRACT_LINKED`
- `linked_contract` FK set
- `CONTRACT_LINKED` system message created
- Both participants receive notifications

---

## Attachment Workflow

- File uploads use REST multipart endpoint (`POST /attachments/`)
- WebSocket does NOT accept file uploads
- Allowed file types: PDF, JPG, JPEG, PNG
- Max file size: 10MB (uses existing `validate_document_file` validator)
- File URLs use existing private media storage behavior

---

## Notification Integration

Chat events trigger notifications via the existing notification service:

| Event | Recipient | Notification Type |
|-------|-----------|-------------------|
| Room created / first message | Technician | `SYSTEM` |
| New message | Other participant | `SYSTEM` |
| Price offer sent | Client | `CONTRACT_PROPOSAL_SUBMITTED` |
| Price accepted | Technician | `CONTRACT_ACCEPTED` |
| Contract linked | Both | `CONTRACT_CREATED` |

---

## Frontend/Mobile Implementation Guide

### Step 1: Room List
```
GET /api/chat/rooms/
```
Displays rooms with last message preview, unread count, and participant info.

### Step 2: Create Room (Client Only)
```http
POST /api/chat/rooms/
{"technician_id": "...", "initial_message": "I need help with..."}
```

### Step 3: Connect WebSocket
```
ws://host/ws/chat/rooms/{room_id}/?token={access_token}
```
- Listen for `chat.message.created` events for realtime updates
- Send `chat.typing.start`/`chat.typing.stop` for typing indicators
- Send `chat.message.send` for instant message delivery

### Step 4: Handle Messages
- Text messages via WebSocket or REST fallback
- File attachments via REST multipart only
- Price offers via dedicated endpoint or WebSocket

### Step 5: Contract Creation
- After price acceptance, create contract via existing contract API
- Link contract to room via `POST /link-contract/`

---

## Known Limitations

- No group/multi-participant chat (client+technician only)
- No message search/full-text search
- No message editing via API (soft-delete only)
- No message reactions/emoji
- No file preview/thumbnail generation
- No message reporting/flagging
- No auto-closing of stale rooms

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
