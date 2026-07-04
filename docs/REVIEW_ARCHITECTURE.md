# Review Architecture

Reviews live in `ratereview.Review`.

Phase 11 extends the existing model with:
- `reviewee`
- `reviewer_role`
- `status`
- `edit_count`
- `last_edited_at`
- moderation history through `ReviewModerationAction`

`technician` remains nullable and is used only when the reviewed user is a technician. This prevents technician-to-client reviews from affecting technician public rating or technician public review lists.

## Service Layer

Core operations:
- `get_review_eligibility`
- `create_contract_review`
- `update_contract_review`
- `moderate_review`
- `restore_review`
- `recalculate_user_reputation`

Business rules live in services, not frontend code.

## Moderation

Reviews are not destructively deleted for Phase 11. Staff hide/restore actions preserve:
- original review content;
- actor;
- reason;
- timestamp.

Moderation also emits an admin activity record:
- event: `review_moderated`
- target type: `review`
- metadata: moderation action and reason

Final regression verified participant eligibility, duplicate idempotency, hidden review exclusion, report creation, moderation content preservation, and activity logging.
