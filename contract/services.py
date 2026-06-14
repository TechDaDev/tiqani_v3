"""Business logic layer for contract lifecycle operations."""

import hashlib
import json
import logging
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    Contract,
    ContractStage,
    ContractVersion,
    ContractSignature,
    ContractDocument,
    PlatformAttestation,
    ContractAuditEvent,
    TimeExtensionRequest,
)
from .pdf_utils import generate_signed_contract_pdf
from wallet.models import WalletTransaction

logger = logging.getLogger(__name__)


def _audit(contract, event_type, actor=None, payload=None):
    """Append contract audit event."""
    ContractAuditEvent.objects.create(
        contract=contract,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )


def _latest_frozen_version(contract):
    return contract.versions.filter(is_frozen=True).order_by('-version_number').first()


def freeze_contract_version(contract, actor):
    """Freeze immutable version before signature workflow."""
    is_participant = (contract.client.user_id == actor.id) or (contract.technician.user_id == actor.id)
    if not (is_participant or actor.is_staff):
        raise PermissionError("Only participants or admin can freeze contract versions.")
    if contract.status not in ('pending_signatures', 'pending_finalization'):
        raise ValueError("Contract must be pending_signatures or pending_finalization to freeze.")

    version, created = contract.get_or_create_frozen_version(actor=actor)
    if created:
        _audit(contract, 'contract_version_frozen', actor=actor, payload={'version_number': version.version_number})
    return version


def request_signature_otp(contract, user):
    """Issue OTP for signature action and send by email."""
    is_client = contract.client.user_id == user.id
    is_technician = contract.technician.user_id == user.id
    if not (is_client or is_technician):
        raise PermissionError("Only contract participants can request signature OTP.")
    if contract.status not in ('pending_signatures', 'pending_finalization'):
        raise ValueError("Contract is not in a signable state.")

    freeze_contract_version(contract, user)

    from accounts.models import OTPVerification
    from accounts.email_utils import send_otp_email

    otp = OTPVerification.generate_otp(user)
    if not send_otp_email(user, otp.otp_code, otp.verification_id):
        raise ValueError("Failed to send OTP email.")

    role = 'client' if is_client else 'technician'
    _audit(contract, 'signature_otp_requested', actor=user, payload={'role': role, 'verification_id': otp.verification_id})
    return otp


@transaction.atomic
def sign_contract_version(contract, user, otp_code, ip_address='', user_agent=''):
    """Create signer proof for frozen version using OTP."""
    is_client = contract.client.user_id == user.id
    is_technician = contract.technician.user_id == user.id
    if not (is_client or is_technician):
        raise PermissionError("Only contract participants can sign.")
    if contract.status not in ('pending_signatures', 'pending_finalization'):
        raise ValueError("Contract is not in a signable state.")

    version = freeze_contract_version(contract, user)
    role = 'client' if is_client else 'technician'

    from accounts.models import OTPVerification
    try:
        otp = OTPVerification.objects.get(user=user, otp_code=otp_code, is_used=False)
    except OTPVerification.DoesNotExist:
        raise ValueError("Invalid OTP code.")
    if not otp.is_valid():
        raise ValueError("OTP has expired or is invalid.")

    signature_hash = hashlib.sha256(
        f"{contract.id}:{version.id}:{role}:{otp.verification_id}:{otp.created_at.isoformat()}".encode('utf-8')
    ).hexdigest()

    signature, created = ContractSignature.objects.get_or_create(
        contract_version=version,
        signer_role=role,
        defaults={
            'signer': user,
            'otp_verification': otp,
            'signature_hash': signature_hash,
            'ip_address': ip_address or None,
            'user_agent': (user_agent or '')[:500],
            'signed_at': timezone.now(),
        },
    )

    if not created:
        return signature

    otp.is_used = True
    otp.save(update_fields=['is_used'])

    if contract.status == 'pending_signatures':
        has_client = version.signatures.filter(signer_role='client').exists()
        has_technician = version.signatures.filter(signer_role='technician').exists()
        if has_client and has_technician:
            contract.status = 'pending_finalization'
            contract.save(update_fields=['status', 'updated_at'])

    _audit(contract, 'contract_signed', actor=user, payload={'role': role, 'version_number': version.version_number})
    return signature


@transaction.atomic
def finalize_signed_contract(contract, actor):
    """Finalize signed package and activate escrow/workflow exactly once."""
    if contract.status == 'in_progress' and contract.finalized_at:
        # Idempotent return path
        version = _latest_frozen_version(contract)
        doc = version.documents.filter(kind='signed_pdf').order_by('-created_at').first() if version else None
        return {'contract': contract, 'version': version, 'document': doc, 'attestation': getattr(version, 'attestation', None)}

    if contract.status != 'pending_finalization':
        raise ValueError("Contract must be pending_finalization before finalization.")

    version = _latest_frozen_version(contract)
    if not version:
        raise ValueError("Frozen contract version not found.")

    signatures = list(version.signatures.order_by('signer_role'))
    has_client = any(sig.signer_role == 'client' for sig in signatures)
    has_technician = any(sig.signer_role == 'technician' for sig in signatures)
    if not (has_client and has_technician):
        raise ValueError("Both client and technician signatures are required.")

    verification_code = secrets.token_urlsafe(12).replace('_', '').replace('-', '').upper()[:18]

    # Generate PDF using ReportLab
    pdf_bytes = generate_signed_contract_pdf(contract, version, signatures, verification_code)
    pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()

    # Verify the PDF starts with %PDF
    if not pdf_bytes.startswith(b'%PDF'):
        raise RuntimeError("Generated PDF is invalid: missing %PDF header")

    # Create document record
    document = ContractDocument.objects.create(
        contract_version=version,
        kind='signed_pdf',
        sha256=pdf_sha,
        file_size=len(pdf_bytes),
        created_by=actor,
    )
    filename = f"{contract.contract_reference}_v{version.version_number}_signed.pdf"
    document.file.save(filename, ContentFile(pdf_bytes), save=True)

    # Build attestation payload
    attestation_payload = {
        'contract_reference': contract.contract_reference,
        'version_number': version.version_number,
        'snapshot_hash': version.canonical_snapshot_hash,
        'document_sha256': document.sha256,
        'signed_roles': sorted([sig.signer_role for sig in signatures]),
        'signed_at': max(s.signed_at for s in signatures).isoformat(),
        'verification_code': verification_code,
        'finalized_at': timezone.now().isoformat(),
        'terms_version': 'v1.0',
        'platform_legal_name': 'Tiqani Platform',
        'platform_registration': getattr(settings, 'CONTRACT_PLATFORM_REGISTRATION', ''),
    }
    attestation_hash = hashlib.sha256(
        json.dumps(attestation_payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    attestation = PlatformAttestation.objects.create(
        contract_version=version,
        verification_code=verification_code,
        attestation_hash=attestation_hash,
        payload=attestation_payload,
    )

    # Activate escrow and mark technician unavailable only now.
    contract._setup_contract_escrow()
    contract.status = 'in_progress'
    contract.finalized_at = timezone.now()
    contract.finalized_by = actor
    contract.technician.is_available = False
    contract.technician.save(update_fields=['is_available'])
    contract.save(update_fields=['escrow_amount', 'client_platform_fee', 'technician_platform_fee', 'status', 'finalized_at', 'finalized_by', 'updated_at'])

    # Ensure financial records after activation.
    from wallet.services import ensure_contract_payment_breakdown, create_contract_funding_intent
    ensure_contract_payment_breakdown(contract)
    create_contract_funding_intent(contract, contract.client.user)

    # Notifications and audit
    from notification.services import notify_contract_in_progress
    try:
        notify_contract_in_progress(contract)
    except Exception as e:
        logger.warning("Finalization notification failed for %s: %s", contract.contract_reference, e, exc_info=True)

    _audit(contract, 'contract_finalized', actor=actor, payload={
        'version_number': version.version_number,
        'verification_code': verification_code,
        'document_sha256': document.sha256,
        'document_file_size': document.file_size,
    })

    # Add chat system message if a room exists.
    from chat.models import ServiceChatMessage
    room = contract.chat_rooms.order_by('-created_at').first()
    if room:
        ServiceChatMessage.objects.create(
            room=room,
            sender=contract.client.user,
            message_type=ServiceChatMessage.MessageType.SYSTEM,
            body=f"Contract {contract.contract_reference} finalized and activated. Verification code: {verification_code}",
            metadata={
                'contract_id': str(contract.id),
                'verification_code': verification_code,
                'event': 'contract_finalized',
                'finalized_at': timezone.now().isoformat(),
            },
        )

    return {'contract': contract, 'version': version, 'document': document, 'attestation': attestation}


def get_contract_signatures(contract, user):
    """List signature records for participants/admin."""
    is_participant = contract.client.user_id == user.id or contract.technician.user_id == user.id
    if not (is_participant or user.is_staff):
        raise PermissionError("Not allowed to view signatures.")
    version = _latest_frozen_version(contract)
    if not version:
        return []
    return list(version.signatures.order_by('signer_role'))


def get_contract_documents(contract, user):
    """List stored documents for participants/admin."""
    is_participant = contract.client.user_id == user.id or contract.technician.user_id == user.id
    if not (is_participant or user.is_staff):
        raise PermissionError("Not allowed to view documents.")
    version = _latest_frozen_version(contract)
    if not version:
        return []
    return list(version.documents.order_by('-created_at'))


def get_final_document(contract, user):
    """Get final signed PDF document for contract."""
    documents = get_contract_documents(contract, user)
    for doc in documents:
        if doc.kind == 'signed_pdf':
            return doc
    return None


def public_verify_by_code(verification_code):
    """Public verification by attestation code.

    Returns only non-sensitive metadata — no emails, phones, addresses, OTP data,
    wallet info, or chat content.
    """
    att = get_object_or_404(PlatformAttestation, verification_code=verification_code)
    version = att.contract_version
    contract = version.contract
    doc = version.documents.filter(kind='signed_pdf').order_by('-created_at').first()

    signatures = list(version.signatures.order_by('signer_role'))
    has_client = any(s.signer_role == 'client' for s in signatures)
    has_technician = any(s.signer_role == 'technician' for s in signatures)

    return {
        'valid': True,
        'contract_reference': contract.contract_reference,
        'version': version.version_number,
        'status': contract.status,
        'document_type': 'FINAL_SIGNED_PDF',
        'finalized_at': contract.finalized_at.isoformat() if contract.finalized_at else None,
        'client_signature_verified': has_client,
        'technician_signature_verified': has_technician,
        'platform_attestation_verified': True,
        'document_hash': doc.sha256 if doc else None,
        'attestation_id': att.verification_code,
    }


def public_verify_uploaded_pdf(file_obj):
    """Public PDF hash verification endpoint helper.

    Does not store the uploaded file permanently.
    """
    body = file_obj.read()
    pdf_sha = hashlib.sha256(body).hexdigest()
    doc = ContractDocument.objects.filter(kind='signed_pdf', sha256=pdf_sha).select_related('contract_version__contract').first()
    if not doc:
        return {'match': False, 'document_sha256': pdf_sha}

    att = getattr(doc.contract_version, 'attestation', None)
    return {
        'match': True,
        'document_sha256': pdf_sha,
        'verification_code': att.verification_code if att else None,
        'contract_reference': doc.contract_version.contract.contract_reference,
        'version_number': doc.contract_version.version_number,
    }


def create_contract(client_profile, technician_profile, data):
    """Create a draft contract between client and technician."""
    contract = Contract(
        client=client_profile,
        technician=technician_profile,
        work_description=data.get("work_description", ""),
    )
    contract.save()

    # Notify technician
    from notification.services import notify_contract_created
    try:
        notify_contract_created(contract, client_profile.user)
    except Exception:
        pass

    return contract


def update_contract_proposal(contract, technician_profile, data):
    """Technician fills proposal fields on a draft contract."""
    if contract.technician.user != technician_profile.user:
        raise PermissionError("Only the assigned technician can update the proposal.")

    if contract.status not in ("draft",):
        raise ValueError("Proposal can only be updated on draft contracts.")

    for field in ("work_description", "agreed_amount", "amount_usd", "duration_days", "start_date", "stage_number"):
        if field in data:
            setattr(contract, field, data[field])

    # Validate stage_number is one of the allowed choices
    if contract.stage_number and contract.stage_number not in dict(Contract.STAGE_CHOICES):
        raise ValueError(f"stage_number must be one of {list(dict(Contract.STAGE_CHOICES).keys())}")

    contract.save()  # save() handles auto-transition to pending_acceptance

    # Notify client of proposal
    from notification.services import notify_contract_proposal_submitted
    try:
        notify_contract_proposal_submitted(contract, technician_profile.user)
    except Exception:
        pass

    return contract


@transaction.atomic
def accept_contract(contract, user):
    """Accept contract. When both parties accept, move to pending_signatures."""
    is_client = hasattr(user, "client_profile") and contract.client.user == user
    is_technician = hasattr(user, "technician_profile") and contract.technician.user == user

    if not is_client and not is_technician:
        raise PermissionError("Only contract participants can accept.")

    if contract.status not in ("pending_acceptance",):
        raise ValueError("Contract must be in pending_acceptance status to accept.")

    if is_client:
        if contract.client_accepted:
            return contract  # idempotent
        contract.client_accepted = True

    if is_technician:
        if contract.technician_accepted:
            return contract
        contract.technician_accepted = True

    # Save triggers status transition to pending_signatures + stage creation.
    contract.save()
    contract.refresh_from_db()

    # Phase 6: notifications
    from notification.services import notify_contract_accepted
    try:
        if is_client:
            notify_contract_accepted(contract, user, contract.technician.user)
        if is_technician:
            notify_contract_accepted(contract, user, contract.client.user)
    except Exception:
        pass

    if contract.status == 'pending_signatures':
        _audit(contract, 'pending_signatures_reached', actor=user)

    return contract


@transaction.atomic
def cancel_contract(contract, user, reason=""):
    """Cancel a contract under safe rules."""
    is_client = hasattr(user, "client_profile") and contract.client.user == user
    is_technician = hasattr(user, "technician_profile") and contract.technician.user == user
    is_admin = user.is_staff

    if not (is_client or is_technician or is_admin):
        raise PermissionError("Only participants or admin can cancel.")

    if contract.status in ("completed", "canceled"):
        raise ValueError(f"Cannot cancel a {contract.status} contract.")

    # If in_progress, only admin can cancel (refund logic is complex)
    if contract.status == "in_progress" and not is_admin:
        raise PermissionError(
            "Only an admin can cancel an in-progress contract. "
            "Please contact support."
        )

    contract.cancel(reason=reason)
    contract.refresh_from_db()

    # Notify other participant
    from notification.services import notify_contract_canceled
    try:
        other = None
        if is_client:
            other = contract.technician.user
        elif is_technician:
            other = contract.client.user
        notify_contract_canceled(contract, user, other_participant=other, reason=reason)
    except Exception:
        pass

    return contract


def update_stage(stage, technician_profile, data):
    """Technician updates stage description/deadline before approval."""
    if stage.contract.technician.user != technician_profile.user:
        raise PermissionError("Only the assigned technician can update this stage.")

    if stage.is_approved_by_client:
        raise ValueError("Cannot update an already approved stage.")

    for field in ("stage_description", "deadline"):
        if field in data:
            setattr(stage, field, data[field])
    stage.save()
    return stage


@transaction.atomic
def submit_stage(stage, technician_profile):
    """Technician marks stage as completed/submitted."""
    if stage.contract.technician.user != technician_profile.user:
        raise PermissionError("Only the assigned technician can submit this stage.")

    if stage.completed_at:
        raise ValueError("Stage has already been submitted.")

    stage.mark_complete()

    # Notify client
    from notification.services import notify_stage_submitted
    try:
        notify_stage_submitted(stage, technician_profile.user)
    except Exception:
        pass

    return stage


@transaction.atomic
def approve_stage(stage, client_profile):
    """Client approves stage — payment released internally."""
    if stage.contract.client.user != client_profile.user:
        raise PermissionError("Only the contract client can approve stages.")

    if not stage.completed_at:
        raise ValueError("Stage must be submitted before approval.")

    # Phase 4: use fee-aware stage release
    from wallet.services import record_stage_release_with_fees
    stage = record_stage_release_with_fees(stage)

    # Check if all stages approved → complete contract
    all_approved = not stage.contract.stages.filter(is_approved_by_client=False).exists()
    if all_approved:
        stage.contract.mark_completed()

    # Notifications
    from notification.services import notify_stage_approved, notify_contract_completed
    try:
        notify_stage_approved(stage, client_profile.user)
        if all_approved:
            notify_contract_completed(stage.contract, actor=client_profile.user)
    except Exception:
        pass

    return stage


@transaction.atomic
def create_extension_request(contract, technician_profile, data):
    """Create a time extension request."""
    if contract.technician.user != technician_profile.user:
        raise PermissionError("Only the assigned technician can request extensions.")

    ext = TimeExtensionRequest(
        contract=contract,
        requested_by=technician_profile,
        requested_days=data["requested_days"],
        reason=data.get("reason", ""),
    )
    ext.full_clean()
    ext.save()

    # Notify client
    from notification.services import notify_extension_requested
    try:
        notify_extension_requested(ext, technician_profile.user)
    except Exception:
        pass

    return ext


@transaction.atomic
def respond_extension_request(ext_request, client_profile, approve, response_text=""):
    """Client approves or rejects extension request."""
    if ext_request.contract.client.user != client_profile.user:
        raise PermissionError("Only the client can respond to extension requests.")

    if ext_request.status != "pending":
        raise ValueError("Extension request has already been processed.")

    if approve:
        ext_request.approve(response_text)
        from notification.services import notify_extension_approved
        try:
            notify_extension_approved(ext_request, client_profile.user)
        except Exception:
            pass
    else:
        ext_request.reject(response_text)
        from notification.services import notify_extension_rejected
        try:
            notify_extension_rejected(ext_request, client_profile.user)
        except Exception:
            pass

    return ext_request
