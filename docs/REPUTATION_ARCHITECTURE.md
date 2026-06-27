# Reputation Architecture

Reputation is backend-calculated by `ratereview.services.recalculate_user_reputation`.

Formula:
- `average_rating = sum(rating values) / visible verified review count`
- Hidden, removed, unverified, and under-review reviews are excluded.
- Distribution counts published verified reviews by exact rating from 1 to 5.
- Completed-contract count comes from backend contract records.

Labels:
- `new`: fewer than 3 published verified reviews.
- `established`: at least 3 published verified reviews.
- `highly_rated`: at least 5 published verified reviews and average rating >= 4.50.

Labels are trust indicators only. They do not imply legal identity verification, professional licensing, or external certification.
