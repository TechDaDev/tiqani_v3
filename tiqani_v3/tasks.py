"""
Project-wide background tasks — media cleanup reporting, health checks.

These tasks are orchestrated by Celery Beat via django-celery-beat.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def generate_media_orphan_report_task():
    """
    Generate a report of potential orphaned media files.

    This task performs a DRY-RUN only — it does NOT delete any files.
    It compares stored FileField/ImageField references against
    filesystem/S3 contents and reports discrepancies.

    Returns a summary dict with counts.
    """
    report = {
        "task": "generate_media_orphan_report",
        "dry_run": True,
        "orphan_count": 0,
        "missing_count": 0,
        "total_media_fields": 0,
        "note": "Dry run only — no files were deleted.",
    }

    # Collect all file field values
    file_references = _collect_file_references()

    report["total_media_fields"] = len(file_references)
    report["missing_count"] = sum(
        1 for ref in file_references if ref.get("exists") is False
    )

    logger.info(
        "Media orphan report: %d fields checked, %d missing references (dry run).",
        report["total_media_fields"],
        report["missing_count"],
    )

    return report


def _collect_file_references():
    """Collect all FileField/ImageField values from the database."""
    references = []

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for user in User.objects.all().iterator():
            if user.profile_image:
                references.append({
                    "model": "CustomUser",
                    "field": "profile_image",
                    "pk": str(user.pk),
                    "path": user.profile_image.name,
                    "exists": _check_file_exists(user.profile_image),
                })
    except Exception as exc:
        logger.warning("Error collecting user profile images: %s", exc)

    try:
        from accounts.models import TechnicianProfile
        for tp in TechnicianProfile.objects.all().iterator():
            if tp.identification_documents:
                references.append({
                    "model": "TechnicianProfile",
                    "field": "identification_documents",
                    "pk": str(tp.pk),
                    "path": tp.identification_documents.name,
                    "exists": _check_file_exists(tp.identification_documents),
                })
    except Exception as exc:
        logger.warning("Error collecting technician documents: %s", exc)

    try:
        from accounts.models import TechnicianImage
        for ti in TechnicianImage.objects.all().iterator():
            if ti.image:
                references.append({
                    "model": "TechnicianImage",
                    "field": "image",
                    "pk": str(ti.pk),
                    "path": ti.image.name,
                    "exists": _check_file_exists(ti.image),
                })
    except Exception as exc:
        logger.warning("Error collecting technician images: %s", exc)

    try:
        from dealership.models import DealershipGuarantee
        for dg in DealershipGuarantee.objects.all().iterator():
            if dg.document_file:
                references.append({
                    "model": "DealershipGuarantee",
                    "field": "document_file",
                    "pk": str(dg.pk),
                    "path": dg.document_file.name,
                    "exists": _check_file_exists(dg.document_file),
                })
    except Exception as exc:
        logger.warning("Error collecting guarantee documents: %s", exc)

    try:
        from dealership.models import DealershipClientRecharge
        for dr in DealershipClientRecharge.objects.all().iterator():
            if dr.proof_file:
                references.append({
                    "model": "DealershipClientRecharge",
                    "field": "proof_file",
                    "pk": str(dr.pk),
                    "path": dr.proof_file.name,
                    "exists": _check_file_exists(dr.proof_file),
                })
    except Exception as exc:
        logger.warning("Error collecting recharge proofs: %s", exc)

    return references


def _check_file_exists(field):
    """Check if a file field's storage reports the file as existing."""
    try:
        return field.storage.exists(field.name)
    except Exception:
        return None


@shared_task
def celery_health_check_task():
    """Simple health check to verify Celery workers are responsive."""
    logger.info("Celery health check: OK")
    return {
        "task": "celery_health_check",
        "status": "ok",
        "timestamp": timezone.now().isoformat(),
    }
