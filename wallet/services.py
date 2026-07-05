"""Fee calculation, payment intent, contract funding, and withdrawal services."""

from decimal import Decimal, ROUND_HALF_UP
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings

from .models import (
    PlatformFeeConfig,
    ContractPaymentBreakdown,
    PlatformEarning,
    PaymentIntent,
    WalletRechargeRequest,
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

    txn = WalletTransaction.objects.create(
        wallet=wallet,
        contract=payment_intent.contract,
        transaction_type=WalletTransaction.Type.DEPOSIT,
        amount=payment_intent.amount,
        description=f"Deposit via {payment_intent.get_purpose_display()} – {payment_intent.id}",
    )

    # Notify
    from notification.services import notify_payment_intent_paid, notify_wallet_transaction
    try:
        notify_payment_intent_paid(payment_intent)
        notify_wallet_transaction(txn)
    except Exception:
        pass

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


# ── Phase 9: Enhanced Withdrawal Service ──


def get_available_balance(wallet):
    """
    Calculate available balance: wallet.balance - SUM(pending + approved withdrawal amounts).
    """
    reserved = WithdrawalRequest.objects.filter(
        wallet=wallet,
        status__in=[
            WithdrawalRequest.Status.PENDING,
            WithdrawalRequest.Status.APPROVED,
            WithdrawalRequest.Status.PROCESSING,
        ],
    ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

    available = wallet.balance - reserved
    if available < 0:
        available = Decimal("0.00")
    return _quantize(available)


def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


@transaction.atomic
def create_wallet_recharge_request(user, amount, receipt_file, note=""):
    amount = _quantize(Decimal(str(amount)))
    if amount <= 0:
        raise ValueError("Recharge amount must be positive.")
    if not receipt_file:
        raise ValueError("Receipt file is required.")
    if WalletRechargeRequest.objects.filter(
        user=user,
        status=WalletRechargeRequest.Status.PENDING_REVIEW,
    ).exists():
        raise ValueError("You already have a pending wallet recharge request.")

    wallet = get_or_create_wallet(user)
    request_obj = WalletRechargeRequest.objects.create(
        user=user,
        wallet=wallet,
        amount=amount,
        currency="IQD",
        note=(note or "").strip(),
        receipt_file=receipt_file,
        original_filename=getattr(receipt_file, "name", "") or "",
        file_size=getattr(receipt_file, "size", None),
        mime_type=getattr(receipt_file, "content_type", "") or "",
    )

    try:
        from notification.services import create_activity, notify_admins

        create_activity(
            "wallet_recharge_requested",
            actor=user,
            target_type="wallet_recharge_request",
            target_id=request_obj.id,
            target_repr=f"{user.username} requested {amount} IQD wallet recharge",
            audience="admin",
            metadata={
                "amount": str(amount),
                "status": request_obj.status,
                "source_service": "wallet",
            },
        )
        notify_admins(
            "wallet_transaction",
            "Wallet recharge request",
            f"{user.username} submitted a wallet recharge request.",
            actor=user,
            target_type="wallet_recharge_request",
            target_id=request_obj.id,
            metadata={"amount": str(amount), "status": request_obj.status},
        )
    except Exception:
        pass

    return request_obj


@transaction.atomic
def approve_wallet_recharge_request(recharge_request, reviewer, review_note=""):
    locked_req = WalletRechargeRequest.objects.select_for_update().get(id=recharge_request.id)
    if locked_req.status == WalletRechargeRequest.Status.APPROVED and locked_req.approved_transaction_id:
        return locked_req
    if locked_req.status != WalletRechargeRequest.Status.PENDING_REVIEW:
        raise ValueError("Only pending wallet recharge requests can be approved.")

    wallet = Wallet.objects.select_for_update().get(id=locked_req.wallet_id)
    wallet.balance = _quantize(wallet.balance + locked_req.amount)
    wallet.save(update_fields=["balance", "updated_at"])

    txn = WalletTransaction.objects.create(
        wallet=wallet,
        contract=None,
        transaction_type=WalletTransaction.Type.DEPOSIT,
        amount=locked_req.amount,
        description=f"Wallet recharge approved from receipt request {locked_req.id}",
    )

    locked_req.status = WalletRechargeRequest.Status.APPROVED
    locked_req.reviewed_by = reviewer
    locked_req.reviewed_at = timezone.now()
    locked_req.review_note = (review_note or "").strip()
    locked_req.approved_transaction = txn
    locked_req.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "approved_transaction",
            "updated_at",
        ]
    )

    try:
        from notification.services import create_activity, create_notification, notify_wallet_transaction

        create_activity(
            "wallet_recharge_approved",
            actor=reviewer,
            target_type="wallet_recharge_request",
            target_id=locked_req.id,
            target_repr=f"Approved wallet recharge {locked_req.id}",
            audience="admin",
            metadata={
                "amount": str(locked_req.amount),
                "previous_state": {"status": WalletRechargeRequest.Status.PENDING_REVIEW},
                "new_state": {"status": locked_req.status, "transaction_id": str(txn.id)},
                "reason": locked_req.review_note,
                "source_service": "wallet",
            },
        )
        create_notification(
            locked_req.user,
            "wallet_transaction",
            "Wallet recharge approved",
            f"Your wallet was credited with {locked_req.amount} {locked_req.currency}.",
            actor=reviewer,
            target_type="wallet_recharge_request",
            target_id=locked_req.id,
            metadata={"amount": str(locked_req.amount), "transaction_id": str(txn.id)},
        )
        notify_wallet_transaction(txn)
    except Exception:
        pass

    return locked_req


@transaction.atomic
def reject_wallet_recharge_request(recharge_request, reviewer, review_note=""):
    note = (review_note or "").strip()
    if not note:
        raise ValueError("Review note is required when rejecting a wallet recharge request.")

    locked_req = WalletRechargeRequest.objects.select_for_update().get(id=recharge_request.id)
    if locked_req.status != WalletRechargeRequest.Status.PENDING_REVIEW:
        raise ValueError("Only pending wallet recharge requests can be rejected.")

    locked_req.status = WalletRechargeRequest.Status.REJECTED
    locked_req.reviewed_by = reviewer
    locked_req.reviewed_at = timezone.now()
    locked_req.review_note = note
    locked_req.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"]
    )

    try:
        from notification.services import create_activity, create_notification

        create_activity(
            "wallet_recharge_rejected",
            actor=reviewer,
            target_type="wallet_recharge_request",
            target_id=locked_req.id,
            target_repr=f"Rejected wallet recharge {locked_req.id}",
            audience="admin",
            metadata={
                "amount": str(locked_req.amount),
                "previous_state": {"status": WalletRechargeRequest.Status.PENDING_REVIEW},
                "new_state": {"status": locked_req.status},
                "reason": note,
                "source_service": "wallet",
            },
        )
        create_notification(
            locked_req.user,
            "wallet_transaction",
            "Wallet recharge rejected",
            note,
            actor=reviewer,
            target_type="wallet_recharge_request",
            target_id=locked_req.id,
            metadata={"amount": str(locked_req.amount), "status": locked_req.status},
        )
    except Exception:
        pass

    return locked_req


@transaction.atomic
def cancel_wallet_recharge_request(recharge_request, user):
    locked_req = WalletRechargeRequest.objects.select_for_update().get(id=recharge_request.id)
    if locked_req.user_id != user.id:
        raise ValueError("You cannot cancel this wallet recharge request.")
    if locked_req.status != WalletRechargeRequest.Status.PENDING_REVIEW:
        raise ValueError("Only pending wallet recharge requests can be cancelled.")

    locked_req.status = WalletRechargeRequest.Status.CANCELLED
    locked_req.save(update_fields=["status", "updated_at"])

    try:
        from notification.services import create_activity

        create_activity(
            "wallet_recharge_cancelled",
            actor=user,
            target_type="wallet_recharge_request",
            target_id=locked_req.id,
            target_repr=f"Cancelled wallet recharge {locked_req.id}",
            audience="admin",
            metadata={
                "amount": str(locked_req.amount),
                "previous_state": {"status": WalletRechargeRequest.Status.PENDING_REVIEW},
                "new_state": {"status": locked_req.status},
                "source_service": "wallet",
            },
        )
    except Exception:
        pass

    return locked_req


WITHDRAWAL_MINIMUM = Decimal("1000.00")


@transaction.atomic
def create_withdrawal_request(user, amount, method="", notes=""):
    """Create a withdrawal request with available-balance check."""
    wallet = Wallet.objects.select_for_update().get(user=user)
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")

    if amount < WITHDRAWAL_MINIMUM:
        raise ValueError(
            f"Minimum withdrawal amount is {WITHDRAWAL_MINIMUM}. Requested: {amount}."
        )

    available = get_available_balance(wallet)
    if amount > available:
        raise ValueError(
            f"Insufficient available balance. You have {available} available but requested {amount}."
        )

    req = WithdrawalRequest.objects.create(
        user=user,
        wallet=wallet,
        amount=amount,
        requested_method=method,
        notes=notes,
    )

    from notification.services import notify_withdrawal_requested
    try:
        notify_withdrawal_requested(req, user)
    except Exception:
        pass

    return req


@transaction.atomic
def approve_withdrawal_request(withdrawal_request, admin_user, note=""):
    """Approve a withdrawal. Balance deduction occurs at processing, not approval."""
    if withdrawal_request.status != WithdrawalRequest.Status.PENDING:
        raise ValueError("Only pending requests can be approved.")

    withdrawal_request.status = WithdrawalRequest.Status.APPROVED
    withdrawal_request.admin_note = note
    withdrawal_request.reviewed_at = timezone.now()
    withdrawal_request.save(update_fields=["status", "admin_note", "reviewed_at"])

    from notification.services import notify_withdrawal_approved
    try:
        notify_withdrawal_approved(withdrawal_request, admin_user)
    except Exception:
        pass

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

    from notification.services import notify_withdrawal_rejected
    try:
        notify_withdrawal_rejected(withdrawal_request, admin_user)
    except Exception:
        pass

    return withdrawal_request


@transaction.atomic
def process_withdrawal_request(withdrawal_request, admin_user):
    """
    Move withdrawal from APPROVED to PROCESSING.
    Deduct wallet balance. Create withdrawal transaction.
    """
    if withdrawal_request.status != WithdrawalRequest.Status.APPROVED:
        raise ValueError("Only approved requests can be processed.")

    wallet = Wallet.objects.select_for_update().get(
        user=withdrawal_request.user
    )

    if wallet.balance < withdrawal_request.amount:
        raise ValueError("Insufficient balance for payout.")

    # Deduct wallet
    wallet.balance -= withdrawal_request.amount
    wallet.save(update_fields=["balance"])

    txn = WalletTransaction.objects.create(
        wallet=wallet,
        contract=None,
        transaction_type=WalletTransaction.Type.WITHDRAWAL,
        amount=withdrawal_request.amount,
        description=f"Withdrawal processing by {admin_user.username}: {withdrawal_request.id}",
    )

    withdrawal_request.status = WithdrawalRequest.Status.PROCESSING
    withdrawal_request.save(update_fields=["status"])

    return withdrawal_request


@transaction.atomic
def confirm_withdrawal_payout(withdrawal_request, admin_user, simulate_failure=False):
    """
    Complete a sandbox payout. Called after sandbox gateway confirms success.
    Deducts if not already deducted. Sets status to PAID or FAILED.
    """
    from .sandbox_payout_gateway import (
        is_sandbox_payout_enabled,
        sandbox_process_payout,
    )

    if not is_sandbox_payout_enabled():
        raise RuntimeError("Sandbox payout gateway is not enabled.")

    if withdrawal_request.status not in (
        WithdrawalRequest.Status.PROCESSING,
        WithdrawalRequest.Status.APPROVED,
    ):
        raise ValueError(
            f"Cannot process payout for status '{withdrawal_request.status}'."
        )

    # Ensure wallet deducted if still APPROVED (not yet processed)
    if withdrawal_request.status == WithdrawalRequest.Status.APPROVED:
        wallet = Wallet.objects.select_for_update().get(
            user=withdrawal_request.user
        )
        if wallet.balance < withdrawal_request.amount:
            raise ValueError("Insufficient balance.")
        wallet.balance -= withdrawal_request.amount
        wallet.save(update_fields=["balance"])
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.Type.WITHDRAWAL,
            amount=withdrawal_request.amount,
            description=f"Withdrawal payout by {admin_user.username}: {withdrawal_request.id}",
        )
        withdrawal_request.status = WithdrawalRequest.Status.PROCESSING
        withdrawal_request.save(update_fields=["status"])

    # Call sandbox gateway
    result = sandbox_process_payout(
        amount=withdrawal_request.amount,
        currency=withdrawal_request.currency,
        withdrawal_id=str(withdrawal_request.id),
        recipient_username=withdrawal_request.user.username,
        simulate_failure=simulate_failure,
    )

    if result["success"]:
        withdrawal_request.status = WithdrawalRequest.Status.PAID
        withdrawal_request.paid_at = timezone.now()
        withdrawal_request.failure_code = ""
        withdrawal_request.failure_message = ""
        withdrawal_request.save(
            update_fields=["status", "paid_at", "failure_code", "failure_message"]
        )

        from notification.services import notify_wallet_transaction
        try:
            last_txn = withdrawal_request.wallet.transactions.order_by("-created_at").first()
            if last_txn:
                notify_wallet_transaction(last_txn)
        except Exception:
            pass
    else:
        withdrawal_request.status = WithdrawalRequest.Status.FAILED
        withdrawal_request.failure_code = result.get("error_code", "unknown")
        withdrawal_request.failure_message = result.get("error_message", "Unknown error")
        withdrawal_request.save(
            update_fields=["status", "failure_code", "failure_message"]
        )

    return withdrawal_request


@transaction.atomic
def retry_failed_withdrawal(withdrawal_request, admin_user, simulate_failure=False):
    """Retry a failed payout."""
    if withdrawal_request.status != WithdrawalRequest.Status.FAILED:
        raise ValueError("Only failed requests can be retried.")

    # Reset to PROCESSING
    withdrawal_request.status = WithdrawalRequest.Status.PROCESSING
    withdrawal_request.failure_code = ""
    withdrawal_request.failure_message = ""
    withdrawal_request.save(update_fields=["status", "failure_code", "failure_message"])

    return confirm_withdrawal_payout(
        withdrawal_request, admin_user, simulate_failure=simulate_failure
    )


@transaction.atomic
def cancel_withdrawal_request(withdrawal_request, user):
    """Cancel a pending/approved withdrawal request. No balance effect since deducted at processing."""
    if withdrawal_request.status not in (
        WithdrawalRequest.Status.PENDING,
        WithdrawalRequest.Status.APPROVED,
    ):
        raise ValueError("Only pending or approved requests can be canceled.")

    if not user.is_staff and withdrawal_request.user != user:
        raise ValueError("You can only cancel your own withdrawal requests.")

    withdrawal_request.status = WithdrawalRequest.Status.CANCELED
    withdrawal_request.save(update_fields=["status"])

    return withdrawal_request

# ── Phase 7: Funding Eligibility, Intent Creation, Sandbox Confirm ──


def get_contract_funding_status(contract):
    """
    Derive funding status from PaymentIntent records.
    Returns one of: unfunded, pending, funded, failed.
    """
    if contract.status == "canceled":
        return "failed"
    intents = PaymentIntent.objects.filter(
        contract=contract,
        purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
    ).order_by("-created_at")
    if not intents.exists():
        return "unfunded"
    if intents.filter(status=PaymentIntent.Status.PAID).exists():
        return "funded"
    if intents.filter(status=PaymentIntent.Status.PENDING).exists():
        return "pending"
    if intents.filter(status=PaymentIntent.Status.FAILED).exists():
        return "failed"
    return "unfunded"


def check_funding_eligibility(contract, user):
    """
    Check if a contract is eligible for funding by a specific user.
    Returns (is_eligible: bool, reason: str|None).
    """
    if not hasattr(user, "client_profile") or contract.client.user_id != user.id:
        return False, "Only the contract client can initiate funding."
    if contract.status != "in_progress":
        return False, f"Contract status is '{contract.status}'; must be 'in_progress'."
    if not contract.agreed_amount or contract.agreed_amount <= 0:
        return False, "Contract has no agreed amount."
    funding_status = get_contract_funding_status(contract)
    if funding_status == "funded":
        return False, "Contract is already funded."
    if funding_status == "pending":
        return False, "A payment is already pending for this contract."
    return True, None


@transaction.atomic
def create_contract_payment_intent(contract, user):
    """
    Create a new CONTRACT_FUNDING PaymentIntent for an eligible contract.
    Idempotent: returns existing pending intent if one exists.
    """
    from .sandbox_gateway import SANDBOX_PROVIDER_NAME

    # Check for existing non-terminal intent FIRST (idempotency)
    existing = PaymentIntent.objects.filter(
        contract=contract,
        purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
    ).exclude(
        status__in=[PaymentIntent.Status.PAID, PaymentIntent.Status.CANCELED],
    ).select_for_update().first()
    if existing:
        return existing

    eligible, reason = check_funding_eligibility(contract, user)
    if not eligible:
        raise ValueError(reason)

    breakdown = ensure_contract_payment_breakdown(contract)
    amount = breakdown.client_total_amount
    provider = getattr(settings, "PAYMENT_PROVIDER", SANDBOX_PROVIDER_NAME)

    intent = PaymentIntent.objects.create(
        contract=contract,
        user=user,
        amount=amount,
        currency="IQD",
        purpose=PaymentIntent.Purpose.CONTRACT_FUNDING,
        provider=provider,
        status=PaymentIntent.Status.PENDING,
    )
    return intent


@transaction.atomic
def confirm_sandbox_payment(intent_id: str, simulate_failure: bool = False):
    """
    Confirm a sandbox payment intent.
    Only works when sandbox is enabled.
    """
    from .sandbox_gateway import is_sandbox_enabled, sandbox_confirm_payment

    if not is_sandbox_enabled():
        raise RuntimeError("Sandbox gateway is not enabled.")

    intent = PaymentIntent.objects.select_for_update().get(id=intent_id)

    if intent.status == PaymentIntent.Status.PAID:
        raise ValueError("Payment intent is already paid.")
    if intent.status not in (PaymentIntent.Status.PENDING, PaymentIntent.Status.FAILED):
        raise ValueError(f"Cannot confirm payment in status '{intent.status}'.")

    result = sandbox_confirm_payment(
        amount=intent.amount,
        currency=intent.currency,
        contract_reference=str(intent.contract.contract_reference),
        payment_intent_id=str(intent.id),
        simulate_failure=simulate_failure,
    )

    if not result["success"]:
        intent.status = PaymentIntent.Status.FAILED
        intent.metadata["failure_code"] = result.get("error_code", "unknown")
        intent.metadata["failure_message"] = result.get("error_message", "Payment failed.")
        intent.provider_reference = result.get("provider_reference", "")
        intent.save(update_fields=["status", "metadata", "provider_reference", "updated_at"])
        return intent, result

    intent.status = PaymentIntent.Status.PAID
    intent.paid_at = timezone.now()
    intent.provider_reference = result.get("provider_reference", "")
    intent.metadata["provider_event_id"] = result.get("provider_event_id")
    intent.save(update_fields=["status", "paid_at", "provider_reference", "metadata", "updated_at"])

    contract = intent.contract
    wallet = intent.user.wallet

    wallet.balance += intent.amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        contract=contract,
        transaction_type=WalletTransaction.Type.DEPOSIT,
        amount=intent.amount,
        description=f"Contract funding deposit – {contract.contract_reference} (sandbox)",
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        contract=contract,
        transaction_type=WalletTransaction.Type.ESCROW,
        amount=contract.agreed_amount,
        description=f"Escrow held for contract {contract.contract_reference}",
    )

    contract.escrow_amount = contract.agreed_amount
    contract.save(update_fields=["escrow_amount", "updated_at"])

    return intent, result
