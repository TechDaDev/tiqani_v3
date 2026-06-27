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

Final regression proof:
- Backend full suite: 1028 passed.
- Frontend full Playwright suite: 371 passed.
- Integrity proof: 0 duplicate reviews, 0 invalid ratings, 0 self reviews, 0 duplicate notification keys.
- Activity logging restored for shared review moderation path.
- Notification recipient isolation and review/report/moderation IDOR paths passed Playwright coverage.
