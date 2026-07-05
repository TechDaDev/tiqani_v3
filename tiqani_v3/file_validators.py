"""
Reusable file validators for upload fields.

Validates file extensions and sizes.
All values in MB for readability.
"""

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Allowed extensions
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
PROOF_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_WALLET_RECHARGE_RECEIPT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
DEFAULT_WALLET_RECHARGE_RECEIPT_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Explicitly blocked extensions — even if they match allowed sets
BLOCKED_EXTENSIONS = {
    ".exe", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".svg", ".html", ".htm", ".js", ".ts", ".py", ".sh",
    ".bat", ".cmd", ".ps1", ".vbs", ".app", ".dmg",
    ".iso", ".bin", ".dat",
}

# Blocked MIME types (approximate check via extension is primary)
BLOCKED_MIMES = {
    "application/x-msdownload",
    "application/x-dosexec",
    "application/zip",
    "application/x-rar-compressed",
    "application/x-7z-compressed",
    "application/gzip",
    "application/x-tar",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "image/svg+xml",
    "text/html",
    "text/javascript",
    "application/javascript",
    "application/x-sh",
    "application/x-msdos-program",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_extension(filename):
    """Return the lowercase extension of a filename."""
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def _validate_extension(filename, allowed_extensions, field_label="File"):
    """Validate that the file extension is in the allowed set."""
    if not filename:
        raise ValidationError(_("No file provided."))

    ext = _get_extension(filename)
    if not ext:
        raise ValidationError(_(f"{field_label} has no file extension."))

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            _(f"{field_label} type ({ext}) is not allowed for security reasons.")
        )

    if ext not in allowed_extensions:
        raise ValidationError(
            _(
                f"{field_label} type '{ext}' is not supported. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}."
            )
        )


def _validate_file_size(file, max_size_mb, field_label="File"):
    """Validate file size does not exceed max_size_mb."""
    if file is None:
        return
    max_bytes = max_size_mb * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            _(
                f"{field_label} size exceeds {max_size_mb} MB limit "
                f"({file.size / (1024 * 1024):.1f} MB)."
            )
        )


def _validate_content_type(file, field_label="File"):
    """Optional content-type validation if file object has content_type."""
    if file is None:
        return
    content_type = getattr(file, "content_type", None)
    if content_type and content_type in BLOCKED_MIMES:
        raise ValidationError(
            _(f"{field_label} MIME type '{content_type}' is not allowed.")
        )


def _normalize_extensions(values):
    return {
        value.lower() if str(value).startswith(".") else f".{str(value).lower()}"
        for value in values
    }


def _validate_allowed_content_type(file, allowed_content_types, field_label="File"):
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in set(allowed_content_types):
        raise ValidationError(
            _(
                f"{field_label} MIME type '{content_type}' is not supported. "
                f"Allowed: {', '.join(sorted(allowed_content_types))}."
            )
        )


# ---------------------------------------------------------------------------
# Public validators
# ---------------------------------------------------------------------------

def validate_profile_image_file(file):
    """
    Validate profile/avatar images.
    Allowed: jpg, jpeg, png, webp. Max: 2 MB.
    """
    max_mb = getattr(settings, "MAX_PROFILE_IMAGE_SIZE_MB", 2)
    _validate_extension(file.name, IMAGE_EXTENSIONS, "Profile image")
    _validate_file_size(file, max_mb, "Profile image")
    _validate_content_type(file, "Profile image")


def validate_category_icon_file(file):
    """
    Validate category icon images.
    Allowed: jpg, jpeg, png, webp. Max: 1 MB.
    """
    max_mb = getattr(settings, "MAX_CATEGORY_ICON_SIZE_MB", 1)
    _validate_extension(file.name, IMAGE_EXTENSIONS, "Category icon")
    _validate_file_size(file, max_mb, "Category icon")
    _validate_content_type(file, "Category icon")


def validate_document_file(file):
    """
    Validate identification/guarantee documents.
    Allowed: pdf, jpg, jpeg, png. Max: 10 MB.
    """
    max_mb = getattr(settings, "MAX_DOCUMENT_SIZE_MB", 10)
    _validate_extension(file.name, DOCUMENT_EXTENSIONS, "Document")
    _validate_file_size(file, max_mb, "Document")
    _validate_content_type(file, "Document")


def validate_proof_file(file):
    """
    Validate proof/receipt files.
    Allowed: pdf, jpg, jpeg, png, webp. Max: 5 MB.
    """
    max_mb = getattr(settings, "MAX_PROOF_FILE_SIZE_MB", 5)
    _validate_extension(file.name, PROOF_EXTENSIONS, "Proof file")
    _validate_file_size(file, max_mb, "Proof file")
    _validate_content_type(file, "Proof file")


def validate_wallet_recharge_receipt_file(file):
    """
    Validate wallet recharge receipts.
    Allowed defaults: pdf, jpg, jpeg, png, webp. Max default: 5 MB.
    """
    allowed_extensions = _normalize_extensions(
        getattr(
            settings,
            "WALLET_RECHARGE_RECEIPT_ALLOWED_EXTENSIONS",
            DEFAULT_WALLET_RECHARGE_RECEIPT_EXTENSIONS,
        )
    )
    allowed_content_types = getattr(
        settings,
        "WALLET_RECHARGE_RECEIPT_ALLOWED_CONTENT_TYPES",
        DEFAULT_WALLET_RECHARGE_RECEIPT_CONTENT_TYPES,
    )
    max_mb = getattr(settings, "MAX_WALLET_RECHARGE_RECEIPT_UPLOAD_MB", 5)
    _validate_extension(file.name, allowed_extensions, "Wallet recharge receipt")
    _validate_file_size(file, max_mb, "Wallet recharge receipt")
    _validate_content_type(file, "Wallet recharge receipt")
    _validate_allowed_content_type(file, allowed_content_types, "Wallet recharge receipt")
