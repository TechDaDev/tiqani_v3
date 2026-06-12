"""
Tests for file validators — allowed extensions, blocked types, size limits.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from tiqani_v3.file_validators import (
    validate_profile_image_file,
    validate_category_icon_file,
    validate_document_file,
    validate_proof_file,
)


class MockFile:
    """Minimal file-like object for validator testing."""

    def __init__(self, name, size=1024, content_type=None):
        self.name = name
        self.size = size
        self.content_type = content_type


class FileValidatorsTest(TestCase):
    """Test all file validators."""

    # ── Allowed extensions ─────────────────────────────────────

    def test_profile_image_allows_jpg(self):
        f = MockFile("avatar.jpg", size=100 * 1024)
        try:
            validate_profile_image_file(f)
        except ValidationError:
            self.fail("jpg should be allowed for profile images")

    def test_profile_image_allows_png(self):
        f = MockFile("avatar.png", size=100 * 1024)
        try:
            validate_profile_image_file(f)
        except ValidationError:
            self.fail("png should be allowed for profile images")

    def test_profile_image_allows_webp(self):
        f = MockFile("avatar.webp", size=100 * 1024)
        try:
            validate_profile_image_file(f)
        except ValidationError:
            self.fail("webp should be allowed for profile images")

    def test_document_allows_pdf(self):
        f = MockFile("doc.pdf", size=100 * 1024)
        try:
            validate_document_file(f)
        except ValidationError:
            self.fail("pdf should be allowed for documents")

    def test_proof_allows_webp(self):
        f = MockFile("proof.webp", size=100 * 1024)
        try:
            validate_proof_file(f)
        except ValidationError:
            self.fail("webp should be allowed for proof files")

    # ── Blocked extensions ─────────────────────────────────────

    def test_profile_image_rejects_exe(self):
        f = MockFile("malware.exe", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_profile_image_rejects_zip(self):
        f = MockFile("archive.zip", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_document_rejects_svg(self):
        f = MockFile("vector.svg", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_document_file(f)

    def test_document_rejects_mp4(self):
        f = MockFile("video.mp4", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_document_file(f)

    def test_profile_image_rejects_html(self):
        f = MockFile("page.html", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_profile_image_rejects_js(self):
        f = MockFile("script.js", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_profile_image_rejects_without_extension(self):
        f = MockFile("README", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_all_validators_block_exe(self):
        """All validators should block .exe files."""
        for validator in [validate_profile_image_file, validate_category_icon_file,
                          validate_document_file, validate_proof_file]:
            f = MockFile("malware.exe", size=100 * 1024)
            with self.assertRaises(ValidationError):
                validator(f)

    def test_all_validators_block_zip(self):
        """All validators should block .zip files."""
        for validator in [validate_profile_image_file, validate_category_icon_file,
                          validate_document_file, validate_proof_file]:
            f = MockFile("archive.zip", size=100 * 1024)
            with self.assertRaises(ValidationError):
                validator(f)

    # ── Size limits ────────────────────────────────────────────

    def test_profile_image_rejects_oversized(self):
        """Profile image > 2 MB should be rejected."""
        f = MockFile("large.jpg", size=3 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_category_icon_rejects_oversized(self):
        """Category icon > 1 MB should be rejected."""
        f = MockFile("large.png", size=2 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validate_category_icon_file(f)

    def test_document_rejects_oversized(self):
        """Document > 10 MB should be rejected."""
        f = MockFile("large.pdf", size=11 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validate_document_file(f)

    def test_proof_rejects_oversized(self):
        """Proof file > 5 MB should be rejected."""
        f = MockFile("large.pdf", size=6 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validate_proof_file(f)

    # ── Edge cases ─────────────────────────────────────────────

    def test_empty_filename_raises_error(self):
        """None/empty filename should raise error."""
        f = MockFile("", size=100)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)

    def test_case_insensitive_extensions(self):
        """Validators should handle uppercase extensions."""
        for ext in [".JPG", ".JPEG", ".PNG", ".WEBP"]:
            f = MockFile(f"avatar{ext}", size=100 * 1024)
            try:
                validate_profile_image_file(f)
            except ValidationError:
                self.fail(f"Uppercase {ext} should be allowed")

    def test_double_extension_rejected(self):
        """Files like image.jpg.exe should be caught by extension check."""
        f = MockFile("image.jpg.exe", size=100 * 1024)
        with self.assertRaises(ValidationError):
            validate_profile_image_file(f)
