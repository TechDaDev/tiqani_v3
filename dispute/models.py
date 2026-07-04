"""Phase 10 — Dispute, refund, chargeback, and liability models."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


# ──────────────────────────────────────────────
#  Enumerations (shared constants)
# ──────────────────────────────────────────────


class DisputeReason(models.TextChoices):
    WORK_NOT_DELIVERED = "work_not_delivered", _("Work Not Delivered")
    WORK_INCOMPLETE = "work_incomplete", _("Work Incomplete")
    QUALITY_NOT_AS_AGREED = "quality_not_as_agreed", _("Quality Not as Agreed")
    MISREPRESENTATION = "misrepresentation", _("Misrepresentation")
    UNAUTHORIZED_COMPLETION = "unauthorized_completion", _("Unauthorized Completion")
    CLIENT_NON_COOPERATION = "client_non_cooperation", _("Client Non-Cooperation")
    SCOPE_CHANGE = "scope_change", _("Scope Change")
    PAYMENT_OR_SETTLEMENT_ERROR = "payment_or_settlement_error", _("Payment or Settlement Error")
    FRAUD_SUSPECTED = "fraud_suspected", _("Fraud Suspected")
    DUPLICATE_PAYMENT = "duplicate_payment", _("Duplicate Payment")
    CHARGEBACK_RECEIVED = "chargeback_received", _("Chargeback Received")
    OTHER = "other", _("Other")


class DisputeCategory(models.TextChoices):
    PRE_SETTLEMENT = "pre_settlement", _("Pre-Settlement")
    POST_SETTLEMENT_RECOVERABLE = "post_settlement_recoverable", _("Post-Settlement Recoverable")
    POST_SETTLEMENT_PARTIALLY_RECOVERABLE = "post_settlement_partially_recoverable", _("Post-Settlement Partially Recoverable")
    POST_SETTLEMENT_NON_RECOVERABLE = "post_settlement_non_recoverable", _("Post-Settlement Non-Recoverable")
    CHARGEBACK_REVIEW = "chargeback_review", _("Chargeback Review")


class DisputeStatus(models.TextChoices):
    OPEN = "open", _("Open")
    AWAITING_RESPONSE = "awaiting_response", _("Awaiting Response")
    UNDER_REVIEW = "under_review", _("Under Review")
    MEDIATION = "mediation", _("Mediation")
    RESOLUTION_PROPOSED = "resolution_proposed", _("Resolution Proposed")
    RESOLVED = "resolved", _("Resolved")
    CLOSED = "closed", _("Closed")
    CANCELED = "canceled", _("Canceled")
    REJECTED = "rejected", _("Rejected")


class ResolutionType(models.TextChoices):
    FULL_CLIENT_REFUND = "full_client_refund", _("Full Client Refund")
    PARTIAL_CLIENT_REFUND = "partial_client_refund", _("Partial Client Refund")
    FULL_TECHNICIAN_AWARD = "full_technician_award", _("Full Technician Award")
    PARTIAL_TECHNICIAN_AWARD = "partial_technician_award", _("Partial Technician Award")
    SPLIT_RESOLUTION = "split_resolution", _("Split Resolution")
    NO_FINANCIAL_CHANGE = "no_financial_change", _("No Financial Change")
    DISPUTE_REJECTED = "dispute_rejected", _("Dispute Rejected")
    MANUAL_RECOVERY_REQUIRED = "manual_recovery_required", _("Manual Recovery Required")
    CHARGEBACK_UPHELD = "chargeback_upheld", _("Chargeback Upheld")
    CHARGEBACK_REJECTED = "chargeback_rejected", _("Chargeback Rejected")


class RefundSourceType(models.TextChoices):
    ESCROW = "escrow", _("Escrow")
    TECHNICIAN_WALLET_REVERSAL = "technician_wallet_reversal", _("Technician Wallet Reversal")
    PLATFORM_FEE_REVERSAL = "platform_fee_reversal", _("Platform Fee Reversal")
    SPLIT_SOURCES = "split_sources", _("Split Sources")
    MANUAL_RECOVERY = "manual_recovery", _("Manual Recovery")
    SANDBOX_PROVIDER = "sandbox_provider", _("Sandbox Provider")


class RefundStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELED = "canceled", _("Canceled")
    PARTIALLY_COMPLETED = "partially_completed", _("Partially Completed")


class ChargebackStatus(models.TextChoices):
    RECEIVED = "received", _("Received")
    UNDER_REVIEW = "under_review", _("Under Review")
    EVIDENCE_SUBMITTED = "evidence_submitted", _("Evidence Submitted")
    UPHELD = "upheld", _("Upheld")
    REJECTED = "rejected", _("Rejected")
    PARTIALLY_UPHELD = "partially_upheld", _("Partially Upheld")
    CLOSED = "closed", _("Closed")


class LiabilityStatus(models.TextChoices):
    OPEN = "open", _("Open")
    PARTIALLY_RECOVERED = "partially_recovered", _("Partially Recovered")
    FULLY_RECOVERED = "fully_recovered", _("Fully Recovered")
    WRITTEN_OFF = "written_off", _("Written Off")


class EvidenceType(models.TextChoices):
    DOCUMENT = "document", _("Document")
    IMAGE = "image", _("Image")
    MESSAGE_REFERENCE = "message_reference", _("Message Reference")
    DELIVERABLE_REFERENCE = "deliverable_reference", _("Deliverable Reference")
    MILESTONE_REFERENCE = "milestone_reference", _("Milestone Reference")
    OTHER = "other", _("Other")


# ──────────────────────────────────────────────
#  Dispute models
# ──────────────────────────────────────────────


class ContractDispute(models.Model):
    """Core dispute record tied to a contract."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.CASCADE,
        related_name="disputes",
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="opened_disputes",
    )
    respondent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="respondent_disputes",
    )
    reason = models.CharField(max_length=40, choices=DisputeReason.choices, db_index=True)
    category = models.CharField(
        max_length=40, choices=DisputeCategory.choices,
        null=True, blank=True, db_index=True,
    )
    claimed_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="IQD")
    status = models.CharField(
        max_length=30, choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN, db_index=True,
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_disputes",
    )
    opened_at = models.DateTimeField(auto_now_add=True, db_index=True)
    response_due_at = models.DateTimeField(null=True, blank=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(
        max_length=64, unique=True, null=True, blank=True,
    )
    resolution_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Contract Dispute")
        verbose_name_plural = _("Contract Disputes")
        indexes = [
            models.Index(fields=["contract", "status"]),
            models.Index(fields=["opened_by", "status"]),
            models.Index(fields=["respondent", "status"]),
            models.Index(fields=["assigned_staff", "status"]),
        ]

    def __str__(self):
        return f"Dispute {self.id}: {self.get_reason_display()} ({self.get_status_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.claimed_amount and self.contract.agreed_amount:
            if self.claimed_amount > self.contract.agreed_amount:
                raise ValidationError("Claimed amount cannot exceed contract agreed amount.")


class DisputeStatement(models.Model):
    """A textual statement in a dispute (opening or response)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        ContractDispute, on_delete=models.CASCADE,
        related_name="statements",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="dispute_statements",
    )
    statement = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Dispute Statement")
        verbose_name_plural = _("Dispute Statements")

    def __str__(self):
        return f"Statement by {self.submitted_by.username} on dispute {self.dispute.id}"


class DisputeEvidence(models.Model):
    """Evidence submitted for a dispute. Immutable after creation."""

    ALLOWED_MIME_TYPES = [
        "application/pdf",
        "image/jpeg", "image/png", "image/webp",
        "text/plain",
        "application/json",
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        ContractDispute, on_delete=models.CASCADE,
        related_name="evidence_items",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="submitted_evidence",
    )
    evidence_type = models.CharField(
        max_length=30, choices=EvidenceType.choices,
        default=EvidenceType.DOCUMENT,
    )
    description = models.TextField(blank=True, default="")
    file = models.FileField(
        upload_to="dispute_evidence/",
        null=True, blank=True,
        validators=[FileExtensionValidator(
            allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp", "txt", "json"],
        )],
    )
    mime_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)
    integrity_hash = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Dispute Evidence")
        verbose_name_plural = _("Dispute Evidence")

    def __str__(self):
        return f"Evidence {self.id} on dispute {self.dispute.id}"


class DisputeResolution(models.Model):
    """The resolution outcome for a dispute. Appended after admin review."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.OneToOneField(
        ContractDispute, on_delete=models.CASCADE,
        related_name="resolution",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="dispute_resolutions",
    )
    resolution_type = models.CharField(
        max_length=40, choices=ResolutionType.choices,
    )
    client_refund_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    technician_retained_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    platform_fee_reversal_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    escrow_released_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    wallet_reversal_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    unrecoverable_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    outstanding_liability_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    resolution_reason = models.TextField()
    resolved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Dispute Resolution")
        verbose_name_plural = _("Dispute Resolutions")

    def __str__(self):
        return f"Resolution {self.get_resolution_type_display()} for dispute {self.dispute.id}"


class DisputeAuditEvent(models.Model):
    """Immutable audit trail for dispute state transitions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        ContractDispute, on_delete=models.CASCADE,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=50, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Dispute Audit Event")
        verbose_name_plural = _("Dispute Audit Events")
        indexes = [
            models.Index(fields=["dispute", "event_type"]),
        ]

    def __str__(self):
        return f"{self.event_type} on dispute {self.dispute.id}"


# ──────────────────────────────────────────────
#  Refund model
# ──────────────────────────────────────────────


class RefundRecord(models.Model):
    """Record of a financial refund resulting from a dispute resolution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        ContractDispute, on_delete=models.CASCADE,
        related_name="refunds",
    )
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.CASCADE,
        related_name="refunds",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="refunds_received",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="IQD")
    source_type = models.CharField(
        max_length=30, choices=RefundSourceType.choices,
    )
    status = models.CharField(
        max_length=25, choices=RefundStatus.choices,
        default=RefundStatus.PENDING, db_index=True,
    )
    refund_method = models.CharField(max_length=50, blank=True, default="")
    provider_reference = models.CharField(max_length=255, blank=True, default="")
    wallet_transaction = models.ForeignKey(
        "wallet.WalletTransaction", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="refund_records",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="created_refunds",
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=100, blank=True, default="")
    failure_message = models.TextField(blank=True, default="")
    idempotency_key = models.CharField(
        max_length=64, unique=True, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Refund Record")
        verbose_name_plural = _("Refund Records")

    def __str__(self):
        return f"Refund {self.amount} {self.currency} – {self.get_status_display()}"


# ──────────────────────────────────────────────
#  Chargeback model
# ──────────────────────────────────────────────


class ChargebackEvent(models.Model):
    """Sandbox or administrative chargeback event record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.CASCADE,
        related_name="chargeback_events",
    )
    dispute = models.ForeignKey(
        ContractDispute, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="chargeback_events",
    )
    provider_reference = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason_code = models.CharField(max_length=50, blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)
    evidence_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=25, choices=ChargebackStatus.choices,
        default=ChargebackStatus.RECEIVED, db_index=True,
    )
    outcome = models.CharField(max_length=40, blank=True, default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="resolved_chargebacks",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(
        max_length=64, unique=True, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Chargeback Event")
        verbose_name_plural = _("Chargeback Events")

    def __str__(self):
        return f"Chargeback {self.id} – {self.get_status_display()}"


# ──────────────────────────────────────────────
#  Financial liability model
# ──────────────────────────────────────────────


class UserFinancialLiability(models.Model):
    """Outstanding financial liability when full recovery is not possible."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="financial_liabilities",
    )
    source_dispute = models.ForeignKey(
        ContractDispute, on_delete=models.CASCADE,
        related_name="liabilities",
    )
    original_amount = models.DecimalField(max_digits=15, decimal_places=2)
    recovered_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"),
    )
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=LiabilityStatus.choices,
        default=LiabilityStatus.OPEN, db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("User Financial Liability")
        verbose_name_plural = _("User Financial Liabilities")

    def __str__(self):
        return f"Liability {self.remaining_amount} – {self.get_status_display()}"
