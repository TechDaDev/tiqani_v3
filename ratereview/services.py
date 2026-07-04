"""Phase 11 review, reputation, and moderation services."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from contract.models import Contract
from dispute.models import ContractDispute, DisputeStatus
from notification.services import create_activity, create_notification_once

from .models import Review, ReviewModerationAction, UserReputationSnapshot


EDIT_WINDOW_DAYS = getattr(settings, "REVIEW_EDIT_WINDOW_DAYS", 14)
MAX_REVIEW_EDITS = getattr(settings, "MAX_REVIEW_EDITS", 1)

TERMINAL_DISPUTE_STATUSES = {
    DisputeStatus.RESOLVED,
    DisputeStatus.CLOSED,
    DisputeStatus.CANCELED,
    DisputeStatus.REJECTED,
}


@dataclass(frozen=True)
class ReviewEligibility:
    eligible: bool
    reason_code: str
    reviewee: object | None = None
    existing_review: Review | None = None
    editable: bool = False

    def as_dict(self):
        return {
            "eligible": self.eligible,
            "reason_code": self.reason_code,
            "reviewee": _safe_user(self.reviewee),
            "existing_review": str(self.existing_review.id) if self.existing_review else None,
            "editable": self.editable,
        }


def _safe_user(user):
    if not user:
        return None
    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.get_full_name(),
        "role": user.role,
    }


def _contract_participants(contract):
    return contract.client.user, contract.technician.user


def _reviewee_for(contract, actor):
    client_user, tech_user = _contract_participants(contract)
    if actor == client_user:
        return tech_user
    if actor == tech_user:
        return client_user
    return None


def get_review_eligibility(contract, actor) -> ReviewEligibility:
    """Return centralized review eligibility for one actor/contract pair."""
    if not actor or not actor.is_authenticated:
        return ReviewEligibility(False, "NOT_PARTICIPANT")

    reviewee = _reviewee_for(contract, actor)
    if reviewee is None:
        return ReviewEligibility(False, "NOT_PARTICIPANT")
    if reviewee == actor:
        return ReviewEligibility(False, "SELF_REVIEW")
    if contract.status != "completed":
        return ReviewEligibility(False, "CONTRACT_NOT_COMPLETED", reviewee=reviewee)

    unresolved = ContractDispute.objects.filter(contract=contract).exclude(
        status__in=TERMINAL_DISPUTE_STATUSES
    ).exists()
    if unresolved:
        return ReviewEligibility(False, "UNRESOLVED_DISPUTE", reviewee=reviewee)

    existing = Review.objects.filter(
        contract=contract,
        reviewer=actor,
        reviewee=reviewee,
    ).first()
    if existing:
        return ReviewEligibility(
            False,
            "ALREADY_REVIEWED",
            reviewee=reviewee,
            existing_review=existing,
            editable=_is_editable(existing),
        )

    return ReviewEligibility(True, "ELIGIBLE", reviewee=reviewee)


def _is_editable(review):
    if review.status != Review.Status.PUBLISHED or not review.is_public:
        return False
    if review.flagged_at or review.moderation_actions.exists():
        return False
    if review.edit_count >= MAX_REVIEW_EDITS:
        return False
    return review.created_at >= timezone.now() - timedelta(days=EDIT_WINDOW_DAYS)


@transaction.atomic
def create_contract_review(*, contract_id, actor, rating, title="", comment="", dimensions=None):
    """Create or return an existing contract review idempotently."""
    contract = Contract.objects.select_related("client__user", "technician__user").get(id=contract_id)
    eligibility = get_review_eligibility(contract, actor)
    if eligibility.existing_review:
        return eligibility.existing_review, False
    if not eligibility.eligible:
        raise PermissionError(eligibility.reason_code)

    dimensions = dimensions or {}
    reviewee = eligibility.reviewee
    review = Review.objects.create(
        contract=contract,
        reviewer=actor,
        reviewee=reviewee,
        reviewer_role=actor.role,
        technician=contract.technician if reviewee == contract.technician.user else None,
        rating=rating,
        title=title,
        comment=comment,
        work_quality_rating=dimensions.get("work_quality_rating"),
        communication_rating=dimensions.get("communication_rating"),
        timeliness_rating=dimensions.get("timeliness_rating"),
        professionalism_rating=dimensions.get("professionalism_rating"),
        is_verified=True,
        is_public=True,
        status=Review.Status.PUBLISHED,
    )
    _notify_review_created(review, actor)
    recalculate_user_reputation(reviewee, role=reviewee.role)
    return review, True


@transaction.atomic
def update_contract_review(*, review, actor, data):
    """Apply documented edit policy: once within window, no edits after moderation."""
    if review.reviewer_id != actor.id:
        raise PermissionError("NOT_REVIEW_OWNER")
    if not _is_editable(review):
        raise PermissionError("REVIEW_NOT_EDITABLE")

    allowed = {
        "rating",
        "title",
        "comment",
        "work_quality_rating",
        "communication_rating",
        "timeliness_rating",
        "professionalism_rating",
    }
    for field, value in data.items():
        if field in allowed:
            setattr(review, field, value)
    review.edit_count += 1
    review.last_edited_at = timezone.now()
    review.save()
    if review.reviewee_id:
        recalculate_user_reputation(review.reviewee, role=review.reviewee.role)
    create_activity(
        "review_edited",
        actor=actor,
        target_type="review",
        target_id=review.id,
        target_repr=str(review),
        audience="admin",
    )
    return review


@transaction.atomic
def moderate_review(*, review, actor, action, reason=""):
    """Moderate without deleting review history."""
    if action == ReviewModerationAction.Action.HIDE:
        review.hide()
    elif action == ReviewModerationAction.Action.RESTORE:
        review.publish()
    elif action == ReviewModerationAction.Action.VERIFY:
        review.is_verified = True
        review.save(update_fields=["is_verified", "updated_at"])
    elif action == ReviewModerationAction.Action.UNVERIFY:
        review.is_verified = False
        review.save(update_fields=["is_verified", "updated_at"])
    else:
        raise ValueError("Unsupported moderation action.")

    ReviewModerationAction.objects.create(
        review=review,
        actor=actor,
        action=action,
        reason=reason or "",
    )
    create_activity(
        "review_moderated",
        actor=actor,
        target_type="review",
        target_id=review.id,
        target_repr=str(review),
        audience="admin",
        metadata={"action": action, "reason": reason or ""},
    )
    _notify_review_moderated(review, actor, action)
    if review.reviewee_id:
        recalculate_user_reputation(review.reviewee, role=review.reviewee.role)
    if review.technician_id:
        recalculate_user_reputation(review.technician.user, role="technician")
    return review


def restore_review(*, review, actor, reason=""):
    return moderate_review(
        review=review,
        actor=actor,
        action=ReviewModerationAction.Action.RESTORE,
        reason=reason,
    )


@transaction.atomic
def recalculate_user_reputation(user, *, role=None):
    """Recalculate transparent reputation snapshot for one user and role."""
    role = role or user.role
    reviews = Review.objects.filter(
        reviewee=user,
        status=Review.Status.PUBLISHED,
        is_public=True,
        is_verified=True,
    )
    counts = reviews.aggregate(
        total=Count("id"),
        r1=Count("id", filter=Q(rating=1)),
        r2=Count("id", filter=Q(rating=2)),
        r3=Count("id", filter=Q(rating=3)),
        r4=Count("id", filter=Q(rating=4)),
        r5=Count("id", filter=Q(rating=5)),
    )
    total = counts["total"] or 0
    weighted = (
        counts["r1"] * 1 +
        counts["r2"] * 2 +
        counts["r3"] * 3 +
        counts["r4"] * 4 +
        counts["r5"] * 5
    )
    average = Decimal("0.00")
    if total:
        average = (Decimal(weighted) / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    completed_contract_count = _completed_contract_count(user, role)
    label = _reputation_label(total, average)
    snapshot, _ = UserReputationSnapshot.objects.update_or_create(
        user=user,
        role=role if role in ("client", "technician") else user.role,
        defaults={
            "average_rating": average,
            "review_count": total,
            "rating_1_count": counts["r1"] or 0,
            "rating_2_count": counts["r2"] or 0,
            "rating_3_count": counts["r3"] or 0,
            "rating_4_count": counts["r4"] or 0,
            "rating_5_count": counts["r5"] or 0,
            "completed_contract_count": completed_contract_count,
            "label": label,
            "last_recalculated_at": timezone.now(),
        },
    )
    if role == "technician" and hasattr(user, "technician_profile"):
        user.technician_profile.rate = average
        user.technician_profile.save(update_fields=["rate"])
    return snapshot


def _completed_contract_count(user, role):
    if role == "client" and hasattr(user, "client_profile"):
        return Contract.objects.filter(client=user.client_profile, status="completed").count()
    if role == "technician" and hasattr(user, "technician_profile"):
        return Contract.objects.filter(technician=user.technician_profile, status="completed").count()
    return 0


def _reputation_label(review_count, average):
    if review_count >= 5 and average >= Decimal("4.50"):
        return UserReputationSnapshot.Label.HIGHLY_RATED
    if review_count >= 3:
        return UserReputationSnapshot.Label.ESTABLISHED
    return UserReputationSnapshot.Label.NEW


def _notify_review_created(review, actor):
    if not review.reviewee_id:
        return None
    return create_notification_once(
        recipient=review.reviewee,
        notification_type="review_created",
        title="New review received",
        message="You received a new review.",
        actor=actor,
        target_type="review",
        target_id=review.id,
        target_url=f"/reviews/{review.id}",
        deduplication_key=f"review_created:{review.id}:{review.reviewee_id}",
        metadata={"review_id": str(review.id), "rating": review.rating},
    )


def _notify_review_moderated(review, actor, action):
    for recipient in {review.reviewer, review.reviewee}:
        if not recipient or recipient == actor:
            continue
        create_notification_once(
            recipient=recipient,
            notification_type="review_moderated",
            title="Review moderation update",
            message="A review moderation action was recorded.",
            actor=actor,
            target_type="review",
            target_id=review.id,
            target_url=f"/reviews/{review.id}",
            deduplication_key=f"review_moderated:{review.id}:{action}:{recipient.id}",
            metadata={"review_id": str(review.id), "action": action},
        )
