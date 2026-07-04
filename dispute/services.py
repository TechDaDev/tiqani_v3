"""Phase 10 — Dispute, refund, and reversal business logic."""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Literal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from contract.models import Contract, ContractAuditEvent
from wallet.models import (
    ContractSettlement,
    ContractPaymentBreakdown,
    PlatformEarning,
    PlatformWallet,
    PlatformWalletTransaction,
    Wallet,
    WalletTransaction,
)

from .models import (
    ContractDispute,
    DisputeStatement,
    DisputeEvidence,
    DisputeResolution,
    DisputeAuditEvent,
    RefundRecord,
    ChargebackEvent,
    UserFinancialLiability,
    DisputeStatus,
    DisputeCategory,
    ResolutionType,
    RefundSourceType,
    RefundStatus,
    ChargebackStatus,
    LiabilityStatus,
)

PRECISION = Decimal("0.01")


def _q(val: Decimal) -> Decimal:
    return val.quantize(PRECISION, rounding=ROUND_HALF_UP)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────


def _record_audit(dispute, event_type, actor=None, payload=None):
    """Append an immutable audit event."""
    DisputeAuditEvent.objects.create(
        dispute=dispute,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )


# ──────────────────────────────────────────────
#  Dispute eligibility
# ──────────────────────────────────────────────


def check_dispute_eligibility(contract, user) -> tuple[bool, str]:
    """
    Check whether a contract is eligible for dispute by the given user.

    Returns (eligible: bool, reason: str).
    """
    if contract.is_delete:
        return False, "Contract is deleted."

    # Must be client or technician participant
    is_client = hasattr(user, "client_profile") and contract.client.user_id == user.id
    is_technician = hasattr(user, "technician_profile") and contract.technician.user_id == user.id
    if not is_client and not is_technician:
        return False, "Only contract participants can open a dispute."

    # Contract must be funded
    if not contract.escrow_amount and not ContractSettlement.objects.filter(
        contract=contract, status=ContractSettlement.Status.COMPLETED,
    ).exists():
        return False, "Contract is not yet funded or settled."

    # Contract must be in an eligible status
    eligible_statuses = ["active", "in_progress", "completion_requested", "completed"]
    if contract.status not in eligible_statuses:
        return False, f"Contract status '{contract.status}' is not eligible for dispute."

    # No open dispute for same contract
    if ContractDispute.objects.filter(
        contract=contract,
        status__in=[DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE,
                     DisputeStatus.UNDER_REVIEW, DisputeStatus.MEDIATION],
    ).exists():
        return False, "An active dispute already exists for this contract."

    return True, ""


# ──────────────────────────────────────────────
#  Financial restriction
# ──────────────────────────────────────────────


def is_financially_restricted(contract) -> bool:
    """Check if contract has open disputes that restrict financial actions."""
    return ContractDispute.objects.filter(
        contract=contract,
        status__in=[DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE,
                     DisputeStatus.UNDER_REVIEW, DisputeStatus.MEDIATION,
                     DisputeStatus.RESOLUTION_PROPOSED],
    ).exists()


# ──────────────────────────────────────────────
#  Category derivation
# ──────────────────────────────────────────────


def derive_dispute_category(contract) -> str:
    """
    Determine the financial category for a dispute based on contract state.
    """
    settlement = ContractSettlement.objects.filter(
        contract=contract,
        status=ContractSettlement.Status.COMPLETED,
    ).first()

    if not settlement:
        return DisputeCategory.PRE_SETTLEMENT

    # Check technician wallet
    tech_wallet = contract.technician.user.wallet
    tech_balance = tech_wallet.balance

    # Check unrecoverable withdrawals
    from wallet.models import WithdrawalRequest
    paid_withdrawals = WithdrawalRequest.objects.filter(
        user=contract.technician.user,
        status__in=["paid", "processing"],
        wallet=tech_wallet,
    ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

    required_reversal = settlement.technician_net_amount
    available = tech_balance + paid_withdrawals  # paid withdrawals are gone

    if available >= required_reversal:
        return DisputeCategory.POST_SETTLEMENT_RECOVERABLE
    elif available > Decimal("0"):
        return DisputeCategory.POST_SETTLEMENT_PARTIALLY_RECOVERABLE
    else:
        return DisputeCategory.POST_SETTLEMENT_NON_RECOVERABLE


# ──────────────────────────────────────────────
#  Dispute opening
# ──────────────────────────────────────────────


@transaction.atomic
def open_dispute(
    *,
    contract_id,
    opened_by,
    reason,
    statement,
    claimed_amount,
    idempotency_key=None,
    dispute_id=None,
) -> ContractDispute:
    """
    Open a new dispute on a contract.

    When dispute_id is provided, uses that as the dispute UUID (for deterministic E2E fixtures).
    Idempotent when idempotency_key is provided.
    """
    # Idempotency
    if idempotency_key:
        existing = ContractDispute.objects.filter(
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing

    contract = Contract.objects.select_for_update().get(id=contract_id)

    eligible, msg = check_dispute_eligibility(contract, opened_by)
    if not eligible:
        raise ValueError(msg)

    # Determine respondent
    is_client = hasattr(opened_by, "client_profile") and contract.client.user_id == opened_by.id
    respondent = contract.technician.user if is_client else contract.client.user

    # Validate claimed amount
    if claimed_amount > (contract.agreed_amount or Decimal("0")):
        raise ValueError("Claimed amount cannot exceed contract agreed amount.")

    # Derive category
    category = derive_dispute_category(contract)

    kwargs = {}
    if dispute_id is not None:
        kwargs["id"] = dispute_id

    dispute = ContractDispute.objects.create(
        **kwargs,
        contract=contract,
        opened_by=opened_by,
        respondent=respondent,
        reason=reason,
        category=category,
        claimed_amount=_q(claimed_amount),
        status=DisputeStatus.OPEN,
        idempotency_key=idempotency_key,
    )

    # Create initial statement
    if statement:
        DisputeStatement.objects.create(
            dispute=dispute,
            submitted_by=opened_by,
            statement=statement,
        )

    # Audit
    _record_audit(dispute, "DISPUTE_CREATED", opened_by, {
        "reason": reason,
        "claimed_amount": str(claimed_amount),
        "category": category,
    })

    # Notify respondent
    _notify_dispute_opened(dispute, opened_by)

    return dispute


# ──────────────────────────────────────────────
#  Statements
# ──────────────────────────────────────────────


@transaction.atomic
def add_dispute_statement(*, dispute_id, submitted_by, statement) -> ContractDispute:
    """Add a statement to a dispute. Returns the updated dispute."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status not in [DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE,
                               DisputeStatus.UNDER_REVIEW]:
        raise ValueError("Cannot add statement in current dispute status.")

    stmt = DisputeStatement.objects.create(
        dispute=dispute,
        submitted_by=submitted_by,
        statement=statement,
    )

    # If respondent is submitting and dispute is OPEN, move to AWAITING_RESPONSE
    if submitted_by.id == dispute.respondent_id and dispute.status == DisputeStatus.OPEN:
        dispute.status = DisputeStatus.AWAITING_RESPONSE
        dispute.save(update_fields=["status"])

    _record_audit(dispute, "DISPUTE_STATEMENT_ADDED", submitted_by, {
        "statement_id": str(stmt.id),
    })
    _notify_dispute_response_submitted(dispute, submitted_by)

    return dispute


# ──────────────────────────────────────────────
#  Evidence
# ──────────────────────────────────────────────


@transaction.atomic
def add_dispute_evidence(
    *, dispute_id, submitted_by, evidence_type, description="", file=None,
    mime_type="", file_size=0, integrity_hash="",
) -> DisputeEvidence:
    """Submit evidence for a dispute."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status not in [DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE,
                               DisputeStatus.UNDER_REVIEW, DisputeStatus.MEDIATION]:
        raise ValueError("Cannot add evidence in current dispute status.")

    evidence = DisputeEvidence.objects.create(
        dispute=dispute,
        submitted_by=submitted_by,
        evidence_type=evidence_type,
        description=description,
        file=file,
        mime_type=mime_type,
        file_size=file_size,
        integrity_hash=integrity_hash,
    )

    _record_audit(dispute, "DISPUTE_EVIDENCE_ADDED", submitted_by, {
        "evidence_id": str(evidence.id),
        "evidence_type": evidence_type,
    })

    return evidence


# ──────────────────────────────────────────────
#  Cancel
# ──────────────────────────────────────────────


@transaction.atomic
def cancel_dispute(*, dispute_id, actor) -> ContractDispute:
    """Cancel a dispute. Only the opener can cancel."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.opened_by_id != actor.id:
        raise ValueError("Only the dispute opener can cancel.")

    if dispute.status not in [DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE]:
        raise ValueError("Dispute cannot be canceled in current status.")

    dispute.status = DisputeStatus.CANCELED
    dispute.closed_at = timezone.now()
    dispute.save(update_fields=["status", "closed_at"])

    _record_audit(dispute, "DISPUTE_CANCELED", actor)
    _notify_dispute_canceled(dispute, actor)

    return dispute


# ──────────────────────────────────────────────
#  Staff actions
# ──────────────────────────────────────────────


@transaction.atomic
def assign_staff(*, dispute_id, staff_user) -> ContractDispute:
    """Assign staff to a dispute."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    dispute.assigned_staff = staff_user
    dispute.save(update_fields=["assigned_staff"])

    _record_audit(dispute, "DISPUTE_ASSIGNED", staff_user, {
        "staff_id": str(staff_user.id),
    })
    _notify_dispute_assigned(dispute, staff_user)

    return dispute


@transaction.atomic
def start_review(*, dispute_id, actor) -> ContractDispute:
    """Move dispute to under review."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status not in [DisputeStatus.OPEN, DisputeStatus.AWAITING_RESPONSE]:
        raise ValueError("Dispute must be OPEN or AWAITING_RESPONSE to start review.")

    dispute.status = DisputeStatus.UNDER_REVIEW
    dispute.review_started_at = timezone.now()
    dispute.save(update_fields=["status", "review_started_at"])

    _record_audit(dispute, "DISPUTE_REVIEW_STARTED", actor)
    _notify_dispute_under_review(dispute, actor)

    return dispute


@transaction.atomic
def start_mediation(*, dispute_id, actor) -> ContractDispute:
    """Move dispute to mediation."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status not in [DisputeStatus.UNDER_REVIEW, DisputeStatus.RESOLUTION_PROPOSED]:
        raise ValueError("Dispute must be UNDER_REVIEW to start mediation.")

    dispute.status = DisputeStatus.MEDIATION
    dispute.save(update_fields=["status"])

    _record_audit(dispute, "DISPUTE_MEDIATION_STARTED", actor)
    _notify_mediation_started(dispute, actor)

    return dispute


@transaction.atomic
def propose_resolution(*, dispute_id, actor, resolution_data) -> ContractDispute:
    """Propose a resolution (without executing financials)."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status not in [DisputeStatus.UNDER_REVIEW, DisputeStatus.MEDIATION]:
        raise ValueError("Dispute must be UNDER_REVIEW or MEDIATION to propose resolution.")

    dispute.status = DisputeStatus.RESOLUTION_PROPOSED
    dispute.save(update_fields=["status"])

    _record_audit(dispute, "DISPUTE_RESOLUTION_PROPOSED", actor, resolution_data)
    _notify_resolution_proposed(dispute, actor)

    return dispute


# ──────────────────────────────────────────────
#  Financial resolution
# ──────────────────────────────────────────────


@transaction.atomic
def resolve_dispute(
    *,
    dispute_id,
    actor,
    resolution_type,
    client_refund_amount=Decimal("0"),
    technician_retained_amount=Decimal("0"),
    platform_fee_reversal_amount=Decimal("0"),
    escrow_released_amount=Decimal("0"),
    wallet_reversal_amount=Decimal("0"),
    unrecoverable_amount=Decimal("0"),
    outstanding_liability_amount=Decimal("0"),
    resolution_reason="",
    idempotency_key=None,
) -> tuple[ContractDispute, DisputeResolution, Optional[RefundRecord], Optional[UserFinancialLiability]]:
    """
    Resolve a dispute with full financial execution.

    This is the main financial mutation entry point.
    Creates resolution, refund records, wallet reversals, and liabilities.

    Returns (dispute, resolution, refund_record, liability).
    """
    if idempotency_key:
        existing_resolution = DisputeResolution.objects.filter(
            dispute_id=dispute_id,
        ).first()
        if existing_resolution:
            dispute = ContractDispute.objects.get(id=dispute_id)
            refund = RefundRecord.objects.filter(dispute_id=dispute_id).first()
            liability = UserFinancialLiability.objects.filter(source_dispute_id=dispute_id).first()
            return dispute, existing_resolution, refund, liability

    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)
    contract = Contract.objects.select_for_update().get(id=dispute.contract_id)

    if dispute.status not in [DisputeStatus.RESOLUTION_PROPOSED, DisputeStatus.UNDER_REVIEW,
                               DisputeStatus.MEDIATION]:
        raise ValueError("Dispute must be in resolvable status.")

    # Validate amounts
    if resolution_type in [ResolutionType.FULL_CLIENT_REFUND, ResolutionType.PARTIAL_CLIENT_REFUND,
                            ResolutionType.SPLIT_RESOLUTION]:
        if client_refund_amount <= 0:
            raise ValueError("Client refund amount must be positive.")
    if resolution_type == ResolutionType.MANUAL_RECOVERY_REQUIRED:
        if outstanding_liability_amount <= 0:
            raise ValueError("Outstanding liability must be positive for manual recovery.")

    # Create resolution record
    resolution = DisputeResolution.objects.create(
        dispute=dispute,
        resolved_by=actor,
        resolution_type=resolution_type,
        client_refund_amount=_q(client_refund_amount),
        technician_retained_amount=_q(technician_retained_amount),
        platform_fee_reversal_amount=_q(platform_fee_reversal_amount),
        escrow_released_amount=_q(escrow_released_amount),
        wallet_reversal_amount=_q(wallet_reversal_amount),
        unrecoverable_amount=_q(unrecoverable_amount),
        outstanding_liability_amount=_q(outstanding_liability_amount),
        resolution_reason=resolution_reason,
    )

    # Execute financial movements
    refund_record = None
    liability = None

    if client_refund_amount > 0:
        refund_record = _execute_refund(
            dispute=dispute,
            contract=contract,
            amount=client_refund_amount,
            resolution=resolution,
            actor=actor,
            idempotency_key=idempotency_key,
        )

    if outstanding_liability_amount > 0:
        liability = UserFinancialLiability.objects.create(
            user=dispute.respondent,
            source_dispute=dispute,
            original_amount=_q(outstanding_liability_amount),
            remaining_amount=_q(outstanding_liability_amount),
        )
        _record_audit(dispute, "LIABILITY_CREATED", actor, {
            "liability_id": str(liability.id),
            "amount": str(outstanding_liability_amount),
        })

    # Update dispute
    dispute.status = DisputeStatus.RESOLVED
    dispute.resolved_at = timezone.now()
    dispute.resolution_summary = resolution_reason
    dispute.save(update_fields=["status", "resolved_at", "resolution_summary"])

    _record_audit(dispute, "DISPUTE_RESOLVED", actor, {
        "resolution_id": str(resolution.id),
        "resolution_type": resolution_type,
        "client_refund_amount": str(client_refund_amount),
        "technician_retained_amount": str(technician_retained_amount),
        "platform_fee_reversal_amount": str(platform_fee_reversal_amount),
        "wallet_reversal_amount": str(wallet_reversal_amount),
        "unrecoverable_amount": str(unrecoverable_amount),
    })
    _notify_dispute_resolved(dispute, actor)

    return dispute, resolution, refund_record, liability


# ──────────────────────────────────────────────
#  Refund execution (internal)
# ──────────────────────────────────────────────


def _execute_refund(
    *, dispute, contract, amount, resolution, actor, idempotency_key=None,
) -> RefundRecord:
    """
    Execute a refund based on the dispute's financial category.

    Handles:
    - Pre-settlement: refund from escrow
    - Post-settlement recoverable: reverse technician wallet
    - Post-settlement partially recoverable: partial reversal + liability
    - Platform fee reversal: create compensating platform wallet transaction
    """
    settlement = ContractSettlement.objects.filter(
        contract=contract,
        status=ContractSettlement.Status.COMPLETED,
    ).first()

    refund_amount = _q(amount)
    source_type = RefundSourceType.ESCROW
    wallet_txn = None

    if not settlement:
        # Pre-settlement: refund from escrow
        if contract.escrow_amount < refund_amount:
            refund_amount = contract.escrow_amount

        # Refund client from escrow
        client_wallet = Wallet.objects.select_for_update().get(user=contract.client.user)
        client_wallet.balance += refund_amount
        client_wallet.save(update_fields=["balance"])

        wallet_txn = WalletTransaction.objects.create(
            wallet=client_wallet,
            contract=contract,
            transaction_type=WalletTransaction.Type.REFUND,
            amount=refund_amount,
            description=f"Escrow refund for dispute {dispute.id} on contract {contract.contract_reference}",
        )

        contract.escrow_amount -= refund_amount
        contract.save(update_fields=["escrow_amount"])

        source_type = RefundSourceType.ESCROW

    else:
        # Post-settlement: reverse from technician wallet
        tech_wallet = Wallet.objects.select_for_update().get(user=contract.technician.user)
        recoverable = min(refund_amount, tech_wallet.balance)

        if recoverable > 0:
            tech_wallet.balance -= recoverable
            tech_wallet.save(update_fields=["balance"])

            wallet_txn = WalletTransaction.objects.create(
                wallet=tech_wallet,
                contract=contract,
                transaction_type=WalletTransaction.Type.REFUND,
                amount=recoverable,
                description=f"Wallet reversal for dispute {dispute.id} on contract {contract.contract_reference}",
            )

            # Credit client
            client_wallet = Wallet.objects.select_for_update().get(user=contract.client.user)
            client_wallet.balance += recoverable
            client_wallet.save(update_fields=["balance"])

            source_type = RefundSourceType.TECHNICIAN_WALLET_REVERSAL

        # Handle platform fee reversal
        if resolution.platform_fee_reversal_amount > 0:
            _reverse_platform_fees(
                contract=contract,
                dispute=dispute,
                amount=resolution.platform_fee_reversal_amount,
                actor=actor,
            )

    # Reverse platform earnings
    if resolution.platform_fee_reversal_amount > 0 and settlement:
        _reverse_platform_earnings(contract, resolution.platform_fee_reversal_amount)

    # Create refund record
    refund = RefundRecord.objects.create(
        dispute=dispute,
        contract=contract,
        client=contract.client.user,
        amount=refund_amount,
        source_type=source_type,
        status=RefundStatus.COMPLETED,
        wallet_transaction=wallet_txn,
        created_by=actor,
        completed_at=timezone.now(),
        idempotency_key=idempotency_key,
    )

    _record_audit(dispute, "REFUND_CREATED", actor, {
        "refund_id": str(refund.id),
        "amount": str(refund_amount),
        "source_type": source_type,
    })
    _notify_refund_processing(dispute, refund)
    _notify_refund_completed(dispute, refund)

    # Contract audit event
    ContractAuditEvent.objects.create(
        contract=contract,
        event_type="DISPUTE_REFUND",
        actor=actor,
        payload={
            "dispute_id": str(dispute.id),
            "refund_id": str(refund.id),
            "amount": str(refund_amount),
            "source_type": source_type,
        },
    )

    return refund


# ──────────────────────────────────────────────
#  Platform fee reversal
# ──────────────────────────────────────────────


def _reverse_platform_fees(*, contract, dispute, amount, actor):
    """Reverse platform fees by creating compensating transactions."""
    platform_wallet = PlatformWallet.objects.select_for_update().get(
        key=PlatformWallet.GLOBAL_KEY,
    )

    reversal_amount = _q(amount)
    if reversal_amount > platform_wallet.balance:
        reversal_amount = platform_wallet.balance

    platform_wallet.balance -= reversal_amount
    platform_wallet.total_fees_collected -= reversal_amount
    platform_wallet.save(update_fields=["balance", "total_fees_collected"])

    PlatformWalletTransaction.objects.create(
        platform_wallet=platform_wallet,
        contract=contract,
        source_user=actor,
        source_type=PlatformWalletTransaction.SourceType.SYSTEM,
        amount=-reversal_amount,
        balance_after=platform_wallet.balance,
        description=f"Fee reversal for dispute {dispute.id} on contract {contract.contract_reference}",
    )

    _record_audit(dispute, "PLATFORM_FEE_REVERSED", actor, {
        "amount": str(reversal_amount),
        "balance_after": str(platform_wallet.balance),
    })


def _reverse_platform_earnings(contract, amount):
    """Mark platform earnings as reversed for the given contract proportionally."""
    earnings = PlatformEarning.objects.filter(
        contract=contract,
        status=PlatformEarning.Status.EARNED,
    ).order_by("created_at")

    remaining = _q(amount)
    for earning in earnings:
        if remaining <= 0:
            break
        if earning.amount <= remaining:
            earning.status = PlatformEarning.Status.REVERSED
            earning.save(update_fields=["status"])
            remaining -= earning.amount
        else:
            # Partial reversal not supported per-earning, skip
            break


# ──────────────────────────────────────────────
#  Reject
# ──────────────────────────────────────────────


@transaction.atomic
def reject_dispute(*, dispute_id, actor, reason="") -> ContractDispute:
    """Reject a dispute (no financial change)."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status != DisputeStatus.UNDER_REVIEW:
        raise ValueError("Only disputes under review can be rejected.")

    dispute.status = DisputeStatus.REJECTED
    dispute.resolved_at = timezone.now()
    dispute.resolution_summary = reason
    dispute.save(update_fields=["status", "resolved_at", "resolution_summary"])

    # Create resolution
    DisputeResolution.objects.create(
        dispute=dispute,
        resolved_by=actor,
        resolution_type=ResolutionType.DISPUTE_REJECTED,
        resolution_reason=reason or "Dispute rejected after review.",
    )

    _record_audit(dispute, "DISPUTE_REJECTED", actor, {"reason": reason})
    _notify_dispute_resolved(dispute, actor)

    return dispute


# ──────────────────────────────────────────────
#  Close
# ──────────────────────────────────────────────


@transaction.atomic
def close_dispute(*, dispute_id, actor) -> ContractDispute:
    """Close a resolved or rejected dispute."""
    dispute = ContractDispute.objects.select_for_update().get(id=dispute_id)

    if dispute.status not in [DisputeStatus.RESOLVED, DisputeStatus.REJECTED]:
        raise ValueError("Only resolved or rejected disputes can be closed.")

    dispute.status = DisputeStatus.CLOSED
    dispute.closed_at = timezone.now()
    dispute.save(update_fields=["status", "closed_at"])

    _record_audit(dispute, "DISPUTE_CLOSED", actor)

    return dispute


# ──────────────────────────────────────────────
#  Chargeback sandbox services
# ──────────────────────────────────────────────


@transaction.atomic
def create_sandbox_chargeback(
    *, contract_id, amount, reason_code="", created_by=None, idempotency_key=None,
) -> ChargebackEvent:
    """Create a sandbox chargeback event."""
    if idempotency_key:
        existing = ChargebackEvent.objects.filter(
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing

    contract = Contract.objects.select_for_update().get(id=contract_id)

    chargeback = ChargebackEvent.objects.create(
        contract=contract,
        provider_reference=f"sandbox-cb-{uuid.uuid4().hex[:12]}",
        amount=_q(amount),
        reason_code=reason_code,
        status=ChargebackStatus.RECEIVED,
        idempotency_key=idempotency_key,
    )

    _record_audit_on_chargeback(chargeback, "CHARGEBACK_RECEIVED", created_by, {
        "amount": str(amount),
        "reason_code": reason_code,
    })
    _notify_chargeback_received(chargeback)

    return chargeback


@transaction.atomic
def start_chargeback_review(*, chargeback_id, actor) -> ChargebackEvent:
    """Start review of a chargeback."""
    cb = ChargebackEvent.objects.select_for_update().get(id=chargeback_id)
    if cb.status != ChargebackStatus.RECEIVED:
        raise ValueError("Chargeback must be in RECEIVED status.")
    cb.status = ChargebackStatus.UNDER_REVIEW
    cb.save(update_fields=["status"])
    _record_audit_on_chargeback(cb, "CHARGEBACK_REVIEW_STARTED", actor)
    return cb


@transaction.atomic
def submit_chargeback_evidence(*, chargeback_id, actor) -> ChargebackEvent:
    """Submit evidence for a chargeback (sandbox)."""
    cb = ChargebackEvent.objects.select_for_update().get(id=chargeback_id)
    if cb.status != ChargebackStatus.UNDER_REVIEW:
        raise ValueError("Chargeback must be under review.")
    cb.status = ChargebackStatus.EVIDENCE_SUBMITTED
    cb.save(update_fields=["status"])
    return cb


def _record_audit_on_chargeback(chargeback, event_type, actor=None, payload=None):
    """Create an audit event tied to the chargeback's linked dispute or directly."""
    if chargeback.dispute_id:
        _record_audit(chargeback.dispute, event_type, actor, payload)


@transaction.atomic
def sandbox_uphold_chargeback(
    *, chargeback_id, actor, idempotency_key=None,
) -> tuple[ChargebackEvent, Optional[ContractDispute], Optional[DisputeResolution]]:
    """Sandbox: uphold a chargeback and create resolution."""
    if idempotency_key and ChargebackEvent.objects.filter(
        idempotency_key=idempotency_key, status=ChargebackStatus.UPHELD,
    ).exists():
        cb = ChargebackEvent.objects.get(id=chargeback_id)
        dispute = cb.dispute
        resolution = DisputeResolution.objects.filter(dispute=dispute).first() if dispute else None
        return cb, dispute, resolution

    cb = ChargebackEvent.objects.select_for_update().get(id=chargeback_id)
    contract = Contract.objects.select_for_update().get(id=cb.contract_id)

    cb.status = ChargebackStatus.UPHELD
    cb.outcome = ResolutionType.CHARGEBACK_UPHELD
    cb.resolved_by = actor
    cb.resolved_at = timezone.now()
    cb.save(update_fields=["status", "outcome", "resolved_by", "resolved_at"])

    # Create or link dispute
    dispute, _ = ContractDispute.objects.get_or_create(
        contract=contract,
        status=DisputeStatus.UNDER_REVIEW,
        defaults={
            "opened_by": actor,
            "respondent": contract.technician.user,
            "reason": "chargeback_received",
            "category": DisputeCategory.CHARGEBACK_REVIEW,
            "claimed_amount": cb.amount,
            "assigned_staff": actor,
        },
    )
    cb.dispute = dispute
    cb.save(update_fields=["dispute"])

    # Create resolution
    resolution = DisputeResolution.objects.create(
        dispute=dispute,
        resolved_by=actor,
        resolution_type=ResolutionType.CHARGEBACK_UPHELD,
        client_refund_amount=cb.amount,
        resolution_reason=f"Chargeback upheld: {cb.reason_code}",
    )

    dispute.status = DisputeStatus.RESOLVED
    dispute.resolved_at = timezone.now()
    dispute.save(update_fields=["status", "resolved_at"])

    _record_audit(dispute, "CHARGEBACK_UPHELD", actor, {
        "chargeback_id": str(cb.id),
        "amount": str(cb.amount),
    })
    _notify_chargeback_resolved(cb)

    return cb, dispute, resolution


@transaction.atomic
def sandbox_reject_chargeback(
    *, chargeback_id, actor, idempotency_key=None,
) -> ChargebackEvent:
    """Sandbox: reject a chargeback."""
    if idempotency_key and ChargebackEvent.objects.filter(
        idempotency_key=idempotency_key, status=ChargebackStatus.REJECTED,
    ).exists():
        return ChargebackEvent.objects.get(id=chargeback_id)

    cb = ChargebackEvent.objects.select_for_update().get(id=chargeback_id)
    cb.status = ChargebackStatus.REJECTED
    cb.outcome = ResolutionType.CHARGEBACK_REJECTED
    cb.resolved_by = actor
    cb.resolved_at = timezone.now()
    cb.save(update_fields=["status", "outcome", "resolved_by", "resolved_at"])

    if cb.dispute_id:
        _record_audit(cb.dispute, "CHARGEBACK_REJECTED", actor, {
            "chargeback_id": str(cb.id),
        })

    _notify_chargeback_resolved(cb)
    return cb


@transaction.atomic
def sandbox_partial_chargeback(
    *, chargeback_id, actor, partial_amount, idempotency_key=None,
) -> ChargebackEvent:
    """Sandbox: partial chargeback outcome."""
    cb = ChargebackEvent.objects.select_for_update().get(id=chargeback_id)
    cb.status = ChargebackStatus.PARTIALLY_UPHELD
    cb.outcome = f"partial_{partial_amount}"
    cb.resolved_by = actor
    cb.resolved_at = timezone.now()
    cb.save(update_fields=["status", "outcome", "resolved_by", "resolved_at"])

    if cb.dispute_id:
        _record_audit(cb.dispute, "CHARGEBACK_PARTIAL", actor, {
            "chargeback_id": str(cb.id),
            "partial_amount": str(partial_amount),
        })

    _notify_chargeback_resolved(cb)
    return cb


# ──────────────────────────────────────────────
#  Reconciliation helpers
# ──────────────────────────────────────────────


def get_dispute_reconciliation(dispute_id: str) -> dict:
    """Return reconciliation data for a resolved dispute."""
    dispute = ContractDispute.objects.get(id=dispute_id)
    resolution = getattr(dispute, "resolution", None)
    refunds = list(dispute.refunds.all())
    liabilities = list(dispute.liabilities.all())

    return {
        "dispute_id": str(dispute.id),
        "contract_id": str(dispute.contract_id),
        "status": dispute.status,
        "category": dispute.category,
        "resolution_type": resolution.resolution_type if resolution else None,
        "client_refund_amount": str(resolution.client_refund_amount) if resolution else "0.00",
        "technician_retained": str(resolution.technician_retained_amount) if resolution else "0.00",
        "platform_fee_reversal": str(resolution.platform_fee_reversal_amount) if resolution else "0.00",
        "wallet_reversal": str(resolution.wallet_reversal_amount) if resolution else "0.00",
        "unrecoverable": str(resolution.unrecoverable_amount) if resolution else "0.00",
        "outstanding_liability": str(resolution.outstanding_liability_amount) if resolution else "0.00",
        "refund_count": len(refunds),
        "refund_statuses": [r.status for r in refunds],
        "refund_total": str(sum(
            Decimal(str(r.amount)) for r in refunds if r.status == RefundStatus.COMPLETED
        )),
        "liability_count": len(liabilities),
        "liability_remaining": str(sum(
            Decimal(str(l.remaining_amount)) for l in liabilities
        )) if liabilities else "0.00",
    }


# ──────────────────────────────────────────────
#  Notifications
# ──────────────────────────────────────────────


def _notify(msg_type="user", **kwargs):
    """Best-effort notification dispatch."""
    try:
        from notification.services import create_notification, notify_admins
        if msg_type == "admin":
            notify_admins(**kwargs)
        else:
            create_notification(**kwargs)
    except Exception:
        pass


def _notify_dispute_opened(dispute, actor):
    contract = dispute.contract
    _notify(
        recipient=dispute.respondent,
        notification_type="system",
        title="Dispute opened",
        message=f"A dispute has been opened on contract {contract.contract_reference}.",
        actor=actor,
        target_type="dispute",
        target_id=dispute.id,
    )
    _notify("admin",
        notification_type="system",
        title="Dispute opened",
        message=f"Dispute opened on contract {contract.contract_reference}.",
        actor=actor,
        target_type="dispute",
        target_id=dispute.id,
    )


def _notify_dispute_response_submitted(dispute, actor):
    recipient = dispute.opened_by if actor.id == dispute.respondent_id else dispute.respondent
    _notify(
        recipient=recipient,
        notification_type="system",
        title="Dispute response submitted",
        message="A response has been submitted to the dispute.",
        actor=actor,
        target_type="dispute",
        target_id=dispute.id,
    )


def _notify_dispute_assigned(dispute, staff_user):
    _notify(
        recipient=staff_user,
        notification_type="system",
        title="Dispute assigned",
        message=f"You have been assigned to dispute {dispute.id}.",
        target_type="dispute",
        target_id=dispute.id,
    )


def _notify_dispute_under_review(dispute, actor):
    for user in [dispute.opened_by, dispute.respondent]:
        _notify(
            recipient=user,
            notification_type="system",
            title="Dispute under review",
            message="Your dispute is now under review by staff.",
            actor=actor,
            target_type="dispute",
            target_id=dispute.id,
        )


def _notify_mediation_started(dispute, actor):
    for user in [dispute.opened_by, dispute.respondent]:
        _notify(
            recipient=user,
            notification_type="system",
            title="Mediation started",
            message="Mediation has been started for your dispute.",
            actor=actor,
            target_type="dispute",
            target_id=dispute.id,
        )


def _notify_resolution_proposed(dispute, actor):
    for user in [dispute.opened_by, dispute.respondent]:
        _notify(
            recipient=user,
            notification_type="system",
            title="Resolution proposed",
            message="A resolution has been proposed for your dispute.",
            actor=actor,
            target_type="dispute",
            target_id=dispute.id,
        )


def _notify_dispute_resolved(dispute, actor):
    for user in [dispute.opened_by, dispute.respondent]:
        _notify(
            recipient=user,
            notification_type="system",
            title="Dispute resolved",
            message=f"Your dispute has been resolved: {dispute.resolution_summary}",
            actor=actor,
            target_type="dispute",
            target_id=dispute.id,
        )


def _notify_dispute_canceled(dispute, actor):
    recipient = dispute.respondent if actor.id == dispute.opened_by_id else dispute.opened_by
    _notify(
        recipient=recipient,
        notification_type="system",
        title="Dispute canceled",
        message="The dispute has been canceled.",
        actor=actor,
        target_type="dispute",
        target_id=dispute.id,
    )


def _notify_refund_processing(dispute, refund):
    _notify(
        recipient=dispute.opened_by,
        notification_type="system",
        title="Refund processing",
        message=f"A refund of {refund.amount} is being processed.",
        target_type="refund",
        target_id=refund.id,
    )


def _notify_refund_completed(dispute, refund):
    _notify(
        recipient=dispute.opened_by,
        notification_type="system",
        title="Refund completed",
        message=f"A refund of {refund.amount} has been completed.",
        target_type="refund",
        target_id=refund.id,
    )


def _notify_chargeback_received(chargeback):
    _notify("admin",
        notification_type="system",
        title="Chargeback received",
        message=f"Chargeback of {chargeback.amount} received for contract {chargeback.contract.contract_reference}.",
        target_type="chargeback",
        target_id=chargeback.id,
    )


def _notify_chargeback_resolved(chargeback):
    _notify("admin",
        notification_type="system",
        title="Chargeback resolved",
        message=f"Chargeback {chargeback.id} resolved: {chargeback.outcome}.",
        target_type="chargeback",
        target_id=chargeback.id,
    )
