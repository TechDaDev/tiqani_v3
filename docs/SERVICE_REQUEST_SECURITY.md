# Service Request Security

## Authentication

All request endpoints require JWT authentication via HTTP-only cookies (`tiqani_access`). Anonymous requests return `401 Unauthorized`.

## Role Authorization

| Endpoint Group | Allowed Role | Unauthorized Response |
|---------------|--------------|----------------------|
| Client endpoints | `client` | `403 Forbidden` |
| Technician endpoints | `technician` | `403 Forbidden` |

## Object-Level Authorization (IDOR Protection)

All endpoints scope queries to the authenticated user:

- **Client endpoints**: Filtered by `client__user=request.user`
- **Technician endpoints**: Filtered by `technician__user=request.user`

Cross-owner access returns `404 Not Found` (not `403`) to prevent existence enumeration.

## Self-Request Prevention

Clients cannot send a request to their own user UUID. Returns `400 Bad Request`.

## Technician Eligibility Validation

Request creation validates:
1. User UUID exists
2. User role is `technician`
3. `TechnicianProfile` exists
4. `approved == True`
5. `is_available == True`

Invalid cases return `400 Bad Request` with descriptive messages.

## Private Field Protection

The following fields are excluded from all API responses:

- `email` (client and technician summaries)
- `phone_number` (client and technician summaries)
- `password`
- `identification_documents`
- `is_superuser`
- `is_staff`
- `last_login`
- `date_joined`
- `user_permissions`
- `groups`

## Cookies

- JWT tokens use HTTP-only cookies
- `tiqani_access`: short-lived access token
- `tiqani_refresh`: refresh token
- No tokens exposed to client-side JavaScript

## Cache Control

Request detail responses should include `Cache-Control: no-store` to prevent sensitive data caching.
