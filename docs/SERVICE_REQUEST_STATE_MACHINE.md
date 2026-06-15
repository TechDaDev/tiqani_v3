# Service Request State Machine

## Status Values

| Value | Meaning | Set By |
|-------|---------|--------|
| `PENDING` | Awaiting technician action | System (on create) |
| `ACCEPTED` | Technician accepted | Technician |
| `DECLINED` | Technician declined | Technician |
| `CANCELLED` | Client cancelled before action | Client |
| `WITHDRAWN` | Client withdrew before action | Client |

## Valid Transitions

```
                  ┌──────────┐
                  │ PENDING  │
                  └────┬─────┘
              ┌────────┼─────────┐──────────┐
              ▼        ▼         ▼          ▼
          ┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐
          │ACCEPT│ │DECLIN│ │CANCEL │ │WITHDRAW│
          └──────┘ └──────┘ └────────┘ └────────┘
```

All terminal states: `ACCEPTED`, `DECLINED`, `CANCELLED`, `WITHDRAWN`

## Invalid Transitions

Any transition from a terminal state returns `409 Conflict`.

Examples:
- `ACCEPTED → DECLINED` → 409
- `DECLINED → ACCEPTED` → 409
- `CANCELLED → ACCEPTED` → 409
- `WITHDRAWN → ACCEPTED` → 409
- `ACCEPTED → CANCELLED` → 409
- `ACCEPTED → WITHDRAWN` → 409

## Duplicate Transitions

Attempting the same action twice on the same request returns `409 Conflict`.

## Semantic Difference

- **CANCELLED**: Client-initiated termination; implies the client no longer needs the service.
- **WITHDRAWN**: Client-initiated withdrawal; implies the client changed their mind or found another technician.
