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
