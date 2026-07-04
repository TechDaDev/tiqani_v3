# Phase 2 — Backend Integration Report

## Completed

- Profile endpoint validation
- Completion-state correction (`get_missing_fields` → `get_incomplete_fields`)
- Proper tests and regression coverage

---

## Fixed Defect: Completion-Method Mismatch

| File | Before (broken) | After (fixed) |
|------|----------------|---------------|
| `accounts/models.py` | `get_missing_fields()` | Renamed to `get_incomplete_fields()` + backward alias |
| `accounts/client_views.py:93` | Called `profile.get_incomplete_fields()` | Works (method now exists) |
| `accounts/technician_serializers.py:62` | Called `obj.get_incomplete_fields()` | Works (method now exists) |

**Root cause:** `BaseProfile` defined the method as `get_missing_fields()`, but both callers used `get_incomplete_fields()`. This caused an `AttributeError` at runtime.

---

## Endpoint Map

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/auth/profile/incomplete-fields/` | Any auth'd | Returns missing fields + completion % |
| GET | `/api/clients/me/` | Client | Client profile |
| PATCH | `/api/clients/me/` | Client | Update client profile |
| GET | `/api/technicians/me/` | Technician | Technician profile |
| PATCH | `/api/technicians/me/` | Technician | Update technician profile |
| GET | `/api/technicians/me/skills/` | Technician | Get skills |
| PATCH | `/api/technicians/me/skills/` | Technician | Update skills |
| GET | `/api/technicians/list/` | Public | List technicians |

---

## Response Contracts

### Incomplete Fields (`GET /api/auth/profile/incomplete-fields/`)
```json
{
  "is_complete": false,
  "incomplete_fields": ["phone_number", "governorate", "address", "gender", "date_of_birth"],
  "total_required": 5,
  "completed_count": 0,
  "completion_percentage": 0.0
}
```

### Client Profile (`GET /api/clients/me/`)
Uses `ClientProfileSerializer` — returns full profile object.

### Technician Profile (`GET /api/technicians/me/`)
Uses `TechnicianProfileSerializer` — returns full profile object.

### Error Response Shape
```json
{
  "detail": "Error message"
}
```
or field errors:
```json
{
  "field_name": ["Error message"]
}
```

---

## Completion Contract

The backend returns:
- `is_complete` (bool): Whether all required fields are filled
- `incomplete_fields` (list): Field names still missing
- `total_required` (int): Total required field count
- `completed_count` (int): Fields filled
- `completion_percentage` (float): 0–100

### Client Required Fields
`phone_number`, `governorate`, `address`, `gender`, `date_of_birth`

### Technician Required Fields
`phone_number`, `governorate`, `address`, `gender`, `date_of_birth`, `profile_image`, plus
`job_title`, `about`, `years_of_expertise`, `identification_documents`

---

## Onboarding

No dedicated onboarding endpoint exists. Onboarding state is derived from:
- `profile.is_complete` (all required fields filled)
- `technician.approved` (admin approval)

---

## Upload

Profile image upload is handled through the normal `PATCH /api/clients/me/` or `PATCH /api/technicians/me/` endpoints with a `profile_image` field using `multipart/form-data`. The returned URL is an absolute path built by the serializer.

---

## Role Permissions

| Endpoint | Anonymous | Client | Technician | Admin |
|----------|-----------|--------|------------|-------|
| `/api/auth/profile/incomplete-fields/` | 401 | 200 | 200 | 200 |
| `/api/clients/me/` | 401 | 200 | 403 | — |
| `/api/technicians/me/` | 401 | 403 | 200 | — |
| `/api/technicians/me/skills/` | 401 | 403 | 200 | — |
| `/api/technicians/list/` | 200 | 200 | 200 | 200 |

---

## Tests Added

- `IncompleteFieldsTest` (6 tests) in `test_client_api.py`
- Technician profile/skills/completion tests (5 tests) in `test_technician_api.py`
