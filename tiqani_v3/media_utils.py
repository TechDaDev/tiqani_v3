"""
Media utility helpers for signed URLs and safe file serialization.

Provides functions to generate signed/private file URLs and safe
metadata dictionaries for serializers, respecting the current
storage backend (local vs. S3).
"""

from django.conf import settings


def get_private_file_url(file_field, request=None):
    """
    Return the URL for a private file field.

    - If S3 is enabled: returns a short-lived signed URL via the storage backend.
    - If local: returns the local MEDIA_URL path.
    - If no file: returns None.

    Args:
        file_field: The Django FileField/ImageField value (or None).
        request: Optional Django request for building absolute local URLs.

    Returns:
        str or None
    """
    if not file_field:
        return None

    if settings.USE_S3_MEDIA:
        try:
            return file_field.url
        except Exception:
            return None

    # Local mode — return relative URL
    try:
        url = file_field.url
        if request and url.startswith("/"):
            url = request.build_absolute_uri(url)
        return url
    except Exception:
        return None


def serialize_private_file(file_field, request=None):
    """
    Return a safe metadata dict for a private file field.

    Includes name, size (bytes), and URL.
    Returns None if no file is present.

    Safe for authenticated serializers only — do not use in public serializers.
    """
    if not file_field:
        return None

    result = {
        "name": None,
        "size": None,
        "url": None,
    }

    try:
        result["name"] = file_field.name.split("/")[-1]
    except Exception:
        pass

    try:
        result["size"] = file_field.size
    except Exception:
        pass

    result["url"] = get_private_file_url(file_field, request)

    return result


def safe_file_metadata(file_field):
    """
    Return minimal metadata for a file field.
    Does NOT include the URL — safe for serializers where
    the URL should not be exposed (e.g. public endpoints).

    Returns None if no file is present.
    """
    if not file_field:
        return None

    result = {
        "name": None,
        "size": None,
    }

    try:
        result["name"] = file_field.name.split("/")[-1]
    except Exception:
        pass

    try:
        result["size"] = file_field.size
    except Exception:
        pass

    return result
