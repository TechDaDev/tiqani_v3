"""Phase 9 — Escrow settlement, technician wallet credit, and platform earnings."""

from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    ContractPaymentBreakdown,
    ContractSettlement,
    PlatformEarning,
    PlatformWallet,
    PlatformWalletTransaction,
    Wallet,
    WalletTransaction,
    WithdrawalRequest,
)
from .services import (
    ensure_contract_payment_breakdown,
    get_contract_funding_status,
    _quantize,
)
from contract.models import Contract, ContractAuditEvent

SETTLEMENT_PRECISION = Decimal("0.01")


# ──────────────────────────────────────────────
#  Settlement eligibility
# ──────────────────────────────────────────────


def check_settlement_eligibility(contract, user):
    """
    Check whether a contract is eligible for escrow settlement.

    Returns (eligible: bool, reason: str).
    """
    if contract.is_delete:
        return False, "Contract is deleted."

    if contract.status != "completed":
        return False, f"Contract status is '{contract.status}'; must be 'completed'."

    funding_status = get_contract_funding_status(contract)
    if funding_status != "funded":
        return False, f"Contract funding status is '{funding_status}'; must be 'funded'."

    if not contract.escrow_amount or contract.escrow_amount <= 0:
        return False, "Contract has no remaining escrow."

    # Check for existing completed settlement
    if ContractSettlement.objects.filter(
        contract=contract, status=ContractSettlement.Status.COMPLETED
    ).exists():
        return False, "Contract is already settled."

    # Must have payment breakdown
    if not hasattr(contract, "payment_breakdown"):
        return False, "Contract has no payment breakdown."

    # Only the client can release escrow
    if not hasattr(user, "client_profile") or contract.client.user_id != user.id:
        return False, "Only the contract client can initiate settlement."

    # No pending completion request
    if contract.completion_requests.filter(
        status="pending"
    ).exists():
        return False, "Contract has a pending completion request."

    return True, ""


# ──────────────────────────────────────────────
#  Settlement execution
# ──────────────────────────────────────────────


@transaction.atomic
def settle_completed_contract(
    *,
    contract_id,
    actor,
    idempotency_key=None,
):
    """
    Release escrow for a completed contract.

    Within a single transaction:
    1. Lock all financial records
    2. Validate eligibility
    3. Check for existing settlement (idempotency)
    4. Create settlement record
    5. Credit technician wallet
    6. Record platform earnings
    7. Credit platform wallet
    8. Reduce escrow
    9. Complete settlement

    Returns ContractSettlement.
    """
    contract = (
        Contract.objects.select_for_update()
        .select_related("client__user", "technician__user")
        .get(id=contract_id)
    )

    # Idempotency check — same key returns existing result
    if idempotency_key:
        existing = ContractSettlement.objects.filter(
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing

    # Prevent duplicate settlement
    existing_completed = ContractSettlement.objects.filter(
        contract=contract,
        status=ContractSettlement.Status.COMPLETED,
    ).exists()
    if existing_completed:
        raise ValueError("Contract is already settled.")

    # Validate eligibility
    eligible, reason = check_settlement_eligibility(contract, actor)
    if not eligible:
        raise ValueError(reason)

    # Lock payment breakdown
    breakdown = ContractPaymentBreakdown.objects.select_for_update().get(
        contract=contract
    )

    # Lock technician wallet
    tech_wallet = Wallet.objects.select_for_update().get(
        user=contract.technician.user
    )

    # Lock platform wallet
    platform_wallet_obj = PlatformWallet.objects.select_for_update().get(
        key=PlatformWallet.GLOBAL_KEY,
    )

    # Derive amounts
    released_principal = contract.escrow_amount
    tech_net = breakdown.technician_net_amount
    tech_commission = breakdown.technician_commission_amount
    client_fee = breakdown.client_service_fee_amount
    total_fee = breakdown.total_platform_fee

    if released_principal <= 0:
        raise ValueError("No escrow to release.")

    # Create settlement record
    settlement = ContractSettlement.objects.create(
        contract=contract,
        payment_breakdown=breakdown,
        released_principal=released_principal,
        technician_net_amount=tech_net,
        technician_commission_amount=tech_commission,
        client_service_fee_amount=client_fee,
        total_platform_fee=total_fee,
        currency=breakdown.currency,
        status=ContractSettlement.Status.PROCESSING,
        initiated_by=actor,
        idempotency_key=idempotency_key,
    )

    # 1. Credit technician wallet
    tech_wallet.balance += tech_net
    tech_wallet.save(update_fields=["balance"])

    tech_txn = WalletTransaction.objects.create(
        wallet=tech_wallet,
        contract=contract,
        transaction_type=WalletTransaction.Type.RELEASE,
        amount=tech_net,
        description=f"Escrow release for {contract.contract_reference} — technician net",
    )

    # 2. Create platform earnings
    commission_earning = PlatformEarning.objects.create(
        contract=contract,
        earning_type=PlatformEarning.EarningType.TECHNICIAN_COMMISSION,
        amount=tech_commission,
        status=PlatformEarning.Status.EARNED,
    )
    client_fee_earning = PlatformEarning.objects.create(
        contract=contract,
        earning_type=PlatformEarning.EarningType.CLIENT_SERVICE_FEE,
        amount=client_fee,
        status=PlatformEarning.Status.EARNED,
    )

    # 3. Credit platform wallet
    platform_wallet_obj.balance += total_fee
    platform_wallet_obj.total_fees_collected += total_fee
    platform_wallet_obj.total_technician_fees += tech_commission
    platform_wallet_obj.total_client_fees += client_fee
    platform_wallet_obj.save(
        update_fields=[
            "balance", "total_fees_collected",
            "total_technician_fees", "total_client_fees",
        ]
    )

    PlatformWalletTransaction.objects.create(
        platform_wallet=platform_wallet_obj,
        contract=contract,
        source_user=contract.technician.user,
        source_wallet=tech_wallet,
        source_type=PlatformWalletTransaction.SourceType.TECHNICIAN,
        amount=tech_commission,
        balance_after=platform_wallet_obj.balance,
        description=f"Technician commission for {contract.contract_reference}",
    )
    PlatformWalletTransaction.objects.create(
        platform_wallet=platform_wallet_obj,
        contract=contract,
        source_user=contract.client.user,
        source_wallet=None,
        source_type=PlatformWalletTransaction.SourceType.CLIENT,
        amount=client_fee,
        balance_after=platform_wallet_obj.balance,
        description=f"Client service fee for {contract.contract_reference}",
    )

    # 4. Reduce contract escrow
    contract.escrow_amount = Decimal("0.00")
    contract.save(update_fields=["escrow_amount"])

    # 5. Link settlement to transactions/earnings
    settlement.technician_wallet_transaction = tech_txn
    settlement.platform_commission_earning = commission_earning
    settlement.client_fee_earning = client_fee_earning
    settlement.status = ContractSettlement.Status.COMPLETED
    settlement.completed_at = timezone.now()
    settlement.save(
        update_fields=[
            "technician_wallet_transaction",
            "platform_commission_earning",
            "client_fee_earning",
            "status",
            "completed_at",
        ]
    )

    # 6. Audit event
    ContractAuditEvent.objects.create(
        contract=contract,
        event_type="ESCROW_RELEASED",
        actor=actor,
        payload={
            "settlement_id": str(settlement.id),
            "released_principal": str(released_principal),
            "technician_net": str(tech_net),
            "technician_commission": str(tech_commission),
            "client_service_fee": str(client_fee),
            "total_platform_fee": str(total_fee),
        },
    )

    # 7. Notify
    _notify_settlement(contract, settlement, tech_txn)

    return settlement


# ──────────────────────────────────────────────
#  Notifications
# ──────────────────────────────────────────────


def _notify_settlement(contract, settlement, tech_txn):
    """Send notifications about settlement completion (best-effort)."""
    from notification.services import notify_wallet_transaction

    try:
        notify_wallet_transaction(tech_txn)
    except Exception:
        pass


# ──────────────────────────────────────────────
#  Financial summary
# ──────────────────────────────────────────────


def get_financial_summary(contract_id):
    """Return a structured financial summary for a contract."""
    contract = Contract.objects.get(id=contract_id)

    breakdown = ensure_contract_payment_breakdown(contract)
    settlement = ContractSettlement.objects.filter(
        contract=contract,
    ).order_by("-created_at").first()

    funding_status = get_contract_funding_status(contract)

    return {
        "contract_id": str(contract.id),
        "contract_reference": contract.contract_reference,
        "contract_status": contract.status,
        "agreed_amount": str(contract.agreed_amount),
        "escrow_amount": str(contract.escrow_amount),
        "total_paid": str(contract.total_paid),
        "funding_status": funding_status,
        "payment_breakdown": {
            "contract_amount": str(breakdown.contract_amount),
            "technician_commission_amount": str(breakdown.technician_commission_amount),
            "client_service_fee_amount": str(breakdown.client_service_fee_amount),
            "total_platform_fee": str(breakdown.total_platform_fee),
            "client_total_amount": str(breakdown.client_total_amount),
            "technician_net_amount": str(breakdown.technician_net_amount),
            "currency": breakdown.currency,
        },
        "settlement": (
            {
                "id": str(settlement.id),
                "status": settlement.status,
                "released_principal": str(settlement.released_principal),
                "technician_net_amount": str(settlement.technician_net_amount),
                "technician_commission_amount": str(settlement.technician_commission_amount),
                "client_service_fee_amount": str(settlement.client_service_fee_amount),
                "total_platform_fee": str(settlement.total_platform_fee),
                "completed_at": settlement.completed_at.isoformat() if settlement.completed_at else None,
            }
            if settlement
            else None
        ),
    }
