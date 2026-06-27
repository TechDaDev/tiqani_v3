# Phase 11 Security

Protected invariants:
- Only contract participants can create reviews.
- Reviewer/reviewee are derived by backend contract participation.
- Users cannot review themselves.
- Unresolved disputes block reviews.
- Duplicate review creation is idempotent.
- Hidden reviews are excluded from public list/detail.
- Moderation requires staff/content moderator permissions.
- Notification list/detail/read state is recipient-isolated.
- Notification dedupe prevents duplicate event spam.

Known deferred work:
- Full production email/SMS/push provider integration.
- ML fraud scoring.
- Advanced trust scoring.
- Large admin redesign.
