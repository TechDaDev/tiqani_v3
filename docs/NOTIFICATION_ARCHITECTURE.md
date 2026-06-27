# Notification Architecture

Phase 11 reuses the existing `notification` app.

Models:
- `Notification`
- `NotificationPreference`
- `ActivityLog`

Delivery:
- In-app REST notification center is primary.
- Existing websocket helpers remain best-effort.
- Production email, SMS, and push providers are deferred.

Deduplication:
- `Notification.deduplication_key` is unique when set.
- `create_notification_once` returns the existing record for repeat event delivery.

Privacy:
- Notifications should use safe target metadata.
- No private email, phone, provider token, internal wallet id, or secret should be placed in payloads.
- User notification endpoints enforce recipient ownership.

Final regression verified:
- 126 seeded notifications.
- 0 duplicate deduplication keys.
- `create_notification_once` returns one event record for repeat delivery.
- Unread and read fixture notifications remain distinct.
- Client review notification preference is enabled.
- Owner-B notification fixture is isolated from the primary client.

Local Redis was unavailable during final validation. Realtime delivery logged non-fatal warnings; REST notification center, read state, unread count, and preferences passed regression.
