"""
ServiceRequest model — lightweight client-to-technician inquiry/request.

This is the initial contact mechanism: a client sends a service request to a
specific technician describing what they need. The technician can accept or
decline. This is NOT a contract — contracts are created separately after
acceptance/negotiation.

Phase 4 scope: create, list (client + technician), detail, accept, decline,
cancel (client), withdraw (client). No payments, stages, or reviews.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class ServiceRequest(models.Model):
    """
    A client-initiated request for service from a specific technician.

    Status lifecycle:
        PENDING   → ACCEPTED | DECLINED | CANCELLED | WITHDRAWN
        ACCEPTED  → (terminal for Phase 4)
        DECLINED  → (terminal)
        CANCELLED → (terminal, client only)
        WITHDRAWN → (terminal, client only)
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACCEPTED = "ACCEPTED", _("Accepted")
        DECLINED = "DECLINED", _("Declined")
        CANCELLED = "CANCELLED", _("Cancelled")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        "accounts.ClientProfile",
        on_delete=models.CASCADE,
        related_name="service_requests",
        verbose_name=_("Client"),
    )
    technician = models.ForeignKey(
        "accounts.TechnicianProfile",
        on_delete=models.CASCADE,
        related_name="service_requests",
        verbose_name=_("Technician"),
    )
    category = models.ForeignKey(
        "category.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
        verbose_name=_("Category"),
    )
    skill = models.ForeignKey(
        "category.Skill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
        verbose_name=_("Skill"),
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Title"),
        help_text=_("Brief title for the service request"),
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed description of the service needed"),
    )
    governorate = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Governorate"),
    )
    service_address = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Service Address"),
    )
    preferred_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Preferred Date"),
    )
    preferred_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Preferred Time"),
    )
    is_urgent = models.BooleanField(
        default=False,
        verbose_name=_("Urgent"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        app_label = "servicerequest"
        verbose_name = _("Service Request")
        verbose_name_plural = _("Service Requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["technician", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Request {self.id} - {self.title} ({self.status})"

    def clean(self):
        """Validate status transitions for existing objects."""
        if self.pk:
            try:
                old = ServiceRequest.objects.get(pk=self.pk)
            except ServiceRequest.DoesNotExist:
                return
            if old.status != self.status:
                allowed = self._allowed_transitions(old.status)
                if self.status not in allowed:
                    raise ValidationError(
                        {"status": _(f"Cannot transition from {old.status} to {self.status}")}
                    )

    def _allowed_transitions(self, from_status):
        transitions = {
            self.Status.PENDING: [
                self.Status.ACCEPTED,
                self.Status.DECLINED,
                self.Status.CANCELLED,
                self.Status.WITHDRAWN,
            ],
            self.Status.ACCEPTED: [],
            self.Status.DECLINED: [],
            self.Status.CANCELLED: [],
            self.Status.WITHDRAWN: [],
        }
        return transitions.get(from_status, [])

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
