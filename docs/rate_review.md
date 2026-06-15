# RateReview App Documentation

Last updated: 2026-02-26

This document reflects the current implementation in `ratereview/`.

## Table of Contents

- [Current Implementation Status](#current-implementation-status)
- [Features](#features)
- [API Availability](#api-availability)
- [Data Model: Review](#data-model-review)
- [Business Logic in Model](#business-logic-in-model)
- [Constraints, Ordering, and Indexes](#constraints-ordering-and-indexes)
- [Admin Panel (ratereviewadminpy)](#admin-panel-ratereviewadminpy)
- [Integration Notes](#integration-notes)
- [Frontend Notes](#frontend-notes)
- [Frontend Implementation Guideline](#frontend-implementation-guideline)

## Current Implementation Status

- `Review` model is fully implemented with validation, moderation fields, and rating recalculation hooks.
- Django Admin for `Review` is implemented with moderation actions.
- `ratereview/views.py` contains no API views yet.
- Project routing (`tiqani_v3/urls.py`) does not currently include a `ratereview` URL module.

## Features

- Rich review model with overall + category-specific rating fields
- Visibility and verification controls (`is_public`, `is_verified`)
- Moderation counters and flagging metadata
- Automatic technician rating refresh on review save
- Admin moderation actions (publish/hide/verify/unverify)
- Contract-linked uniqueness enforcement for reviewer submissions

## API Availability

There are currently **no active RateReview REST endpoints** mounted in this project version.

That means endpoint examples such as creating reviews via public API are not available until URL wiring + DRF views/serializers are added.

---

## Data Model: `Review`

Model location: `ratereview/models.py`

### Core fields
- `id` (UUID primary key)
- `contract` (optional FK to `contract.Contract`, nullable, `SET_NULL`)
- `reviewer` (FK to user, `related_name='reviews_made'`)
- `technician` (FK to `accounts.TechnicianProfile`, `related_name='reviews_received'`)
- `rating` (1..5)

### Detailed rating fields (optional)
- `work_quality_rating` (1..5)
- `communication_rating` (1..5)
- `timeliness_rating` (1..5)
- `professionalism_rating` (1..5)

### Content fields
- `title` (max 150, optional)
- `comment` (optional)
- `technician_response` (optional)

### Moderation/visibility fields
- `is_public` (default `True`)
- `is_verified` (default `False`, auto-true when linked to contract)
- `helpful_count` (default `0`)
- `reported_count` (default `0`)
- `flagged_at` (nullable datetime)

### Timestamps
- `created_at`
- `updated_at`

---

## Business Logic in Model

### `compute_overall_rating()`
- If detailed rating fields are present, `rating` is recalculated as rounded average of provided sub-scores.
- If no sub-scores are provided, falls back to existing `rating`.

### `save()` behavior
- Auto sets `is_verified=True` when `contract` is attached.
- Normalizes `rating` using `compute_overall_rating()`.
- After save, calls `technician.update_rating()` (if available) to refresh technician aggregate score.

### Moderation helper methods
- `publish()` → sets `is_public=True`
- `hide()` → sets `is_public=False`
- `mark_helpful()` → atomic increment of `helpful_count`
- `flag()` → atomic increment of `reported_count` and sets `flagged_at=Now()`

---

## Constraints, Ordering, and Indexes

### Constraint
- Unique review per reviewer+contract when contract is present:
  - `UniqueConstraint(fields=['reviewer', 'contract'], condition=Q(contract__isnull=False), name='unique_reviewer_contract_review')`

### Ordering
- Default ordering: newest first (`-created_at`)

### Indexes
- `(technician, created_at)`
- `rating`
- `is_public`
- `is_verified`
- `(contract, technician)`

---

## Admin Panel (`ratereview/admin.py`)

### Registered model
- `Review` is registered with a custom `ReviewAdmin`.

### Admin features
- List display includes key moderation fields and timestamps.
- Filters for visibility, verification, rating, created/flagged times.
- Search across technician username, reviewer username, title/comment, and contract reference.
- Read-only fields include counters and timestamps.

### Admin actions
- Publish selected reviews
- Hide selected reviews
- Verify selected reviews
- Unverify selected reviews

---

## Integration Notes

- `accounts.TechnicianProfile.update_rating()` is used to maintain technician average score from related reviews.
- `contract.Contract` can be linked to a review for engagement verification and uniqueness enforcement.

---

## Frontend Notes

- Frontend should not depend on public RateReview APIs yet; they are not routed.
- Review data can still exist in DB/admin and may be surfaced indirectly if other serializers expose `reviews_received`.
- To support client-side create/list/update/delete flows, backend still needs:
  1. DRF serializers for `Review`
  2. API views/viewsets in `ratereview/views.py`
  3. URL config (e.g., `ratereview/urls.py`) and inclusion in project routes

---

## Frontend Implementation Guideline

- Gate review UI behind a feature flag until API endpoints are exposed.
- If displaying review-derived ratings, treat them as read-only and source from existing account/technician payloads.
- Avoid hardcoding non-existent endpoints; centralize API paths in one config module.
- Prepare forms/components for future review APIs but keep submit actions disabled in production until backend routing is added.
- Add clear UX messaging: "Review service not yet available" where applicable.
