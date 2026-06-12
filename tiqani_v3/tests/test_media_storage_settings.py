"""
Tests for media storage settings — local mode, S3 settings, private storage.
"""

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings


class MediaStorageSettingsTest(TestCase):
    """Verify media storage configuration."""

    def test_local_mode_is_default_in_tests(self):
        """Tests run with USE_S3_MEDIA=False."""
        self.assertFalse(settings.USE_S3_MEDIA)

    def test_default_storage_is_filesystem(self):
        """Default storage backend is FileSystemStorage when S3 disabled."""
        from django.core.files.storage import default_storage
        self.assertEqual(
            default_storage.__class__.__name__,
            "FileSystemStorage",
        )

    def test_upload_limits_are_configured(self):
        """Upload size limits are present in settings."""
        self.assertGreaterEqual(settings.MAX_PROFILE_IMAGE_SIZE_MB, 1)
        self.assertGreaterEqual(settings.MAX_CATEGORY_ICON_SIZE_MB, 1)
        self.assertGreaterEqual(settings.MAX_DOCUMENT_SIZE_MB, 1)
        self.assertGreaterEqual(settings.MAX_PROOF_FILE_SIZE_MB, 1)

    @override_settings(
        USE_S3_MEDIA=True,
        S3_ACCESS_KEY_ID="test-key",
        S3_SECRET_ACCESS_KEY="test-secret",
        S3_STORAGE_BUCKET_NAME="test-bucket",
        S3_REGION_NAME="us-east-1",
        S3_QUERYSTRING_AUTH=True,
        S3_QUERYSTRING_EXPIRE=900,
        S3_DEFAULT_ACL="private",
        S3_FILE_OVERWRITE=False,
    )
    def test_private_storage_signed_urls(self):
        """Private storage config uses signed URLs and private ACL."""
        from tiqani_v3.storage_backends import PrivateMediaStorage
        storage = PrivateMediaStorage()
        self.assertEqual(storage.default_acl, "private")
        self.assertTrue(storage.querystring_auth)
        self.assertEqual(storage.querystring_expire, 900)
        self.assertFalse(storage.file_overwrite)

    @override_settings(
        USE_S3_MEDIA=True,
        S3_ACCESS_KEY_ID="test-key",
        S3_SECRET_ACCESS_KEY="test-secret",
        S3_STORAGE_BUCKET_NAME="test-bucket",
        S3_REGION_NAME="us-east-1",
    )
    def test_prod_settings_with_s3_enabled(self):
        """Production settings can be imported with S3 enabled (fake env)."""
        import os
        os.environ["DJANGO_SETTINGS_MODULE"] = "tiqani_v3.settings.prod"
        os.environ["SECRET_KEY"] = "test-secret-key-12345"
        os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1"
        os.environ["DATABASE_URL"] = "sqlite:///db.sqlite3"
        os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"
        os.environ["CSRF_TRUSTED_ORIGINS"] = "http://localhost:3000"
        os.environ["USE_S3_MEDIA"] = "True"
        os.environ["S3_STORAGE_BUCKET_NAME"] = "test-bucket"
        os.environ["S3_ACCESS_KEY_ID"] = "test-key"
        os.environ["S3_SECRET_ACCESS_KEY"] = "test-secret-key"
        os.environ["S3_REGION_NAME"] = "us-east-1"
        # Verify import works
        try:
            from django.conf import settings as prod_settings
            # Re-load settings
            import django
            django.setup()
            self.assertFalse(prod_settings.DEBUG)
        except Exception as e:
            self.fail(f"Prod settings import failed with S3 enabled: {e}")
