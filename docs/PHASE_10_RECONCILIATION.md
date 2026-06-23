# Phase 10 Reconciliation

Per disputed contract, the reconciliation extends Phase 9 to return:
- funded_total, principal, escrow original
- original settlement amounts
- recovered technician amount
- refunded client amount
- reversed platform fees
- remaining escrow
- outstanding liability
- chargeback exposure
- refund status
- dispute status
- reconciliation status

## Reconciliation Statuses
| Status | Meaning |
|---|---|
| BALANCED | All financial records match |
| DISPUTED | Active dispute exists |
| REFUND_PENDING | Refund in progress |
| PARTIALLY_RECOVERED | Only partial recovery achieved |
| MANUAL_RECOVERY_REQUIRED | Outstanding liability exists |
| MISMATCH | Discrepancy found |
| CLOSED_BALANCED | Dispute closed, financials match |

## Service
`get_dispute_reconciliation()` returns structured data for a dispute.
