"""Business logic layer for contract lifecycle operations."""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Contract, ContractStage, TimeExtensionRequest
from wallet.models import WalletTransaction


def create_contract(client_profile, technician_profile, data):
    """Create a draft contract between client and technician."""
    contract = Contract(
        client=client_profile,
        technician=technician_profile,
        work_description=data.get("work_description", ""),
    )
    contract.save()
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
    return contract


@transaction.atomic
def accept_contract(contract, user):
    """Accept contract. When both parties accept, move to in_progress."""
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

    # Save triggers status transition + escrow + stage creation if both accepted
    contract.save()
    contract.refresh_from_db()
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
    return stage


@transaction.atomic
def approve_stage(stage, client_profile):
    """Client approves stage — payment released internally."""
    if stage.contract.client.user != client_profile.user:
        raise PermissionError("Only the contract client can approve stages.")

    if not stage.completed_at:
        raise ValueError("Stage must be submitted before approval.")

    stage.approve_by_client()

    # Check if all stages approved → complete contract
    all_approved = not stage.contract.stages.filter(is_approved_by_client=False).exists()
    if all_approved:
        stage.contract.mark_completed()

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
    else:
        ext_request.reject(response_text)

    return ext_request
