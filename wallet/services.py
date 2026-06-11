"""Fee calculation and payment preparation services."""

from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone

from .models import (
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PlatformEarning,
    PaymentIntent,
    WithdrawalRequest,
    Wallet,
    WalletTransaction,
)

FEE_PRECISION = Decimal("0.01")


def _quantize(val):
    return val.quantize(FEE_PRECISION, rounding=ROUND_HALF_UP)


def get_active_fee_config():
    """Return the active PlatformFeeConfig (creates default if none)."""
    return PlatformFeeConfig.get_active_config()


def calculate_contract_breakdown(contract_amount, fee_config=None):
    """
    Calculate the full financial breakdown for a given contract amount.

    Returns dict with all computed fields.
    Example for 500000 IQD:
        technician_commission_rate = 10.00
        client_service_fee_rate = 5.00
        technician_commission_amount = 50000
        client_service_fee_amount = 25000
        total_platform_fee = 75000
        client_total_amount = 525000
        technician_net_amount = 450000
    """
    if fee_config is None:
        fee_config = get_active_fee_config()

    amount = Decimal(str(contract_amount))

    tech_rate = fee_config.technician_commission_rate
    client_rate = fee_config.client_service_fee_rate

    tech_commission = _quantize(amount * tech_rate / Decimal("100"))
    client_fee = _quantize(amount * client_rate / Decimal("100"))
    total_fee = _quantize(tech_commission + client_fee)
    client_total = _quantize(amount + client_fee)
    tech_net = _quantize(amount - tech_commission)

    return {
        "contract_amount": amount,
        "technician_commission_rate": tech_rate,
        "client_service_fee_rate": client_rate,
        "technician_commission_amount": tech_commission,
        "client_service_fee_amount": client_fee,
        "total_platform_fee": total_fee,
        "client_total_amount": client_total,
        "technician_net_amount": tech_net,
    }


@transaction.atomic
def create_contract_payment_breakdown(contract):
    """Create a ContractPaymentBreakdown snapshot for a contract."""
    if not contract.agreed_amount:
        raise ValueError("Contract must have an agreed_amount before creating breakdown.")

    fee_config = get_active_fee_config()
    calc = calculate_contract_breakdown(contract.agreed_amount, fee_config)

    breakdown = ContractPaymentBreakdown.objects.create(
        contract=contract,
        fee_config=fee_config,
        **calc,
    )
    return breakdown


def ensure_contract_payment_breakdown(contract):
    """Return existing breakdown or create one."""
    if hasattr(contract, "payment_breakdown"):
        return contract.payment_breakdown
    return create_contract_payment_breakdown(contract)


@transaction.atomic
def create_contract_funding_intent(contract, user):
    """Create a PaymentIntent for contract funding if not exists."""
    existing = PaymentIntent.objects.filter(
        contract=contract,
        purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
    ).exclude(status__in=[PaymentIntent.Status.CANCELED]).first()
    if existing:
        return existing

    calc = ensure_contract_payment_breakdown(contract)
    intent = PaymentIntent.objects.create(
        contract=contract,
        user=user,
        amount=calc.client_total_amount,
        purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
    )
    return intent


@transaction.atomic
def mark_payment_intent_paid(payment_intent):
    """Mark a payment intent as paid (internal ledger only)."""
    if payment_intent.status == PaymentIntent.Status.PAID:
        raise ValueError("Payment intent is already paid.")

    payment_intent.status = PaymentIntent.Status.PAID
    payment_intent.paid_at = timezone.now()
    payment_intent.save(update_fields=["status", "paid_at"])

    # Fund the user's wallet
    wallet = payment_intent.user.wallet
    wallet.balance += payment_intent.amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        contract=payment_intent.contract,
        transaction_type=WalletTransaction.Type.DEPOSIT,
        amount=payment_intent.amount,
        description=f"Deposit via {payment_intent.get_purpose_display()} – {payment_intent.id}",
    )
    return payment_intent


@transaction.atomic
def record_platform_earnings_for_contract(contract):
    """Create PlatformEarning records for the full contract (called at stage approval)."""
    breakdown = ensure_contract_payment_breakdown(contract)
    created = []

    # Only create if they don't already exist
    if not PlatformEarning.objects.filter(contract=contract, earning_type=PlatformEarning.EarningType.TECHNICIAN_COMMISSION).exists():
        earning = PlatformEarning.objects.create(
            contract=contract,
            earning_type=PlatformEarning.EarningType.TECHNICIAN_COMMISSION,
            amount=breakdown.technician_commission_amount,
            status=PlatformEarning.Status.EARNED,
        )
        created.append(earning)

    if not PlatformEarning.objects.filter(contract=contract, earning_type=PlatformEarning.EarningType.CLIENT_SERVICE_FEE).exists():
        earning = PlatformEarning.objects.create(
            contract=contract,
            earning_type=PlatformEarning.EarningType.CLIENT_SERVICE_FEE,
            amount=breakdown.client_service_fee_amount,
            status=PlatformEarning.Status.EARNED,
        )
        created.append(earning)

    return created


@transaction.atomic
def record_stage_release_with_fees(stage):
    """
    When a stage is approved, release the technician's net portion.
    Record proportional platform earnings.
    Stage amount is a portion of agreed_amount.
    """
    contract = stage.contract
    if stage.is_approved_by_client:
        raise ValueError("Stage is already approved.")

    stage.approve_by_client()

    # Calculate proportional share
    total_stages = contract.stages.count()
    if total_stages == 0:
        return stage

    breakdown = ensure_contract_payment_breakdown(contract)

    # Proportional per-stage amounts
    stage_ratio = stage.amount / contract.agreed_amount if contract.agreed_amount else Decimal("0")
    stage_commission = _quantize(breakdown.technician_commission_amount * stage_ratio)
    stage_client_fee = _quantize(breakdown.client_service_fee_amount * stage_ratio)
    stage_tech_net = _quantize(stage.amount - stage_commission)

    # Create platform earning records per stage if not exist
    for earning_type, amount in [
        (PlatformEarning.EarningType.TECHNICIAN_COMMISSION, stage_commission),
        (PlatformEarning.EarningType.CLIENT_SERVICE_FEE, stage_client_fee),
    ]:
        PlatformEarning.objects.get_or_create(
            contract=contract,
            stage=stage,
            earning_type=earning_type,
            defaults={
                "amount": amount,
                "status": PlatformEarning.Status.EARNED,
            },
        )

    return stage


@transaction.atomic
def create_withdrawal_request(user, amount, method="", notes=""):
    """Create a withdrawal request."""
    wallet = user.wallet
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")

    if wallet.balance < amount:
        raise ValueError(
            f"Insufficient balance. You have {wallet.balance} but requested {amount}."
        )

    req = WithdrawalRequest.objects.create(
        user=user,
        wallet=wallet,
        amount=amount,
        requested_method=method,
        notes=notes,
    )
    return req


@transaction.atomic
def approve_withdrawal_request(withdrawal_request, admin_user, note=""):
    """Approve a withdrawal (internal ledger deduction)."""
    if withdrawal_request.status != WithdrawalRequest.Status.PENDING:
        raise ValueError("Only pending requests can be approved.")

    wallet = withdrawal_request.wallet
    if wallet.balance < withdrawal_request.amount:
        raise ValueError("Insufficient balance.")

    wallet.balance -= withdrawal_request.amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.Type.WITHDRAWAL,
        amount=withdrawal_request.amount,
        description=f"Withdrawal approved by {admin_user.username}: {withdrawal_request.id}",
    )

    withdrawal_request.status = WithdrawalRequest.Status.APPROVED
    withdrawal_request.admin_note = note
    withdrawal_request.reviewed_at = timezone.now()
    withdrawal_request.save(update_fields=["status", "admin_note", "reviewed_at"])

    return withdrawal_request


@transaction.atomic
def reject_withdrawal_request(withdrawal_request, admin_user, note=""):
    """Reject a withdrawal request."""
    if withdrawal_request.status != WithdrawalRequest.Status.PENDING:
        raise ValueError("Only pending requests can be rejected.")

    withdrawal_request.status = WithdrawalRequest.Status.REJECTED
    withdrawal_request.admin_note = note
    withdrawal_request.reviewed_at = timezone.now()
    withdrawal_request.save(update_fields=["status", "admin_note", "reviewed_at"])

    return withdrawal_request
