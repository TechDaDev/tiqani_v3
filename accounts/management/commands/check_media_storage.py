"""
Management command to check media storage configuration.

Usage:
    python manage.py check_media_storage
    python manage.py check_media_storage --test-upload   # Only if S3 credentials exist
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check media storage configuration and upload limits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-upload",
            action="store_true",
            help="Upload a tiny test object to verify S3 connectivity (requires credentials).",
        )

    def _info(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✓  {msg}"))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f"  ⚠  {msg}"))

    def _error(self, msg):
        self.stdout.write(self.style.ERROR(f"  ✗  {msg}"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Media Storage Check"))
        self.stdout.write("=" * 55)

        # ── Mode ──────────────────────────────────────────────
        if settings.USE_S3_MEDIA:
            self._info(f"Media mode: S3-compatible (USE_S3_MEDIA=True)")
            self._check_s3_mode()
        else:
            self._info(f"Media mode: Local filesystem")
            self._check_local_mode()

        # ── Upload limits (common) ────────────────────────────
        self._print_upload_limits()

        # ── Test upload ───────────────────────────────────────
        if options.get("test_upload"):
            self._test_upload()

        self.stdout.write(self.style.MIGRATE_HEADING("Check complete."))

    def _check_local_mode(self):
        """Check local media configuration."""
        self._info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        self._info(f"MEDIA_URL: {settings.MEDIA_URL}")

    def _check_s3_mode(self):
        """Check S3 media configuration for potential issues."""
        required_vars = {
            "S3_STORAGE_BUCKET_NAME": settings.S3_STORAGE_BUCKET_NAME,
            "S3_ACCESS_KEY_ID": settings.S3_ACCESS_KEY_ID,
            "S3_SECRET_ACCESS_KEY": settings.S3_SECRET_ACCESS_KEY,
        }
        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            self._error(f"Missing required S3 variables: {', '.join(missing)}")
        else:
            self._info("Required S3 environment variables are present (secret key hidden).")

        self._info(f"Bucket: {settings.S3_STORAGE_BUCKET_NAME}")
        self._info(f"Endpoint URL: {settings.S3_ENDPOINT_URL or '(AWS default)'}")
        self._info(f"Region: {settings.S3_REGION_NAME}")
        self._info(f"Signed URL expiry: {settings.S3_QUERYSTRING_EXPIRE}s ({settings.S3_QUERYSTRING_EXPIRE // 60} min)")

        if not settings.S3_QUERYSTRING_AUTH:
            self._warn("S3_QUERYSTRING_AUTH is disabled — files may be publicly accessible!")
        if settings.S3_DEFAULT_ACL != "private":
            self._warn(f"S3_DEFAULT_ACL is '{settings.S3_DEFAULT_ACL}', not 'private'!")
        if settings.S3_QUERYSTRING_EXPIRE > 86400:
            self._warn(f"Signed URL expiry is very long ({settings.S3_QUERYSTRING_EXPIRE}s). Consider reducing.")
        if settings.S3_FILE_OVERWRITE:
            self._warn("S3_FILE_OVERWRITE is enabled — files can be overwritten!")

    def _print_upload_limits(self):
        """Print current upload limits."""
        self._info(f"Max profile image: {getattr(settings, 'MAX_PROFILE_IMAGE_SIZE_MB', 2)} MB")
        self._info(f"Max category icon: {getattr(settings, 'MAX_CATEGORY_ICON_SIZE_MB', 1)} MB")
        self._info(f"Max document: {getattr(settings, 'MAX_DOCUMENT_SIZE_MB', 10)} MB")
        self._info(f"Max proof file: {getattr(settings, 'MAX_PROOF_FILE_SIZE_MB', 5)} MB")

    def _test_upload(self):
        """Attempt a test upload to S3."""
        if not settings.USE_S3_MEDIA:
            self._warn("--test-upload skipped: not in S3 mode.")
            return

        try:
            from django.core.files.base import ContentFile
            from storages.backends.s3boto3 import S3Boto3Storage

            storage = S3Boto3Storage(
                access_key=settings.S3_ACCESS_KEY_ID,
                secret_key=settings.S3_SECRET_ACCESS_KEY,
                bucket_name=settings.S3_STORAGE_BUCKET_NAME,
                region_name=settings.S3_REGION_NAME,
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                default_acl="private",
                querystring_auth=True,
                querystring_expire=60,
                location="_check_media_storage",
            )

            test_content = ContentFile(b"test", name="test.txt")
            saved_path = storage.save("ping.txt", test_content)
            url = storage.url(saved_path)
            storage.delete(saved_path)

            self._info(f"Test upload succeeded. File saved and deleted.")
            self._info(f"Sample signed URL: {url[:80]}...")
        except Exception as e:
            self._error(f"Test upload failed: {e}")
