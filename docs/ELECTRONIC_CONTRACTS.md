# Electronic Contracts — Phase 19

## Overview

Phase 19 introduces a complete electronic contract signing, finalization, and public
verification system. Contracts signed through Tiqani produce immutable snapshots,
OTP-verified digital signatures, a signed PDF, and a platform attestation with a
public verification code.

## Lifecycle

```
draft
  → (technician completes proposal)
  → pending_acceptance
  → (both parties accept the business terms)
  → pending_signatures
  → (both parties sign the same frozen version via OTP)
  → pending_finalization
  → (authorized user triggers finalization)
  → in_progress
  → (stages completed and approved)
  → completed
```

**Key rule:** The contract never moves to `in_progress` merely because acceptance
flags are true. Escrow and platform fees are charged **only during finalization**.

## Frontend Signing Sequence

1. **Acceptance** — Client and technician each POST to `/api/contracts/{id}/accept/`.
2. **Freeze** (optional) — Either party POSTs to `/api/contracts/{id}/freeze/`.
3. **Request OTP** — Each party POSTs to `/api/contracts/{id}/request-signature-otp/`.
   An email with a 6-digit code is sent.
4. **Sign** — Each party POSTs to `/api/contracts/{id}/sign/` with the OTP code.
   The server derives the signer role from the authenticated user.
5. **Poll signatures** — GET `/api/contracts/{id}/signatures/` to check both parties.
6. **Finalize** — Either party (or admin) POSTs to `/api/contracts/{id}/finalize/`.
   Generates PDF, attestation, activates escrow, notifies both parties.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/contracts/{id}/freeze/` | JWT | Freeze immutable snapshot |
| POST | `/api/contracts/{id}/request-signature-otp/` | JWT | Send signing OTP |
| POST | `/api/contracts/{id}/sign/` | JWT | Submit OTP to sign |
| GET | `/api/contracts/{id}/signatures/` | JWT | List signature records |
| POST | `/api/contracts/{id}/finalize/` | JWT | Finalize signed contract |
| GET | `/api/contracts/{id}/documents/` | JWT | List document metadata |
| GET | `/api/contracts/{id}/documents/final/` | JWT | Download signed PDF |
| GET | `/api/contracts/verify/{code}/` | None | Public verification |
| POST | `/api/contracts/verify-pdf/` | None | Verify uploaded PDF |

## OTP Flow

- OTP is generated via `accounts.models.OTPVerification.generate_otp()`.
- Sent to the user's registered email via `accounts.email_utils.send_otp_email()`.
- Default validity: 600 seconds (configurable via `OTP_VALIDITY_SECONDS`).
- Default max attempts: 3 (configurable via `OTP_MAX_ATTEMPTS`).
- OTP is marked `is_used = True` after successful signing.
- The signer role (`client` or `technician`) is derived **server-side** from the
  authenticated user, never accepted from the client request.

## Signature Evidence

Each `ContractSignature` record stores:

- `signature_hash` — SHA-256 of `{contract_id}:{version_id}:{role}:{otp_verification_id}:{timestamp}`
- `signed_at` — server timestamp
- `ip_address` — client IP at signing time
- `user_agent` — client user agent at signing time
- `otp_verification` — FK to the OTP used (does not expose raw OTP code)

Signatures are immutable after creation. They cannot be deleted or modified.

## Immutable Versions

`ContractVersion` records are created by `get_or_create_frozen_version()` which:

1. Builds a canonical JSON snapshot of the contract state.
2. Computes SHA-256 of the canonical JSON.
3. Stores both the snapshot and hash.
4. Versions are immutable (`is_frozen = True`).

A new version is created if any contract field changes. Signatures are bound to
a specific version, not to the mutable contract record.

## PDF Sections

The generated PDF (via ReportLab, see `contract/pdf_utils.py`) includes:

1. **Header** — Tiqani branding, title, contract reference, version, status, dates
2. **Parties** — Client and technician legal names, platform IDs, masked contacts, verification status
3. **Project Details** — Title, description, location, accepted offer reference
4. **Financial Summary** — Agreed amount, fees, escrow, total funding required
5. **Timeline** — Start date, duration, deadline, extension policy
6. **Stages** — Numbered stages with amounts, deadlines, release conditions
7. **Obligations** — Client, technician, and platform obligations
8. **Digital Signatures** — Role, name, signature ID, method, timestamp
9. **Platform Attestation** — Attestation text, hash, legal name, seal method, verification URL
10. **QR Code** — Links to public verification endpoint
11. **Footer** — Electronic document statement, governing law, support notice

## Download Flow

- The final PDF is stored as a private `FileField` on `ContractDocument`.
- Participants and admin can list/download via the `/documents/` endpoints.
- Anonymous users cannot access the PDF directly.
- Public verification returns metadata only (not the PDF).

## Verification Flow

### By verification code (GET, unauthenticated)

```
GET /api/contracts/verify/ABC123XYZ456/

Response:
{
  "valid": true,
  "contract_reference": "TIQ-2026-00042",
  "version": 1,
  "status": "in_progress",
  "document_type": "FINAL_SIGNED_PDF",
  "finalized_at": "2026-06-14T12:00:00+00:00",
  "client_signature_verified": true,
  "technician_signature_verified": true,
  "platform_attestation_verified": true,
  "document_hash": "abc...123",
  "attestation_id": "ABC123XYZ456"
}
```

### By uploaded PDF (POST, unauthenticated)

Upload the PDF. The server computes SHA-256 and matches it against stored hashes.
The uploaded file is **not stored permanently**.

## Status Polling

Frontend should poll `GET /api/contracts/{id}/` after each action and check
the `status` field. After finalization, status becomes `in_progress`.

## Failure Recovery

- **OTP expired:** User re-requests OTP via `/request-signature-otp/`.
- **PDF generation failure:** Contract remains `pending_finalization`. No wallet charge.
- **Storage failure:** No wallet charge. Manual intervention needed.
- **Wallet failure:** Contract stays `pending_finalization`. Notify support.
- **Retry safety:** Finalization is idempotent. Duplicate calls do not duplicate PDFs,
  escrow, fees, payment intents, or audit events.

## Legal Review Disclaimer

The platform attestation states:

> *This electronic attestation records transaction and document-integrity evidence.
> It does not represent governmental notarization unless explicitly established
> under applicable law.*

Users should consult local legal counsel regarding the legal validity of electronic
signatures and contract formation in their jurisdiction.

## Arabic/RTL Status

The current PDF template uses Latin fonts (Helvetica). Arabic/RTL text rendering
is not yet supported. A future upgrade may add:

- ReportLab's `arabic_reshaper` and `bidi.algorithm` for Arabic text
- A custom TrueType font with Arabic glyphs (e.g., Noto Naskh Arabic, open-licensed)
- RTL-aware table layout adjustments

## Platform Attestation Limitations

- The attestation is a SHA-256 fingerprint, not a cryptographic signature from a
  recognized certificate authority.
- It provides integrity evidence but does not constitute notarization.
- The platform registration number is configurable via settings.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `CONTRACT_PUBLIC_VERIFY_BASE_URL` | `http://localhost:8000` | Base URL for QR verification links |
| `CONTRACT_PLATFORM_REGISTRATION` | `""` | Platform legal registration number |
| `CONTRACT_PDF_MAX_UPLOAD_MB` | `10` | Max uploaded verification PDF size |
