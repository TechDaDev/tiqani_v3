"""Business logic for Phase 8 contract execution and milestones."""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import (
    Contract,
    ExecutionMilestone,
    DeliverableSubmission,
    RevisionRequest,
    CompletionRequest,
    ContractAuditEvent,
)


# ──────────────────────────────────────────────
#  Eligibility
# ──────────────────────────────────────────────


def check_execution_eligibility(contract, user):
    """
    Check whether a contract is eligible for execution activation.
    Returns (eligible: bool, reason: str).
    """
    if contract.status not in ('in_progress',):
        return False, f"Contract status is '{contract.status}', must be 'in_progress'."
    if contract.status == 'active':
        return False, "Contract is already active."
    if contract.status == 'completed':
        return False, "Contract is already completed."
    if contract.status == 'canceled':
        return False, "Contract is canceled."

    # Check funding via wallet service
    from wallet.services import get_contract_funding_status
    funding = get_contract_funding_status(contract)
    if funding != 'funded':
        return False, f"Contract is not funded (status: {funding})."

    # Must have at least one milestone
    milestone_count = contract.execution_milestones.count()
    if milestone_count == 0:
        return False, "At least one milestone must be created before activation."

    return True, ""


def check_completion_eligibility(contract, user):
    """
    Check whether a technician can request completion.
    """
    if contract.status != 'active':
        return False, f"Contract must be active, current status: '{contract.status}'."

    # All milestones must be approved
    total = contract.execution_milestones.count()
    approved = contract.execution_milestones.filter(status='APPROVED').count()
    if total == 0:
        return False, "No milestones defined."
    if approved < total:
        return False, f"Only {approved}/{total} milestones approved."

    # No unresolved revisions
    unresolved = contract.execution_milestones.filter(
        revisions__status='OPEN'
    ).exists()
    if unresolved:
        return False, "Unresolved revision requests exist."

    return True, ""


# ──────────────────────────────────────────────
#  Activation
# ──────────────────────────────────────────────


@transaction.atomic
def activate_contract(contract, actor):
    """Activate a funded contract for execution."""
    contract.activate_execution()
    _record_event(contract, 'CONTRACT_ACTIVATED', actor, {
        'activated_at': contract.activated_at.isoformat() if contract.activated_at else None,
    })
    return contract


# ──────────────────────────────────────────────
#  Milestones
# ──────────────────────────────────────────────


@transaction.atomic
def create_milestone(contract, data, actor):
    """Create a draft milestone within a contract."""
    max_seq = contract.execution_milestones.order_by('-sequence').first()
    next_seq = (max_seq.sequence + 1) if max_seq else 1
    sequence = data.get('sequence', next_seq)

    milestone = ExecutionMilestone.objects.create(
        contract=contract,
        sequence=sequence,
        title=data['title'],
        description=data.get('description', ''),
        due_date=data.get('due_date'),
        created_by=actor,
        status=ExecutionMilestone.Status.DRAFT,
    )
    _record_event(contract, 'MILESTONE_CREATED', actor, {
        'milestone_id': str(milestone.id),
        'sequence': milestone.sequence,
        'title': milestone.title,
    })
    return milestone


@transaction.atomic
def start_milestone(milestone, actor):
    """Technician starts work on a pending milestone."""
    if milestone.status != ExecutionMilestone.Status.PENDING:
        raise ValueError(f"Cannot start milestone with status '{milestone.status}'.")
    milestone.status = ExecutionMilestone.Status.IN_PROGRESS
    milestone.started_at = timezone.now()
    milestone.save(update_fields=['status', 'started_at'])
    _record_event(milestone.contract, 'MILESTONE_STARTED', actor, {
        'milestone_id': str(milestone.id),
        'sequence': milestone.sequence,
    })
    return milestone


@transaction.atomic
def submit_deliverable(milestone, data, actor):
    """Technician submits a deliverable for a milestone."""
    if not milestone.can_submit():
        raise ValueError(f"Cannot submit to milestone with status '{milestone.status}'.")

    # Next version
    latest = milestone.submissions.order_by('-version').first()
    next_version = (latest.version + 1) if latest else 1

    submission = DeliverableSubmission.objects.create(
        milestone=milestone,
        submitted_by=actor,
        version=next_version,
        summary=data['summary'],
        notes=data.get('notes', ''),
        external_link=data.get('external_link', ''),
    )

    milestone.status = ExecutionMilestone.Status.SUBMITTED
    milestone.submitted_at = timezone.now()
    milestone.save(update_fields=['status', 'submitted_at'])

    event_type = 'DELIVERABLE_RESUBMITTED' if next_version > 1 else 'DELIVERABLE_SUBMITTED'
    _record_event(milestone.contract, event_type, actor, {
        'milestone_id': str(milestone.id),
        'submission_id': str(submission.id),
        'version': next_version,
    })
    return submission


@transaction.atomic
def request_revision(milestone, submission, data, actor):
    """Client requests revision on a submission."""
    if not milestone.can_request_revision():
        raise ValueError(f"Cannot request revision on milestone with status '{milestone.status}'.")

    rev_count = milestone.revisions.count()
    revision = RevisionRequest.objects.create(
        milestone=milestone,
        submission=submission,
        requested_by=actor,
        reason=data['reason'],
        revision_number=rev_count + 1,
    )

    milestone.status = ExecutionMilestone.Status.REVISION_REQUESTED
    milestone.revision_count += 1
    milestone.save(update_fields=['status', 'revision_count'])

    _record_event(milestone.contract, 'REVISION_REQUESTED', actor, {
        'milestone_id': str(milestone.id),
        'submission_id': str(submission.id),
        'revision_number': revision.revision_number,
    })
    return revision


@transaction.atomic
def approve_milestone(milestone, actor):
    """Client approves a milestone submission."""
    if not milestone.can_approve():
        raise ValueError(f"Cannot approve milestone with status '{milestone.status}'.")

    milestone.status = ExecutionMilestone.Status.APPROVED
    milestone.approved_at = timezone.now()
    milestone.save(update_fields=['status', 'approved_at'])

    _record_event(milestone.contract, 'MILESTONE_APPROVED', actor, {
        'milestone_id': str(milestone.id),
        'sequence': milestone.sequence,
    })
    return milestone


# ──────────────────────────────────────────────
#  Completion
# ──────────────────────────────────────────────


@transaction.atomic
def request_completion(contract, data, actor):
    """Technician requests contract completion."""
    eligible, reason = check_completion_eligibility(contract, actor)
    if not eligible:
        raise ValueError(reason)

    contract.request_completion(actor)
    CompletionRequest.objects.create(
        contract=contract,
        requested_by=actor,
        completion_message=data.get('completion_message', ''),
    )

    _record_event(contract, 'COMPLETION_REQUESTED', actor, {
        'requested_by': str(actor.id),
    })
    return contract


@transaction.atomic
def confirm_completion(contract, completion_request, actor):
    """Client confirms contract completion."""
    if completion_request.status != CompletionRequest.Status.PENDING:
        raise ValueError("Completion request is not pending.")

    contract.confirm_completion()
    completion_request.status = CompletionRequest.Status.CONFIRMED
    completion_request.responded_at = timezone.now()
    completion_request.save(update_fields=['status', 'responded_at'])

    _record_event(contract, 'CONTRACT_COMPLETED', actor, {
        'escrow_held': str(contract.escrow_amount),
        'no_payout': True,
    })
    return contract


@transaction.atomic
def reject_completion(contract, completion_request, data, actor):
    """Client rejects completion request, returning to active."""
    if completion_request.status != CompletionRequest.Status.PENDING:
        raise ValueError("Completion request is not pending.")

    completion_request.status = CompletionRequest.Status.REJECTED
    completion_request.response_message = data.get('response_message', '')
    completion_request.responded_at = timezone.now()
    completion_request.save(update_fields=['status', 'response_message', 'responded_at'])

    contract.status = 'active'
    contract.save(update_fields=['status'])

    _record_event(contract, 'COMPLETION_REJECTED', actor, {
        'reason': data.get('response_message', ''),
    })
    return contract


# ──────────────────────────────────────────────
#  Reordering
# ──────────────────────────────────────────────


@transaction.atomic
def reorder_milestones(contract, ordered_ids):
    """Reorder milestones by sequence."""
    milestones = list(contract.execution_milestones.filter(id__in=ordered_ids))
    if len(milestones) != len(ordered_ids):
        raise ValueError("Some milestone IDs not found in contract.")

    # Set all to temporary high values to avoid unique constraint violations
    temp_base = 100000
    for i, milestone in enumerate(milestones):
        milestone.sequence = temp_base + i
    ExecutionMilestone.objects.bulk_update(milestones, ['sequence'])

    # Now set to final correct ordering
    for idx, milestone_id in enumerate(ordered_ids, start=1):
        milestone = next(m for m in milestones if str(m.id) == str(milestone_id))
        milestone.sequence = idx
    ExecutionMilestone.objects.bulk_update(milestones, ['sequence'])

    return contract.execution_milestones.order_by('sequence').all()


# ──────────────────────────────────────────────
#  History
# ──────────────────────────────────────────────


def _record_event(contract, event_type, actor, payload=None):
    """Record an append-only execution history event."""
    ContractAuditEvent.objects.create(
        contract=contract,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )


def get_execution_history(contract):
    """Get execution history events for a contract."""
    return ContractAuditEvent.objects.filter(
        contract=contract,
        event_type__in=[
            'CONTRACT_ACTIVATED',
            'MILESTONE_CREATED',
            'MILESTONE_STARTED',
            'DELIVERABLE_SUBMITTED',
            'DELIVERABLE_RESUBMITTED',
            'REVISION_REQUESTED',
            'MILESTONE_APPROVED',
            'COMPLETION_REQUESTED',
            'COMPLETION_REJECTED',
            'CONTRACT_COMPLETED',
        ],
    ).select_related('actor').order_by('-created_at')
