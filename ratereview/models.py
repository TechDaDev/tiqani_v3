"""Rating and review models."""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from decimal import Decimal


class Review(models.Model):
    """Customer feedback for a technician (optionally tied to a contract)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        'contract.Contract',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviews',
        help_text="Optional link to a contract to verify the engagement",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_made',
        help_text="User who submitted the review",
    )
    technician = models.ForeignKey(
        'accounts.TechnicianProfile',
        on_delete=models.CASCADE,
        related_name='reviews_received',
        help_text="Technician being reviewed",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall rating from 1 (poor) to 5 (excellent)",
    )
    work_quality_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Specific score for quality of work",
    )
    communication_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Specific score for communication and responsiveness",
    )
    timeliness_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Specific score for timeliness and punctuality",
    )
    professionalism_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Specific score for professionalism and conduct",
    )
    title = models.CharField(max_length=150, blank=True, help_text="Short headline for the review")
    comment = models.TextField(blank=True, help_text="Detailed feedback from the client")
    technician_response = models.TextField(blank=True, help_text="Optional response from the technician")
    is_public = models.BooleanField(default=True, help_text="If false, hides the review from public listings")
    is_verified = models.BooleanField(default=False, help_text="True when linked to a contract or manually approved")
    helpful_count = models.PositiveIntegerField(default=0, help_text="Number of times users marked this review helpful")
    reported_count = models.PositiveIntegerField(default=0, help_text="Number of times the review was reported")
    flagged_at = models.DateTimeField(null=True, blank=True, help_text="When the review was flagged for moderation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['technician', 'created_at']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['contract', 'technician']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reviewer', 'contract'],
                condition=Q(contract__isnull=False),
                name='unique_reviewer_contract_review',
            ),
        ]

    def __str__(self):
        return f"Review {self.rating}/5 for {self.technician.user.username}"

    def compute_overall_rating(self) -> int:
        """Calculate overall rating using specific scores when available."""
        scores = [
            score
            for score in [
                self.work_quality_rating,
                self.communication_rating,
                self.timeliness_rating,
                self.professionalism_rating,
            ]
            if score is not None
        ]
        if scores:
            return round(sum(scores) / len(scores)) or 1
        return self.rating or 1

    def save(self, *args, **kwargs):
        # Auto-verify when linked to a contract
        self.is_verified = bool(self.contract_id) or self.is_verified
        # Normalize rating from sub-scores if provided
        self.rating = self.compute_overall_rating()

        super().save(*args, **kwargs)

        # Update cached technician rating after persistence
        if self.technician_id and hasattr(self.technician, 'update_rating'):
            self.technician.update_rating()

    def publish(self):
        """Make the review visible."""
        self.is_public = True
        self.save(update_fields=['is_public', 'updated_at'])

    def hide(self):
        """Hide the review from public listings."""
        self.is_public = False
        self.save(update_fields=['is_public', 'updated_at'])

    def mark_helpful(self):
        """Increment the helpful counter (idempotency should be enforced at the caller)."""
        self.helpful_count = models.F('helpful_count') + 1
        self.save(update_fields=['helpful_count'])
        self.refresh_from_db(fields=['helpful_count'])
        return self.helpful_count

    def flag(self):
        """Increment reported count (does NOT set flagged_at — caller decides threshold)."""
        self.reported_count = models.F('reported_count') + 1
        self.save(update_fields=['reported_count'])
        self.refresh_from_db(fields=['reported_count'])
        return self.reported_count


class ReviewHelpful(models.Model):
    """Tracks which users marked a review as helpful — prevents duplicate votes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name='helpful_votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='helpful_votes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'user'],
                name='unique_review_helpful_vote',
            ),
        ]


class ReviewReport(models.Model):
    """Tracks reports against a review — prevents duplicate reports."""

    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('abuse', 'Abusive or harmful'),
        ('fake', 'Fake or fraudulent'),
        ('inappropriate', 'Inappropriate content'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name='reports'
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='review_reports',
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'reporter'],
                name='unique_review_report',
            ),
        ]
