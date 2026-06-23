# Dispute State Machine

## Status Transitions

```
OPEN → AWAITING_RESPONSE
AWAITING_RESPONSE → UNDER_REVIEW
OPEN → UNDER_REVIEW
UNDER_REVIEW → MEDIATION
MEDIATION → RESOLUTION_PROPOSED
UNDER_REVIEW → RESOLUTION_PROPOSED
RESOLUTION_PROPOSED → RESOLVED
RESOLVED → CLOSED
OPEN → CANCELED
AWAITING_RESPONSE → CANCELED
UNDER_REVIEW → REJECTED
REJECTED → CLOSED
```

## Transition Rules
- Every transition goes through `dispute/services.py`
- Validates actor permission and previous state
- Appends immutable `DisputeAuditEvent`
- Sends notification to relevant participants

## Trigger Points
| Transition | Service Method | Allowed Actor |
|---|---|---|
| OPEN | `open_dispute()` | Client or Technician |
| AWAITING_RESPONSE | `add_dispute_statement()` | Respondent |
| UNDER_REVIEW | `start_review()` | Staff |
| MEDIATION | `start_mediation()` | Staff |
| RESOLUTION_PROPOSED | `propose_resolution()` | Staff |
| RESOLVED | `resolve_dispute()` | Staff |
| REJECTED | `reject_dispute()` | Staff |
| CLOSED | `close_dispute()` | Staff |
| CANCELED | `cancel_dispute()` | Original opener only |
