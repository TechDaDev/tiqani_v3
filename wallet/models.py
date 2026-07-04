import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Wallet(models.Model):
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    transaction_id = models.CharField(max_length=32, unique=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_wallet'
        managed = False

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex
        if self.balance < 0:
            raise ValueError('Wallet balance cannot be negative.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Wallet: {self.user.username} ({self.balance})"


class WalletTransaction(TimestampedModel):
    class Type(models.TextChoices):
        DEPOSIT = 'deposit', _('Deposit')
        WITHDRAWAL = 'withdrawal', _('Withdrawal')
        PAYMENT = 'payment', _('Payment')
        REFUND = 'refund', _('Refund')
        ESCROW = 'escrow', _('Escrow')
        RELEASE = 'release', _('Release')
        PLATFORM_FEE = 'platform_fee', _('Platform Fee')

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transactions')
    contract = models.ForeignKey('contract.Contract', null=True, blank=True, on_delete=models.SET_NULL)

    transaction_type = models.CharField(max_length=20, choices=Type.choices, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()

    class Meta:
        db_table = 'accounts_wallettransaction'
        managed = False
        ordering = ['-created_at']


class PlatformWallet(models.Model):
    GLOBAL_KEY = 'global_platform_wallet'

    key = models.CharField(max_length=64, unique=True, default=GLOBAL_KEY, editable=False)
    currency = models.CharField(max_length=3, default='IQD')
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_fees_collected = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_client_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_technician_fees = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_platformwallet'
        managed = False
        verbose_name = _('Platform Wallet')
        verbose_name_plural = _('Platform Wallet')

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.GLOBAL_KEY
        if self.balance < 0:
            raise ValueError('Platform wallet balance cannot be negative.')
        super().save(*args, **kwargs)

    @classmethod
    def get_global_wallet(cls):
        wallet, _ = cls.objects.get_or_create(key=cls.GLOBAL_KEY)
        return wallet

    def __str__(self):
        return f"Platform Wallet ({self.balance} {self.currency})"


class PlatformWalletTransaction(TimestampedModel):
    class SourceType(models.TextChoices):
        CLIENT = 'client', _('Client')
        TECHNICIAN = 'technician', _('Technician')
        SYSTEM = 'system', _('System')

    platform_wallet = models.ForeignKey(
        PlatformWallet,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    contract = models.ForeignKey(
        'contract.Contract',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='platform_fee_transactions'
    )
    source_user = models.ForeignKey(
        'accounts.CustomUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='platform_fee_transactions'
    )
    source_wallet = models.ForeignKey(
        Wallet,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='platform_fee_transactions'
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField()

    class Meta:
        db_table = 'accounts_platformwallettransaction'
        managed = False
        ordering = ['-created_at']

    def __str__(self):
        return f"Platform fee {self.amount} from {self.source_type}"


# ──────────────────────────────────────────────
#  Phase 4 – Fee engine & payment prep models
# ──────────────────────────────────────────────


class PlatformFeeConfig(TimestampedModel):
    """Configurable platform fee rates. Only one active at a time."""

    name = models.CharField(max_length=128, help_text="Label for this fee config")
    technician_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("10.00"),
        help_text="Percentage deducted from technician payout",
    )
    client_service_fee_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00"),
        help_text="Percentage added to client total as service/protection fee",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Platform Fee Config"
        verbose_name_plural = "Platform Fee Configs"

    def __str__(self):
        return f"{self.name} (tech={self.technician_commission_rate}% client={self.client_service_fee_rate}%)"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.technician_commission_rate < 0:
            raise ValidationError("Technician commission rate cannot be negative.")
        if self.client_service_fee_rate < 0:
            raise ValidationError("Client service fee rate cannot be negative.")

    @classmethod
    def get_active_config(cls):
        config = cls.objects.filter(is_active=True).order_by("-created_at").first()
        if config is None:
            config = cls.objects.create(
                name="Default 15% Platform Fee",
                technician_commission_rate=Decimal("10.00"),
                client_service_fee_rate=Decimal("5.00"),
            )
        return config


class ContractPaymentBreakdown(TimestampedModel):
    """Snapshot of fee breakdown for a single contract at acceptance time."""

    contract = models.OneToOneField(
        "contract.Contract", on_delete=models.CASCADE,
        related_name="payment_breakdown",
    )
    fee_config = models.ForeignKey(
        PlatformFeeConfig, null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    contract_amount = models.DecimalField(max_digits=15, decimal_places=2)
    technician_commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    client_service_fee_rate = models.DecimalField(max_digits=5, decimal_places=2)
    technician_commission_amount = models.DecimalField(max_digits=15, decimal_places=2)
    client_service_fee_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_platform_fee = models.DecimalField(max_digits=15, decimal_places=2)
    client_total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    technician_net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="IQD")

    class Meta:
        verbose_name = "Contract Payment Breakdown"
        verbose_name_plural = "Contract Payment Breakdowns"

    def __str__(self):
        return f"Breakdown for {self.contract.contract_reference}: platform={self.total_platform_fee}"


class PlatformEarning(TimestampedModel):
    """Ledger record of platform revenue earned from contract/stage."""

    class EarningType(models.TextChoices):
        TECHNICIAN_COMMISSION = "technician_commission", "Technician Commission"
        CLIENT_SERVICE_FEE = "client_service_fee", "Client Service Fee"
        ADJUSTMENT = "adjustment", "Adjustment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        EARNED = "earned", "Earned"
        REVERSED = "reversed", "Reversed"

    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.CASCADE,
        related_name="platform_earnings",
    )
    stage = models.ForeignKey(
        "contract.ContractStage", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="platform_earnings",
    )
    earning_type = models.CharField(max_length=30, choices=EarningType.choices, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="IQD")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    wallet_transaction = models.ForeignKey(
        "wallet.WalletTransaction", null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Platform Earning"
        verbose_name_plural = "Platform Earnings"

    def __str__(self):
        return f"{self.get_earning_type_display()} {self.amount} – {self.get_status_display()}"


class PaymentIntent(TimestampedModel):
    """Placeholder for future external payment provider."""

    class Purpose(models.TextChoices):
        CONTRACT_FUNDING = "contract_funding", "Contract Funding"
        WALLET_DEPOSIT = "wallet_deposit", "Wallet Deposit"
        WITHDRAWAL = "withdrawal", "Withdrawal"

    class Provider(models.TextChoices):
        MANUAL = "manual", "Manual / Internal"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REQUIRES_ACTION = "requires_action", "Requires Action"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.CASCADE,
        related_name="payment_intents",
    )
    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE,
        related_name="payment_intents",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="IQD")
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.CONTRACT_FUNDING)
    provider = models.CharField(max_length=30, choices=Provider.choices, default=Provider.MANUAL)
    provider_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Intent"
        verbose_name_plural = "Payment Intents"

    def __str__(self):
        return f"{self.get_purpose_display()} {self.amount} – {self.get_status_display()}"


class WithdrawalRequest(TimestampedModel):
    """Technician/admin withdrawal preparation record."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PROCESSING = "processing", "Processing"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE,
        related_name="withdrawal_requests",
    )
    wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT,
        related_name="withdrawal_requests",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="IQD")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    requested_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    failure_code = models.CharField(max_length=100, blank=True)
    failure_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"

    def __str__(self):
        return f"Withdrawal {self.amount} – {self.get_status_display()}"


class ContractSettlement(TimestampedModel):
    """Immutable record of a completed contract escrow settlement."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REVERSED = "reversed", "Reversed"

    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.PROTECT,
        related_name="settlements",
    )
    payment_breakdown = models.ForeignKey(
        ContractPaymentBreakdown, null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    released_principal = models.DecimalField(max_digits=15, decimal_places=2)
    technician_net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    technician_commission_amount = models.DecimalField(max_digits=15, decimal_places=2)
    client_service_fee_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_platform_fee = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="IQD")
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
    )
    initiated_by = models.ForeignKey(
        "accounts.CustomUser", null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=100, blank=True)
    failure_message = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    technician_wallet_transaction = models.ForeignKey(
        WalletTransaction, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="settlement_releases",
    )
    platform_commission_earning = models.ForeignKey(
        PlatformEarning, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="settlement_commission",
    )
    client_fee_earning = models.ForeignKey(
        PlatformEarning, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="settlement_client_fee",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contract Settlement"
        verbose_name_plural = "Contract Settlements"
        constraints = [
            models.UniqueConstraint(
                fields=["contract"],
                condition=models.Q(status="completed"),
                name="unique_completed_settlement_per_contract",
            ),
        ]

    def __str__(self):
        return f"Settlement {self.id}: {self.released_principal} – {self.get_status_display()}"
