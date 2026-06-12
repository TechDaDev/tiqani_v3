"""
Dealership financial services — formulas, recharge/cashout logic, ledger updates.
"""

import hashlib
import secrets
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.db import transaction, IntegrityError
from django.db.models import Sum, Q
from django.utils import timezone
from django.conf import settings

from .models import (
    DealershipProfile,
    DealershipGuarantee,
    DealershipRechargeFeeConfig,
    DealershipClientRecharge,
    DealershipClientCashout,
    DealershipCreditLedger,
    DealershipSettlement,
)

logger = logging.getLogger(__name__)

FEE_PRECISION = Decimal("0.01")


def _quantize(val):
    return val.quantize(FEE_PRECISION, rounding=ROUND_HALF_UP)


# =====================================================================
# Financial formulas
# =====================================================================

def calculate_total_guarantee(dealership):
    """
    Sum of all verified guarantee amounts for a dealership.
    """
    result = DealershipGuarantee.objects.filter(
        dealership=dealership,
        status=DealershipGuarantee.Status.VERIFIED,
    ).aggregate(
        total=Sum('total_guarantee_amount'),
    )
    return result['total'] or Decimal('0.00')


def calculate_usable_credit_limit(dealership):
    """
    usable_credit_limit = total_verified_guarantee * usage_limit_percent / 100
    """
    total_guarantee = calculate_total_guarantee(dealership)
    limit_pct = dealership.usage_limit_percent
    return _quantize(total_guarantee * limit_pct / Decimal('100'))


def calculate_net_exposure(dealership):
    """
    net_exposure =
      + total_completed_recharges
      - total_completed_cashouts
      - settlements_paid_to_platform
      - settlements_paid_by_platform
    """
    recharges = DealershipClientRecharge.objects.filter(
        dealership=dealership,
        status=DealershipClientRecharge.Status.COMPLETED,
    ).aggregate(total=Sum('dealership_exposure_amount'))['total'] or Decimal('0.00')

    cashouts = DealershipClientCashout.objects.filter(
        dealership=dealership,
        status=DealershipClientCashout.Status.COMPLETED,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    settlements_to_platform = DealershipSettlement.objects.filter(
        dealership=dealership,
        status=DealershipSettlement.Status.COMPLETED,
        direction=DealershipSettlement.Direction.DEALERSHIP_OWES_PLATFORM,
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')

    settlements_from_platform = DealershipSettlement.objects.filter(
        dealership=dealership,
        status=DealershipSettlement.Status.COMPLETED,
        direction=DealershipSettlement.Direction.PLATFORM_OWES_DEALERSHIP,
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')

    return _quantize(recharges - cashouts - settlements_to_platform + settlements_from_platform)


def calculate_available_recharge_capacity(dealership):
    """
    available = usable_credit_limit - net_exposure
    """
    return _quantize(
        calculate_usable_credit_limit(dealership)
        - calculate_net_exposure(dealership)
    )


def calculate_recharge_fee(wallet_credit_amount=None, cash_received_amount=None, fee_config=None, fee_mode=None):
    """
    Calculate fee for a recharge transaction.

    Mode A (added_on_top):
        Input: wallet_credit_amount
        fee = wallet_credit_amount * fee_percent / 100
        cash_received = wallet_credit_amount + fee
        exposure = wallet_credit_amount

    Mode B (deducted_from_deposit):
        Input: cash_received_amount
        fee = cash_received_amount * fee_percent / 100
        wallet_credit = cash_received_amount - fee
        exposure = wallet_credit
    """
    if fee_config is None:
        fee_config = DealershipRechargeFeeConfig.get_active_config()

    fee_percent = fee_config.fee_percent

    if fee_mode is None:
        fee_mode = fee_config.default_fee_mode

    if fee_mode == DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP:
        if wallet_credit_amount is None:
            raise ValueError("wallet_credit_amount is required for added_on_top mode.")
        wallet_credit = _quantize(Decimal(str(wallet_credit_amount)))
        fee = _quantize(wallet_credit * fee_percent / Decimal('100'))
        cash_received = _quantize(wallet_credit + fee)
        exposure = wallet_credit
    elif fee_mode == DealershipRechargeFeeConfig.FeeMode.DEDUCTED_FROM_DEPOSIT:
        if cash_received_amount is None:
            raise ValueError("cash_received_amount is required for deducted_from_deposit mode.")
        cash_received = _quantize(Decimal(str(cash_received_amount)))
        fee = _quantize(cash_received * fee_percent / Decimal('100'))
        wallet_credit = _quantize(cash_received - fee)
        exposure = wallet_credit
    else:
        raise ValueError(f"Unknown fee_mode: {fee_mode}")

    # Apply min/max fee caps
    if fee_config.minimum_fee_amount is not None and fee < fee_config.minimum_fee_amount:
        fee = fee_config.minimum_fee_amount
    if fee_config.maximum_fee_amount is not None and fee > fee_config.maximum_fee_amount:
        fee = fee_config.maximum_fee_amount

    # Recalculate if fee cap changed amounts
    if fee_mode == DealershipRechargeFeeConfig.FeeMode.ADDED_ON_TOP:
        cash_received = _quantize(wallet_credit + fee)
        exposure = wallet_credit
    elif fee_mode == DealershipRechargeFeeConfig.FeeMode.DEDUCTED_FROM_DEPOSIT:
        wallet_credit = _quantize(cash_received - fee)
        if wallet_credit < 0:
            wallet_credit = Decimal('0.00')
        exposure = wallet_credit

    return {
        'fee_percent': fee_percent,
        'fee_mode': fee_mode,
        'cash_received_amount': cash_received,
        'wallet_credit_amount': wallet_credit,
        'dealership_fee_amount': fee,
        'dealership_exposure_amount': exposure,
    }


def should_lock_dealership(dealership, additional_exposure=Decimal('0.00')):
    """
    Check if net_exposure + additional_exposure >= usable_credit_limit.
    Returns (should_lock, net_exposure, usable_limit).
    """
    net = calculate_net_exposure(dealership)
    limit = calculate_usable_credit_limit(dealership)
    total = _quantize(net + additional_exposure)
    if limit <= Decimal('0.00'):
        return True, net, limit
    return total >= limit, net, limit


# =====================================================================
# Recharge creation
# =====================================================================

@transaction.atomic
def create_recharge(dealership, client, fee_mode, wallet_credit_amount=None,
                    cash_received_amount=None, created_by=None, idempotency_key=None,
                    proof_file=None):
    """
    Create a dealership client recharge and update client wallet.

    Returns (recharge_obj, created).
    If idempotency_key is provided and exists, returns (existing_obj, False).
    """
    # Check idempotency
    if idempotency_key:
        existing = DealershipClientRecharge.objects.filter(
            dealership=dealership,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing, False

    # Validate dealership
    if not dealership.is_operational:
        raise ValueError("Dealership is not operational.")
    if not dealership.recharge_enabled:
        raise ValueError("Dealership recharge is disabled.")
    if dealership.financially_locked:
        raise ValueError("Dealership is financially locked.")

    fee_config = DealershipRechargeFeeConfig.get_active_config()
    calc = calculate_recharge_fee(
        wallet_credit_amount=wallet_credit_amount,
        cash_received_amount=cash_received_amount,
        fee_config=fee_config,
        fee_mode=fee_mode,
    )

    # Check capacity
    available = calculate_available_recharge_capacity(dealership)
    if calc['dealership_exposure_amount'] > available:
        raise ValueError(
            f"Insufficient recharge capacity. Available: {available}, "
            f"Requested: {calc['dealership_exposure_amount']}"
        )

    # Check lock rule
    will_lock, net_exp, usable_limit = should_lock_dealership(
        dealership, calc['dealership_exposure_amount']
    )

    # Create recharge record
    recharge = DealershipClientRecharge.objects.create(
        dealership=dealership,
        client=client,
        fee_mode=fee_mode,
        fee_percent=calc['fee_percent'],
        cash_received_amount=calc['cash_received_amount'],
        wallet_credit_amount=calc['wallet_credit_amount'],
        dealership_fee_amount=calc['dealership_fee_amount'],
        dealership_exposure_amount=calc['dealership_exposure_amount'],
        status=DealershipClientRecharge.Status.COMPLETED,
        receipt_number=_generate_receipt_number(),
        proof_file=proof_file,
        idempotency_key=idempotency_key,
        created_by=created_by or dealership.user,
    )

    # Update client wallet (select_for_update to prevent race conditions)
    from wallet.models import Wallet, WalletTransaction
    wallet = Wallet.objects.select_for_update().get(user=client)
    wallet.balance += calc['wallet_credit_amount']
    wallet.save(update_fields=['balance'])

    # Create wallet transaction
    txn = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.Type.DEPOSIT,
        amount=calc['wallet_credit_amount'],
        description=(
            f"Dealership recharge from {dealership.business_name} — "
            f"receipt {recharge.receipt_number}"
        ),
    )
    recharge.wallet_transaction = txn
    recharge.completed_at = timezone.now()
    recharge.save(update_fields=['wallet_transaction', 'completed_at'])

    # Create ledger entry
    ledger = DealershipCreditLedger.objects.create(
        dealership=dealership,
        transaction_type=DealershipCreditLedger.TransactionType.CLIENT_RECHARGE,
        amount=calc['dealership_exposure_amount'],
        balance_after=calculate_net_exposure(dealership),
        reference_type='dealership_recharge',
        reference_id=recharge.id,
        created_by=created_by or dealership.user,
        notes=f"Recharge {calc['wallet_credit_amount']} IQD to {client.username}",
    )

    # Check and apply financial lock
    if will_lock:
        dealership.financially_locked = True
        dealership.save(update_fields=['financially_locked'])

    # Notifications
    _notify_recharge_completed(recharge, dealership, client)
    if will_lock:
        _notify_dealership_locked(dealership)

    return recharge, True


# =====================================================================
# Cash-out flow
# =====================================================================

def generate_confirmation_code():
    """Generate a 6-digit confirmation code."""
    return str(secrets.randbelow(900000) + 100000)


def hash_confirmation_code(code):
    """SHA-256 hash of confirmation code."""
    return hashlib.sha256(code.encode()).hexdigest()


@transaction.atomic
def create_cashout(dealership, client, amount, idempotency_key=None):
    """
    Create a cash-out request (client initiates). Returns (cashout_obj, created).
    Does NOT deduct wallet yet — deduction happens at confirmation.
    """
    if idempotency_key:
        existing = DealershipClientCashout.objects.filter(
            dealership=dealership,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing, False

    # Validate
    if not dealership.is_operational:
        raise ValueError("Dealership is not operational.")
    if not dealership.cashout_enabled:
        raise ValueError("Dealership cash-out is disabled.")

    amount = _quantize(Decimal(str(amount)))
    if amount <= Decimal('0.00'):
        raise ValueError("Cash-out amount must be positive.")

    # Check client wallet balance
    from wallet.models import Wallet
    wallet = Wallet.objects.select_for_update().get(user=client)
    if wallet.balance < amount:
        raise ValueError(
            f"Insufficient wallet balance. You have {wallet.balance} "
            f"but requested {amount}."
        )

    # Check single cashout limit
    if dealership.single_cashout_limit and amount > dealership.single_cashout_limit:
        raise ValueError(
            f"Amount exceeds single cash-out limit of {dealership.single_cashout_limit}."
        )

    # Check daily limit
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_total = DealershipClientCashout.objects.filter(
        dealership=dealership,
        status__in=[DealershipClientCashout.Status.COMPLETED, DealershipClientCashout.Status.CODE_ISSUED],
        created_at__gte=today_start,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    if dealership.daily_cashout_limit and (daily_total + amount) > dealership.daily_cashout_limit:
        raise ValueError(
            f"Amount exceeds daily cash-out limit of {dealership.daily_cashout_limit}. "
            f"Daily used: {daily_total}."
        )

    # Generate confirmation code
    code = generate_confirmation_code()
    code_hash = hash_confirmation_code(code)
    code_expires_at = timezone.now() + timedelta(minutes=10)

    cashout = DealershipClientCashout.objects.create(
        dealership=dealership,
        client=client,
        amount=amount,
        status=DealershipClientCashout.Status.CODE_ISSUED,
        confirmation_code_hash=code_hash,
        code_expires_at=code_expires_at,
        idempotency_key=idempotency_key,
    )

    # Send code to client (console fallback for dev)
    _send_cashout_code(client, code, cashout)

    # Notify
    _notify_cashout_requested(cashout, dealership, client)

    return cashout, True


@transaction.atomic
def confirm_cashout(cashout, confirming_user):
    """
    Confirm a cash-out by the dealership (dealership has given client the cash).
    Deducts client wallet, creates ledger entry, updates exposure.
    """
    if cashout.status != DealershipClientCashout.Status.CODE_ISSUED:
        raise ValueError(f"Cannot confirm cash-out in status: {cashout.status}")

    if cashout.dealership.user != confirming_user:
        raise ValueError("Only the owning dealership can confirm this cash-out.")

    if cashout.code_expires_at and timezone.now() > cashout.code_expires_at:
        cashout.status = DealershipClientCashout.Status.EXPIRED
        cashout.save(update_fields=['status'])
        raise ValueError("Confirmation code has expired. Please request a new cash-out.")

    dealership = cashout.dealership
    client = cashout.client
    amount = cashout.amount

    # Verify dealership operational
    if not dealership.is_operational:
        raise ValueError("Dealership is not operational.")

    # Re-check client wallet balance
    from wallet.models import Wallet, WalletTransaction
    wallet = Wallet.objects.select_for_update().get(user=client)
    if wallet.balance < amount:
        cashout.status = DealershipClientCashout.Status.CANCELLED
        cashout.save(update_fields=['status'])
        raise ValueError(
            f"Insufficient wallet balance at confirmation. "
            f"Balance: {wallet.balance}, Requested: {amount}."
        )

    # Deduct wallet
    wallet.balance -= amount
    wallet.save(update_fields=['balance'])

    # Create wallet transaction
    txn = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=WalletTransaction.Type.WITHDRAWAL,
        amount=amount,
        description=(
            f"Cash-out to dealership {dealership.business_name} — "
            f"client {client.username}"
        ),
    )

    # Update cashout
    cashout.status = DealershipClientCashout.Status.COMPLETED
    cashout.completed_at = timezone.now()
    cashout.wallet_transaction = txn
    cashout.save(update_fields=['status', 'completed_at', 'wallet_transaction'])

    # Create ledger entry (cash-out reduces exposure)
    ledger = DealershipCreditLedger.objects.create(
        dealership=dealership,
        transaction_type=DealershipCreditLedger.TransactionType.CLIENT_CASHOUT,
        amount=-amount,  # Negative — reduces exposure
        balance_after=calculate_net_exposure(dealership),
        reference_type='dealership_cashout',
        reference_id=cashout.id,
        created_by=confirming_user,
        notes=f"Cash-out {amount} IQD by {client.username}",
    )

    cashout.dealership_ledger_entry = ledger
    cashout.save(update_fields=['dealership_ledger_entry'])

    # If dealership was financially locked and exposure dropped below limit, unlock
    _update_financial_lock_after_cashout(dealership)

    # Notifications
    _notify_cashout_completed(cashout, dealership, client)

    return cashout


def _update_financial_lock_after_cashout(dealership):
    """If net exposure drops below limit, unlock the dealership."""
    if dealership.financially_locked:
        net = calculate_net_exposure(dealership)
        limit = calculate_usable_credit_limit(dealership)
        if limit > Decimal('0.00') and net < limit:
            dealership.financially_locked = False
            dealership.save(update_fields=['financially_locked'])


def _verify_confirmation_code(cashout, code):
    """Verify a confirmation code against stored hash."""
    code_hash = hash_confirmation_code(code)
    return cashout.confirmation_code_hash == code_hash


def verify_cashout_code(cashout, confirmation_code, verifying_user):
    """Verify cash-out confirmation code (without confirming)."""
    if cashout.dealership.user != verifying_user:
        raise ValueError("Only the owning dealership can verify this cash-out.")
    if cashout.code_expires_at and timezone.now() > cashout.code_expires_at:
        raise ValueError("Confirmation code has expired.")
    if not _verify_confirmation_code(cashout, confirmation_code):
        raise ValueError("Invalid confirmation code.")
    return True


# =====================================================================
# Settlement
# =====================================================================

@transaction.atomic
def generate_settlement(dealership, period_start, period_end, created_by=None):
    """
    Generate a settlement for a dealership for a given period.
    Calculates net position and direction.
    """
    # Sum completed recharges in period
    recharges = DealershipClientRecharge.objects.filter(
        dealership=dealership,
        status=DealershipClientRecharge.Status.COMPLETED,
        completed_at__date__gte=period_start,
        completed_at__date__lte=period_end,
    ).aggregate(total=Sum('dealership_exposure_amount'))['total'] or Decimal('0.00')

    # Sum completed cashouts in period
    cashouts = DealershipClientCashout.objects.filter(
        dealership=dealership,
        status=DealershipClientCashout.Status.COMPLETED,
        completed_at__date__gte=period_start,
        completed_at__date__lte=period_end,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    net = _quantize(recharges - cashouts)

    if net > Decimal('0.00'):
        direction = DealershipSettlement.Direction.DEALERSHIP_OWES_PLATFORM
    elif net < Decimal('0.00'):
        direction = DealershipSettlement.Direction.PLATFORM_OWES_DEALERSHIP
        net = abs(net)
    else:
        direction = DealershipSettlement.Direction.SETTLED_ZERO

    settlement = DealershipSettlement.objects.create(
        dealership=dealership,
        period_start=period_start,
        period_end=period_end,
        total_recharges=recharges,
        total_cashouts=cashouts,
        net_amount=net,
        direction=direction,
        status=DealershipSettlement.Status.DRAFT,
        created_by=created_by,
    )
    return settlement


@transaction.atomic
def complete_settlement(settlement, settled_by):
    """
    Complete a settlement. Updates ledger and unlocks or locks dealership accordingly.
    """
    if settlement.status != DealershipSettlement.Status.DRAFT:
        raise ValueError(f"Cannot complete settlement in status: {settlement.status}")

    settlement.status = DealershipSettlement.Status.COMPLETED
    settlement.settled_by = settled_by
    settlement.settled_at = timezone.now()
    settlement.save(update_fields=['status', 'settled_by', 'settled_at'])

    # Create ledger entry
    ledger_type = (
        DealershipCreditLedger.TransactionType.SETTLEMENT_PAID_TO_PLATFORM
        if settlement.direction == DealershipSettlement.Direction.DEALERSHIP_OWES_PLATFORM
        else DealershipCreditLedger.TransactionType.SETTLEMENT_PAID_BY_PLATFORM
    )

    amount = (
        -settlement.net_amount
        if settlement.direction == DealershipSettlement.Direction.DEALERSHIP_OWES_PLATFORM
        else settlement.net_amount
    )

    DealershipCreditLedger.objects.create(
        dealership=settlement.dealership,
        transaction_type=ledger_type,
        amount=amount,
        balance_after=calculate_net_exposure(settlement.dealership),
        reference_type='dealership_settlement',
        reference_id=settlement.id,
        created_by=settled_by,
        notes=f"Settlement {settlement.period_start} → {settlement.period_end} completed",
    )

    # Update financial lock
    _update_financial_lock_after_cashout(settlement.dealership)

    return settlement


# =====================================================================
# Dashboard metrics
# =====================================================================

def get_dealership_metrics():
    """Aggregated dealership metrics for admin dashboard."""
    from django.db.models import Count

    total = DealershipProfile.objects.count()
    active = DealershipProfile.objects.filter(active=True, suspended=False, blocked=False).count()
    pending = DealershipProfile.objects.filter(status=DealershipProfile.Status.PENDING_REVIEW).count()
    locked = DealershipProfile.objects.filter(financially_locked=True).count()

    # Guarantees
    guarantee_total = DealershipGuarantee.objects.filter(
        status=DealershipGuarantee.Status.VERIFIED,
    ).aggregate(total=Sum('total_guarantee_amount'))['total'] or Decimal('0.00')

    # These are expensive to compute per dealership, so we do a rough estimate
    # Based on verified guarantees and usage limits
    all_dealerships = DealershipProfile.objects.filter(
        active=True, suspended=False, blocked=False
    )
    total_net_exposure = Decimal('0.00')
    total_available_capacity = Decimal('0.00')

    for d in all_dealerships:
        try:
            total_net_exposure += calculate_net_exposure(d)
            total_available_capacity += calculate_available_recharge_capacity(d)
        except Exception:
            pass

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    today_recharges = DealershipClientRecharge.objects.filter(
        status=DealershipClientRecharge.Status.COMPLETED,
        completed_at__gte=today_start,
    ).aggregate(total=Sum('wallet_credit_amount'))['total'] or Decimal('0.00')

    today_cashouts = DealershipClientCashout.objects.filter(
        status=DealershipClientCashout.Status.COMPLETED,
        completed_at__gte=today_start,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    pending_settlements = DealershipSettlement.objects.filter(
        status__in=[DealershipSettlement.Status.DRAFT, DealershipSettlement.Status.PENDING],
    ).count()

    return {
        'total_dealerships': total,
        'active_dealerships': active,
        'pending_dealerships': pending,
        'financially_locked_dealerships': locked,
        'total_verified_guarantees': str(guarantee_total),
        'total_net_exposure': str(total_net_exposure),
        'total_available_recharge_capacity': str(total_available_capacity),
        'today_recharges_total': str(today_recharges),
        'today_cashouts_total': str(today_cashouts),
        'pending_settlements': pending_settlements,
    }


# =====================================================================
# Helpers
# =====================================================================

def _generate_receipt_number():
    """Generate a unique receipt number."""
    import uuid
    return f"DR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def _send_cashout_code(client, code, cashout):
    """
    Send confirmation code to client.
    Uses existing notification system or falls back to console in dev.
    """
    try:
        from notification.services import create_notification
        from notification.models import Notification
        create_notification(
            recipient=client,
            notification_type=Notification.Type.SYSTEM,
            title="Cash-out Confirmation Code",
            message=(
                f"Your cash-out of {cashout.amount} IQD to "
                f"{cashout.dealership.business_name} needs confirmation. "
                f"Code: {code} (expires in 10 minutes)"
            ),
            actor=None,
            target_type='dealership_cashout',
            target_id=cashout.id,
        )
    except Exception as exc:
        logger.warning("Failed to send cashout code via notification: %s", exc)
        logger.info("Cashout code for %s: %s", client.username, code)


def _notify_recharge_completed(recharge, dealership, client):
    """Send notifications for completed recharge."""
    try:
        from notification.services import create_notification, create_activity
        from notification.models import Notification

        # Notify client
        create_notification(
            recipient=client,
            notification_type=Notification.Type.WALLET_TRANSACTION,
            title="Wallet Recharged",
            message=(
                f"Your wallet has been recharged with "
                f"{recharge.wallet_credit_amount} IQD by {dealership.business_name}."
            ),
            actor=dealership.user,
            target_type='dealership_recharge',
            target_id=recharge.id,
        )
        # Notify dealership
        create_notification(
            recipient=dealership.user,
            notification_type=Notification.Type.WALLET_TRANSACTION,
            title="Recharge Completed",
            message=(
                f"Successfully recharged {recharge.wallet_credit_amount} IQD "
                f"to {client.username}."
            ),
            actor=dealership.user,
            target_type='dealership_recharge',
            target_id=recharge.id,
        )
        # Activity log
        create_activity(
            verb='recharge_completed',
            actor=dealership.user,
            target_type='dealership_recharge',
            target_id=recharge.id,
            target_repr=f"Recharge {recharge.wallet_credit_amount} IQD → {client.username}",
            audience='admin',
        )
    except Exception as exc:
        logger.warning("Notification error (recharge completed): %s", exc)


def _notify_dealership_locked(dealership):
    """Notify dealership and finance admins about financial lock."""
    try:
        from notification.services import create_notification, create_notifications_bulk, create_activity
        from notification.models import Notification

        # Notify dealership
        create_notification(
            recipient=dealership.user,
            notification_type=Notification.Type.SYSTEM,
            title="Dealership Financially Locked",
            message=(
                f"Your dealership '{dealership.business_name}' has been "
                f"financially locked because net exposure reached the credit limit."
            ),
            target_type='dealership_profile',
            target_id=dealership.id,
        )
        # Notify finance admins
        from django.contrib.auth import get_user_model
        User = get_user_model()
        finance_admins = User.objects.filter(
            is_staff=True,
            admin_profile__role__in=['system_admin', 'finance_admin'],
        )
        create_notifications_bulk(
            finance_admins,
            notification_type=Notification.Type.SYSTEM,
            title="Dealership Financially Locked",
            message=(
                f"Dealership '{dealership.business_name}' has been "
                f"financially locked."
            ),
            actor=dealership.user,
            target_type='dealership_profile',
            target_id=dealership.id,
        )
        create_activity(
            verb='dealership_locked',
            actor=None,
            target_type='dealership_profile',
            target_id=dealership.id,
            target_repr=f"Dealership {dealership.business_name} financially locked",
            audience='admin',
        )
    except Exception as exc:
        logger.warning("Notification error (dealership locked): %s", exc)


def _notify_cashout_requested(cashout, dealership, client):
    """Send notifications for cash-out request."""
    try:
        from notification.services import create_notification, create_activity
        from notification.models import Notification

        # Notify client
        create_notification(
            recipient=client,
            notification_type=Notification.Type.WALLET_TRANSACTION,
            title="Cash-out Requested",
            message=(
                f"A cash-out of {cashout.amount} IQD to "
                f"{dealership.business_name} has been created. "
                f"Please visit the dealership to complete."
            ),
            actor=client,
            target_type='dealership_cashout',
            target_id=cashout.id,
        )
        # Notify dealership
        create_notification(
            recipient=dealership.user,
            notification_type=Notification.Type.WALLET_TRANSACTION,
            title="New Cash-out Request",
            message=(
                f"{client.username} has requested a cash-out of "
                f"{cashout.amount} IQD."
            ),
            actor=client,
            target_type='dealership_cashout',
            target_id=cashout.id,
        )
        create_activity(
            verb='cashout_requested',
            actor=client,
            target_type='dealership_cashout',
            target_id=cashout.id,
            target_repr=f"Cash-out {cashout.amount} IQD by {client.username}",
            audience='admin',
        )
    except Exception as exc:
        logger.warning("Notification error (cashout requested): %s", exc)


def _notify_cashout_completed(cashout, dealership, client):
    """Send notifications for completed cash-out."""
    try:
        from notification.services import create_notification, create_activity
        from notification.models import Notification

        # Notify client
        create_notification(
            recipient=client,
            notification_type=Notification.Type.WALLET_TRANSACTION,
            title="Cash-out Completed",
            message=(
                f"Your cash-out of {cashout.amount} IQD to "
                f"{dealership.business_name} has been completed."
            ),
            actor=dealership.user,
            target_type='dealership_cashout',
            target_id=cashout.id,
        )
        # Notify dealership
        create_notification(
            recipient=dealership.user,
            notification_type=Notification.Type.WALLET_TRANSACTION,
            title="Cash-out Completed",
            message=(
                f"Cash-out of {cashout.amount} IQD for {client.username} "
                f"has been completed."
            ),
            actor=dealership.user,
            target_type='dealership_cashout',
            target_id=cashout.id,
        )
        create_activity(
            verb='cashout_completed',
            actor=dealership.user,
            target_type='dealership_cashout',
            target_id=cashout.id,
            target_repr=f"Cash-out {cashout.amount} IQD by {client.username} completed",
            audience='admin',
        )
    except Exception as exc:
        logger.warning("Notification error (cashout completed): %s", exc)
