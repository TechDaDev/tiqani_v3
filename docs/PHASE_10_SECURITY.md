# Phase 10 Security

## Permission Matrix
| Action | Client | Technician | Staff |
|---|---|---|---|
| Open dispute | Own contract only | Own contract only | No |
| Add statement | Own dispute | Own dispute | No |
| Add evidence | Own dispute | Own dispute | No |
| Cancel dispute | Own dispute only | Own dispute only | No |
| View dispute | Own dispute | Own dispute | All |
| Assign staff | No | No | Yes |
| Start review | No | No | Yes |
| Mediation | No | No | Yes |
| Propose resolution | No | No | Yes |
| Resolve | No | No | Yes |
| Reject | No | No | Yes |
| Close | No | No | Yes |
| Create refund | No | No | Yes |
| Create chargeback | No | No | Yes |

## IDOR Protection
- `_get_dispute()` checks participant or staff status
- `_get_contract()` checks participant or staff status
- Invalid UUIDs return 404
- Deleted contracts are inaccessible

## Amount Validation
- Claimed amount cannot exceed contract agreed amount
- Refund amount validated against escrow/wallet holdings
- All amounts backend-derived or backend-validated

## Private Data
- No wallet IDs exposed in dispute responses
- No provider references exposed to participants
- No internal notes exposed
- Evidence metadata does not include file paths
