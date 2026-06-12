"""
S3-compatible storage backend classes.

Uses django-storages S3Boto3Storage with configuration from settings.

PrivateMediaStorage — default private storage with signed URLs.
PublicMediaStorage — for explicitly public assets only.
"""

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class PrivateMediaStorage(S3Boto3Storage):
    """
    Private media storage with signed URLs.
    Files are not publicly accessible; access requires short-lived signed URLs.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("access_key", settings.S3_ACCESS_KEY_ID)
        kwargs.setdefault("secret_key", settings.S3_SECRET_ACCESS_KEY)
        kwargs.setdefault("bucket_name", settings.S3_STORAGE_BUCKET_NAME)
        kwargs.setdefault("region_name", settings.S3_REGION_NAME)
        kwargs.setdefault("endpoint_url", settings.S3_ENDPOINT_URL or None)
        kwargs.setdefault("custom_domain", settings.S3_CUSTOM_DOMAIN or None)
        kwargs.setdefault("signature_version", settings.S3_SIGNATURE_VERSION)
        kwargs.setdefault("addressing_style", settings.S3_ADDRESSING_STYLE)
        kwargs.setdefault("default_acl", "private")
        kwargs.setdefault("querystring_auth", settings.S3_QUERYSTRING_AUTH)
        kwargs.setdefault("querystring_expire", settings.S3_QUERYSTRING_EXPIRE)
        kwargs.setdefault("file_overwrite", settings.S3_FILE_OVERWRITE)
        kwargs.setdefault("location", settings.S3_PRIVATE_MEDIA_LOCATION)
        kwargs.setdefault(
            "object_parameters",
            {"CacheControl": settings.S3_OBJECT_PARAMETERS_CACHE_CONTROL},
        )
        super().__init__(*args, **kwargs)


class PublicMediaStorage(S3Boto3Storage):
    """
    Public media storage for assets that are explicitly safe to serve publicly.
    Use sparingly — only for assets like category icons that need public URLs.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("access_key", settings.S3_ACCESS_KEY_ID)
        kwargs.setdefault("secret_key", settings.S3_SECRET_ACCESS_KEY)
        kwargs.setdefault("bucket_name", settings.S3_STORAGE_BUCKET_NAME)
        kwargs.setdefault("region_name", settings.S3_REGION_NAME)
        kwargs.setdefault("endpoint_url", settings.S3_ENDPOINT_URL or None)
        kwargs.setdefault("custom_domain", settings.S3_CUSTOM_DOMAIN or None)
        kwargs.setdefault("signature_version", settings.S3_SIGNATURE_VERSION)
        kwargs.setdefault("default_acl", "private")  # Still private unless overridden
        kwargs.setdefault("querystring_auth", True)
        kwargs.setdefault("querystring_expire", settings.S3_QUERYSTRING_EXPIRE)
        kwargs.setdefault("file_overwrite", settings.S3_FILE_OVERWRITE)
        kwargs.setdefault("location", settings.S3_PUBLIC_MEDIA_LOCATION)
        kwargs.setdefault(
            "object_parameters",
            {"CacheControl": settings.S3_OBJECT_PARAMETERS_CACHE_CONTROL},
        )
        super().__init__(*args, **kwargs)
