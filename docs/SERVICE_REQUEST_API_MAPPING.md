# Service Request API — Endpoint Mapping

## Base URLs

| Scope | Base URL |
|-------|----------|
| Client | `/api/requests/` |
| Technician | `/api/technician/requests/` |

## Client Endpoints

| Method | Path | Action | Auth | Role |
|--------|------|--------|------|------|
| GET | `/api/requests/` | List own requests | JWT | client |
| POST | `/api/requests/` | Create request | JWT | client |
| GET | `/api/requests/{id}/` | Detail own request | JWT | client |
| POST | `/api/requests/{id}/cancel/` | Cancel pending request | JWT | client |
| POST | `/api/requests/{id}/withdraw/` | Withdraw pending request | JWT | client |

## Technician Endpoints

| Method | Path | Action | Auth | Role |
|--------|------|--------|------|------|
| GET | `/api/technician/requests/` | List assigned requests | JWT | technician |
| GET | `/api/technician/requests/{id}/` | Detail assigned request | JWT | technician |
| POST | `/api/technician/requests/{id}/accept/` | Accept pending request | JWT | technician |
| POST | `/api/technician/requests/{id}/decline/` | Decline pending request | JWT | technician |

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success (list, detail, action) |
| 201 | Created |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Wrong role |
| 404 | Request not found |
| 409 | Invalid state transition |
