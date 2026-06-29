"""
Management command to check media storage configuration.

Usage:
    python manage.py check_media_storage
    python manage.py check_media_storage --test-upload   # Only if S3 credentials exist
"""

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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
        self.stdout.write(self.style.MIGRATE_HEADING("Media and Static Storage Check"))
        self.stdout.write("=" * 55)

        # ── Mode ──────────────────────────────────────────────
        if settings.USE_S3_MEDIA:
            self._info(f"Media mode: S3-compatible (USE_S3_MEDIA=True)")
            self._check_s3_mode()
        else:
            self._info(f"Media mode: Local filesystem")
            self._check_local_mode()

        if getattr(settings, "USE_S3_STATIC", False):
            self._info("Static mode: S3-compatible (USE_S3_STATIC=True)")
            self._info(f"Static prefix: {settings.S3_STATIC_LOCATION}")
        else:
            self._info("Static mode: local/WhiteNoise")
            self._info(f"STATIC_ROOT: {settings.STATIC_ROOT}")

        # ── Upload limits (common) ────────────────────────────
        self._print_upload_limits()

        # ── Test upload ───────────────────────────────────────
        if options.get("test_upload"):
            self._test_uploads()

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
        self._info(f"Media prefix: {settings.S3_MEDIA_LOCATION}")
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

    def _save_and_delete(self, storage, label):
        test_content = ContentFile(b"test", name="test.txt")
        saved_path = storage.save("_check_storage/ping.txt", test_content)
        url = storage.url(saved_path)
        storage.delete(saved_path)
        self._info(f"{label} test upload succeeded. File saved and deleted.")
        self._info(f"{label} sample URL: {url[:80]}...")

    def _test_uploads(self):
        """Attempt test uploads to configured storage backends."""
        try:
            if settings.USE_S3_MEDIA:
                self._save_and_delete(default_storage, "Media")
            else:
                self._warn("Media test upload skipped: not in S3 mode.")

            if getattr(settings, "USE_S3_STATIC", False):
                self._save_and_delete(staticfiles_storage, "Static")
            else:
                self._warn("Static test upload skipped: not in S3 mode.")
        except Exception as e:
            self._error(f"Test upload failed: {e}")
