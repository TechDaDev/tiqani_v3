"""Offer model — technician proposal linked to an accepted service request.

Phase 6 scope:
    - Technician creates offer for an ACCEPTED service request.
    - Client reviews, accepts, or rejects.
    - Acceptance atomically creates a minimal draft Contract.
    - No wallet, escrow, payment, or execution stages.

See docs/OFFER_STATE_MACHINE.md for transitions.
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from servicerequest.models import ServiceRequest


class Offer(models.Model):
    """
    A technician's proposal for a specific service request.

    One active offer per request is enforced at the application layer.
    Previous SUBMITTED offers are auto-withdrawn when a new offer is submitted.

    Status lifecycle:
        DRAFT     → SUBMITTED → ACCEPTED | REJECTED
        SUBMITTED → WITHDRAWN
        (All other transitions are invalid — terminal states are terminal.)
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        SUBMITTED = "SUBMITTED", _("Submitted")
        ACCEPTED = "ACCEPTED", _("Accepted")
        REJECTED = "REJECTED", _("Rejected")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="offers",
        verbose_name=_("Service Request"),
    )

    # Amount (always IQD)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Amount"),
        help_text=_("Proposed price in IQD"),
    )
    currency = models.CharField(
        max_length=3,
        default="IQD",
        editable=False,
        verbose_name=_("Currency"),
    )

    # Description / scope
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed scope of work"),
    )
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Estimated Duration (Days)"),
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name=_("Status"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        app_label = "contract"
        verbose_name = _("Offer")
        verbose_name_plural = _("Offers")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_request"],
                condition=models.Q(status="ACCEPTED"),
                name="uq_offer_accepted_per_request",
            ),
        ]
        indexes = [
            models.Index(fields=["service_request", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Offer {self.id} on {self.service_request_id} ({self.status})"

    @property
    def client(self):
        """Convenience — the service request owner."""
        return self.service_request.client

    @property
    def technician(self):
        """Convenience — the assigned technician."""
        return self.service_request.technician

    @property
    def is_terminal(self):
        return self.status in (
            self.Status.ACCEPTED,
            self.Status.REJECTED,
            self.Status.WITHDRAWN,
        )

    def can_edit(self):
        """Only DRAFT offers can be edited."""
        return self.status == self.Status.DRAFT

    def can_withdraw(self):
        """DRAFT and SUBMITTED offers can be withdrawn."""
        return self.status in (self.Status.DRAFT, self.Status.SUBMITTED)

    def clean(self):
        """Validate status transitions."""
        if self.pk:
            try:
                old = Offer.objects.get(pk=self.pk)
            except Offer.DoesNotExist:
                return
            if old.status != self.status:
                allowed = self._allowed_transitions(old.status)
                if self.status not in allowed:
                    from django.core.exceptions import ValidationError
                    raise ValidationError(
                        {"status": _(f"Cannot transition from {old.status} to {self.status}")}
                    )

    @staticmethod
    def _allowed_transitions(from_status):
        transitions = {
            Offer.Status.DRAFT: [Offer.Status.SUBMITTED, Offer.Status.WITHDRAWN],
            Offer.Status.SUBMITTED: [
                Offer.Status.ACCEPTED,
                Offer.Status.REJECTED,
                Offer.Status.WITHDRAWN,
            ],
            Offer.Status.ACCEPTED: [],
            Offer.Status.REJECTED: [],
            Offer.Status.WITHDRAWN: [],
        }
        return transitions.get(from_status, [])

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        # Ensure amount is Decimal for comparison
        if isinstance(self.amount, str):
            self.amount = Decimal(self.amount)
        # Validate amount
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": _("Amount must be greater than zero.")})
        self.clean()
        super().save(*args, **kwargs)
