"""
Dealership models — Profiles, Guarantees, Recharges, Cashouts, Ledger, Settlements, Idempotency.
"""

import uuid
import hashlib
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# DealershipProfile
# ---------------------------------------------------------------------------

class DealershipProfile(models.Model):
    """
    Extended profile for dealership users. Ties to a CustomUser with role='dealership'.
    Controls financial state: guarantees, limits, locks, suspensions.
    """

    class Status(models.TextChoices):
        PENDING_REVIEW = 'pending_review', _('Pending Review')
        ACTIVE = 'active', _('Active')
        SUSPENDED = 'suspended', _('Suspended')
        BLOCKED = 'blocked', _('Blocked')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='dealership_profile',
    )
    business_name = models.CharField(max_length=255, verbose_name=_("Business Name"))
    owner_name = models.CharField(max_length=255, verbose_name=_("Owner Name"))
    phone = models.CharField(max_length=50, verbose_name=_("Phone"))
    governorate = models.CharField(max_length=100, verbose_name=_("Governorate"))
    address = models.TextField(blank=True, verbose_name=_("Address"))

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING_REVIEW, db_index=True,
        verbose_name=_("Status"),
    )
    active = models.BooleanField(default=False, verbose_name=_("Active"))
    financially_locked = models.BooleanField(default=False, verbose_name=_("Financially Locked"))
    suspended = models.BooleanField(default=False, verbose_name=_("Suspended"))
    blocked = models.BooleanField(default=False, verbose_name=_("Blocked"))

    # Financial limits
    usage_limit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('80.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_("Usage Limit (%)"),
    )
    min_required_guarantee = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Minimum Required Guarantee (IQD)"),
    )
    max_allowed_guarantee = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_("Maximum Allowed Guarantee (IQD)"),
    )
    single_cashout_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('1000000.00'),
        verbose_name=_("Single Cash-out Limit (IQD)"),
    )
    daily_cashout_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('5000000.00'),
        verbose_name=_("Daily Cash-out Limit (IQD)"),
    )
    monthly_cashout_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('50000000.00'),
        verbose_name=_("Monthly Cash-out Limit (IQD)"),
    )
    cashout_enabled = models.BooleanField(default=True, verbose_name=_("Cash-out Enabled"))
    recharge_enabled = models.BooleanField(default=True, verbose_name=_("Recharge Enabled"))

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_dealerships',
        verbose_name=_("Approved By"),
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Approved At"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Dealership Profile")
        verbose_name_plural = _("Dealership Profiles")
        indexes = [
            models.Index(fields=['status', 'active']),
            models.Index(fields=['financially_locked']),
        ]

    def __str__(self):
        return f"{self.business_name} ({self.user.username}) — {self.get_status_display()}"

    @property
    def is_operational(self):
        """Dealership is active, not suspended, not blocked."""
        return self.active and not self.suspended and not self.blocked


# ---------------------------------------------------------------------------
# DealershipGuarantee
# ---------------------------------------------------------------------------

class DealershipGuarantee(models.Model):
    """Financial guarantee provided by a dealership to secure recharges."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        VERIFIED = 'verified', _('Verified')
        REJECTED = 'rejected', _('Rejected')
        EXPIRED = 'expired', _('Expired')

    dealership = models.ForeignKey(
        DealershipProfile, on_delete=models.CASCADE,
        related_name='guarantees',
    )
    cash_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Cash Amount (IQD)"),
    )
    bank_check_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Bank Check Amount (IQD)"),
    )
    legal_document_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Legal Document Amount (IQD)"),
    )
    total_guarantee_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Total Guarantee Amount (IQD)"),
    )
    document_file = models.FileField(
        upload_to='dealership/guarantees/', null=True, blank=True,
        verbose_name=_("Document File"),
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
        verbose_name=_("Status"),
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='verified_guarantees',
        verbose_name=_("Verified By"),
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Verified At"))
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Expires At"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Dealership Guarantee")
        verbose_name_plural = _("Dealership Guarantees")
        ordering = ['-created_at']

    def __str__(self):
        return f"Guarantee {self.total_guarantee_amount} IQD — {self.dealership.business_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        self.total_guarantee_amount = (
            self.cash_amount + self.bank_check_amount + self.legal_document_amount
        )
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# DealershipRechargeFeeConfig
# ---------------------------------------------------------------------------

class DealershipRechargeFeeConfig(models.Model):
    """Configurable fee rate for dealership-to-client wallet recharges."""

    class FeeMode(models.TextChoices):
        ADDED_ON_TOP = 'added_on_top', _('Added On Top')
        DEDUCTED_FROM_DEPOSIT = 'deducted_from_deposit', _('Deducted From Deposit')

    fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Fee (%)"),
    )
    minimum_fee_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_("Minimum Fee Amount (IQD)"),
    )
    maximum_fee_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_("Maximum Fee Amount (IQD)"),
    )
    default_fee_mode = models.CharField(
        max_length=30, choices=FeeMode.choices,
        default=FeeMode.ADDED_ON_TOP,
        verbose_name=_("Default Fee Mode"),
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Active"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Dealership Recharge Fee Config")
        verbose_name_plural = _("Dealership Recharge Fee Configs")
        ordering = ['-created_at']

    def __str__(self):
        return f"Fee {self.fee_percent}% ({self.default_fee_mode}) — {'Active' if self.is_active else 'Inactive'}"

    @classmethod
    def get_active_config(cls):
        """Return the active fee config, creating a default if none exists."""
        config = cls.objects.filter(is_active=True).order_by('-created_at').first()
        if config is None:
            config = cls.objects.create(
                fee_percent=Decimal('1.00'),
                default_fee_mode=cls.FeeMode.ADDED_ON_TOP,
            )
        return config


# ---------------------------------------------------------------------------
# DealershipClientRecharge
# ---------------------------------------------------------------------------

class DealershipClientRecharge(models.Model):
    """Record of a dealership recharging a client's wallet."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        REJECTED = 'rejected', _('Rejected')
        REVERSED = 'reversed', _('Reversed')

    class FeeMode(models.TextChoices):
        ADDED_ON_TOP = 'added_on_top', _('Added On Top')
        DEDUCTED_FROM_DEPOSIT = 'deducted_from_deposit', _('Deducted From Deposit')

    dealership = models.ForeignKey(
        DealershipProfile, on_delete=models.CASCADE,
        related_name='client_recharges',
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='dealership_recharges',
        verbose_name=_("Client"),
    )
    fee_mode = models.CharField(
        max_length=30, choices=FeeMode.choices,
        default=FeeMode.ADDED_ON_TOP,
        verbose_name=_("Fee Mode"),
    )
    fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=_("Fee Percent"),
    )

    # Financial fields — all calculated server-side
    cash_received_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Cash Received from Client (IQD)"),
    )
    wallet_credit_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Wallet Credit Amount (IQD)"),
    )
    dealership_fee_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Dealership Fee Amount (IQD)"),
    )
    dealership_exposure_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Dealership Exposure Amount (IQD)"),
    )

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
        verbose_name=_("Status"),
    )
    receipt_number = models.CharField(
        max_length=64, unique=True, null=True, blank=True,
        verbose_name=_("Receipt Number"),
    )
    proof_file = models.FileField(
        upload_to='dealership/recharges/', null=True, blank=True,
        verbose_name=_("Proof File"),
    )
    wallet_transaction = models.ForeignKey(
        'wallet.WalletTransaction', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='dealership_recharge',
        verbose_name=_("Wallet Transaction"),
    )
    idempotency_key = models.CharField(
        max_length=255, null=True, blank=True, db_index=True,
        verbose_name=_("Idempotency Key"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_recharges',
        verbose_name=_("Created By"),
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Dealership Client Recharge")
        verbose_name_plural = _("Dealership Client Recharges")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dealership', 'status']),
            models.Index(fields=['client', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['dealership_id', 'idempotency_key'],
                name='uq_dealership_idempotency_recharge',
                condition=models.Q(idempotency_key__isnull=False),
            )
        ]

    def __str__(self):
        return (
            f"Recharge {self.wallet_credit_amount} IQD "
            f"→ {self.client.username} ({self.get_status_display()})"
        )


# ---------------------------------------------------------------------------
# DealershipClientCashout
# ---------------------------------------------------------------------------

class DealershipClientCashout(models.Model):
    """Record of a client cashing out wallet funds through a dealership."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CODE_ISSUED = 'code_issued', _('Code Issued')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        EXPIRED = 'expired', _('Expired')
        DISPUTED = 'disputed', _('Disputed')
        REVERSED = 'reversed', _('Reversed')

    dealership = models.ForeignKey(
        DealershipProfile, on_delete=models.CASCADE,
        related_name='client_cashouts',
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='dealership_cashouts',
        verbose_name=_("Client"),
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Amount (IQD)"),
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
        verbose_name=_("Status"),
    )
    confirmation_code_hash = models.CharField(
        max_length=128, blank=True,
        verbose_name=_("Confirmation Code Hash"),
    )
    code_expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Code Expires At"))
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Confirmed At"))
    wallet_transaction = models.ForeignKey(
        'wallet.WalletTransaction', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='dealership_cashout',
        verbose_name=_("Wallet Transaction"),
    )
    dealership_ledger_entry = models.ForeignKey(
        'DealershipCreditLedger', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='cashout_entry',
        verbose_name=_("Ledger Entry"),
    )
    idempotency_key = models.CharField(
        max_length=255, null=True, blank=True, db_index=True,
        verbose_name=_("Idempotency Key"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    dispute_reason = models.TextField(blank=True, verbose_name=_("Dispute Reason"))

    class Meta:
        verbose_name = _("Dealership Client Cashout")
        verbose_name_plural = _("Dealership Client Cashouts")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dealership', 'status']),
            models.Index(fields=['client', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['dealership_id', 'idempotency_key'],
                name='uq_dealership_idempotency_cashout',
                condition=models.Q(idempotency_key__isnull=False),
            )
        ]

    def __str__(self):
        return (
            f"Cashout {self.amount} IQD "
            f"← {self.client.username} ({self.get_status_display()})"
        )


# ---------------------------------------------------------------------------
# DealershipCreditLedger
# ---------------------------------------------------------------------------

class DealershipCreditLedger(models.Model):
    """Ledger tracking all dealership credit/debit movements."""

    class TransactionType(models.TextChoices):
        GUARANTEE_ADDED = 'guarantee_added', _('Guarantee Added')
        CLIENT_RECHARGE = 'client_recharge', _('Client Recharge')
        RECHARGE_REVERSAL = 'recharge_reversal', _('Recharge Reversal')
        CLIENT_CASHOUT = 'client_cashout', _('Client Cashout')
        CASHOUT_REVERSAL = 'cashout_reversal', _('Cashout Reversal')
        SETTLEMENT_PAID_TO_PLATFORM = 'settlement_paid_to_platform', _('Settlement Paid to Platform')
        SETTLEMENT_PAID_BY_PLATFORM = 'settlement_paid_by_platform', _('Settlement Paid by Platform')
        MANUAL_ADJUSTMENT = 'manual_adjustment', _('Manual Adjustment')

    dealership = models.ForeignKey(
        DealershipProfile, on_delete=models.CASCADE,
        related_name='ledger_entries',
    )
    transaction_type = models.CharField(
        max_length=40, choices=TransactionType.choices, db_index=True,
        verbose_name=_("Transaction Type"),
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Amount (IQD)"),
    )
    balance_after = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name=_("Balance After (IQD)"),
    )
    reference_type = models.CharField(
        max_length=50, blank=True,
        verbose_name=_("Reference Type"),
    )
    reference_id = models.UUIDField(null=True, blank=True, verbose_name=_("Reference ID"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Created By"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Dealership Credit Ledger")
        verbose_name_plural = _("Dealership Credit Ledger")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dealership', 'transaction_type']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        return f"[{self.transaction_type}] {self.amount} IQD — {self.dealership.business_name}"


# ---------------------------------------------------------------------------
# DealershipSettlement
# ---------------------------------------------------------------------------

class DealershipSettlement(models.Model):
    """Periodic settlement between dealership and platform."""

    class Direction(models.TextChoices):
        DEALERSHIP_OWES_PLATFORM = 'dealership_owes_platform', _('Dealership Owes Platform')
        PLATFORM_OWES_DEALERSHIP = 'platform_owes_dealership', _('Platform Owes Dealership')
        SETTLED_ZERO = 'settled_zero', _('Settled Zero')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    dealership = models.ForeignKey(
        DealershipProfile, on_delete=models.CASCADE,
        related_name='settlements',
    )
    period_start = models.DateField(verbose_name=_("Period Start"))
    period_end = models.DateField(verbose_name=_("Period End"))
    total_recharges = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Total Recharges (IQD)"),
    )
    total_cashouts = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Total Cashouts (IQD)"),
    )
    net_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name=_("Net Amount (IQD)"),
    )
    direction = models.CharField(
        max_length=30, choices=Direction.choices,
        verbose_name=_("Direction"),
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
        verbose_name=_("Status"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_settlements',
        verbose_name=_("Created By"),
    )
    settled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='settlements_processed',
        verbose_name=_("Settled By"),
    )
    settled_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Settled At"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Dealership Settlement")
        verbose_name_plural = _("Dealership Settlements")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dealership', 'status']),
            models.Index(fields=['period_start', 'period_end']),
        ]

    def __str__(self):
        return (
            f"Settlement {self.period_start} → {self.period_end} "
            f"({self.get_direction_display()}) — {self.get_status_display()}"
        )
