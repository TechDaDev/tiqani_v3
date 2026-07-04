# Phase 7 Frontend Handoff

## Routes

- `/contracts/{id}/fund` — Client funding page
- `/contracts/{id}` — Contract detail with funding status integration

## Proxies

4 proxy routes map browser requests to Django wallet endpoints.

## Components

- `PaymentStatusBadge` — Color-coded funding badge
- `FundingSummary` — Funding details card
- `FundingAction` — Start funding button with loading state

## State

Funding state derived from backend `ContractFundingStatus` response.
No optimistic frontend funding.
