# Contract Execution API

## Endpoints

### Eligibility & Activation

| Method | Path | Actor | Description |
|--------|------|-------|-------------|
| GET | `/api/contracts/{id}/execution/eligibility/` | Client/Tech | Check execution eligibility |
| POST | `/api/contracts/{id}/activate/` | Client | Activate contract execution |

### Milestones

| Method | Path | Actor | Description |
|--------|------|-------|-------------|
| GET | `/api/contracts/{id}/milestones/` | Client/Tech | List milestones |
| POST | `/api/contracts/{id}/milestones/` | Client | Create draft milestone |
| PATCH | `/api/milestones/{id}/` | Client | Update draft milestone |
| POST | `/api/contracts/{id}/milestones/reorder/` | Client | Reorder milestones |
| POST | `/api/milestones/{id}/start/` | Technician | Start milestone work |

### Deliverables

| Method | Path | Actor | Description |
|--------|------|-------|-------------|
| POST | `/api/milestones/{id}/submit/` | Technician | Submit deliverable |
| GET | `/api/milestones/{id}/submissions/` | Client/Tech | List submissions |

### Revisions & Approval

| Method | Path | Actor | Description |
|--------|------|-------|-------------|
| POST | `/api/milestones/{id}/revision/` | Client | Request revision |
| POST | `/api/milestones/{id}/approve/` | Client | Approve milestone |

### Completion

| Method | Path | Actor | Description |
|--------|------|-------|-------------|
| POST | `/api/contracts/{id}/completion-request/` | Technician | Request contract completion |
| POST | `/api/contracts/{id}/completion-reject/` | Client | Reject completion request |
| POST | `/api/contracts/{id}/complete/` | Client | Confirm completion |

### History

| Method | Path | Actor | Description |
|--------|------|-------|-------------|
| GET | `/api/contracts/{id}/execution-history/` | Client/Tech | Get execution event history |

## Contract States

```
FUNDED → ACTIVE → COMPLETION_REQUESTED → COMPLETED
                       ↓ (reject)
                      ACTIVE
```

## Models Added

- `ExecutionMilestone` — work-tracking milestones (separate from payment stages)
- `DeliverableSubmission` — versioned technician submissions
- `RevisionRequest` — append-only revision history
- `CompletionRequest` — technician completion request with client response

## Security

- All endpoints require authentication
- Client-only: activate, create milestones, approve, request revision, confirm/reject completion
- Technician-only: start milestone, submit deliverable, request completion
- Cross-client/technician access returns 404 (not 403)
- No escrow release
- No wallet credit
