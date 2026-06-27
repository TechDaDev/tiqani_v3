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
