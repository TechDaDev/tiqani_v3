"""Notification and activity feed models."""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Per-user notification for platform events."""

    class Type(models.TextChoices):
        CONTRACT_CREATED = 'contract_created', 'Contract Created'
        CONTRACT_PROPOSAL_SUBMITTED = 'contract_proposal_submitted', 'Proposal Submitted'
        CONTRACT_ACCEPTED = 'contract_accepted', 'Contract Accepted'
        CONTRACT_CANCELED = 'contract_canceled', 'Contract Canceled'
        CONTRACT_COMPLETED = 'contract_completed', 'Contract Completed'
        STAGE_SUBMITTED = 'stage_submitted', 'Stage Submitted'
        STAGE_APPROVED = 'stage_approved', 'Stage Approved'
        EXTENSION_REQUESTED = 'extension_requested', 'Extension Requested'
        EXTENSION_APPROVED = 'extension_approved', 'Extension Approved'
        EXTENSION_REJECTED = 'extension_rejected', 'Extension Rejected'
        REVIEW_CREATED = 'review_created', 'Review Created'
        REVIEW_RESPONDED = 'review_responded', 'Review Responded'
        REVIEW_REPORTED = 'review_reported', 'Review Reported'
        REVIEW_MODERATED = 'review_moderated', 'Review Moderated'
        WALLET_TRANSACTION = 'wallet_transaction', 'Wallet Transaction'
        PAYMENT_INTENT_CREATED = 'payment_intent_created', 'Payment Intent Created'
        PAYMENT_INTENT_PAID = 'payment_intent_paid', 'Payment Intent Paid'
        WITHDRAWAL_REQUESTED = 'withdrawal_requested', 'Withdrawal Requested'
        WITHDRAWAL_APPROVED = 'withdrawal_approved', 'Withdrawal Approved'
        WITHDRAWAL_REJECTED = 'withdrawal_rejected', 'Withdrawal Rejected'
        TECHNICIAN_APPROVED = 'technician_approved', 'Technician Approved'
        TECHNICIAN_REJECTED = 'technician_rejected', 'Technician Rejected'
        SYSTEM = 'system', 'System'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='notifications_sent',
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    target_type = models.CharField(max_length=50, blank=True, db_index=True)
    target_id = models.UUIDField(null=True, blank=True)
    target_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['is_read', 'created_at'], name='idx_notif_cleanup'),
            models.Index(fields=['target_type', 'target_id']),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} — {self.recipient.username}"

    def mark_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at', 'updated_at'])

    def mark_unread(self):
        self.is_read = False
        self.read_at = None
        self.save(update_fields=['is_read', 'read_at', 'updated_at'])

    @classmethod
    def unread_count_for_user(cls, user):
        return cls.objects.filter(recipient=user, is_read=False).count()


class ActivityLog(models.Model):
    """Platform-wide activity feed for admins / audit trail."""

    class Audience(models.TextChoices):
        USER = 'user', 'User'
        ADMIN = 'admin', 'Admin'
        SYSTEM = 'system', 'System'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    verb = models.CharField(max_length=50, db_index=True)
    target_type = models.CharField(max_length=50, blank=True, db_index=True)
    target_id = models.UUIDField(null=True, blank=True)
    target_repr = models.CharField(max_length=255, blank=True)
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.SYSTEM, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activity logs'
        indexes = [
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['audience', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.audience}] {self.verb} by {self.actor or 'system'}"
