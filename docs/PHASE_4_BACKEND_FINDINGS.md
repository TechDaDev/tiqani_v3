# Phase 4 Backend Hardening — Findings

## Summary

- **App**: `servicerequest`
- **Model**: `ServiceRequest` (UUID PK)
- **Client relation**: `ForeignKey(ClientProfile)`
- **Technician relation**: `ForeignKey(TechnicianProfile)`
- **Status choices**: PENDING, ACCEPTED, DECLINED, CANCELLED, WITHDRAWN
- **Valid transitions**: PENDING → any terminal state
- **Invalid transitions**: All terminal → any other state → 409 Conflict
- **Total backend tests**: 118 (all passing)

## Hardenings Applied

1. **Serializer `validate_technician`**: Added `user.role == TECHNICIAN` check (previously only checked for `TechnicianProfile` existence)
2. **Self-request prevention**: Added check in `ClientRequestListCreateView.post()` — client cannot request self
3. **All valid transition states tested**: Model-level and API-level

## Tests Created

| File | Tests | Coverage |
|------|-------|----------|
| `test_models.py` | 19 | Default status, string repr, all valid/invalid transitions |
| `test_serializers.py` | 17 | Creation validation, private field exclusion, technician eligibility |
| `test_client_api.py` | 28 | Create, list, detail, cancel, withdraw, IDOR, auth |
| `test_technician_api.py` | 17 | Inbox, detail, accept, decline, IDOR, auth |
| `test_transitions.py` | 16 | All transition paths via API, duplicates |
| `test_permissions.py` | 14 | Cross-client/technician IDOR, role enforcement, anonymous |
| `test_security.py` | 7 | Private field leakage, safe error responses |

## Known Limitations

- No pagination on list endpoints (returns all matching records)
- No throttling enforcement in test settings
- OpenAPI schema has pre-existing 440 errors (unrelated to servicerequest)
