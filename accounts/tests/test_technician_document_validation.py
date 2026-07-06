from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.forms.models import modelform_factory
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import TechnicianProfile

User = get_user_model()


class TechnicianDocumentAdminFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="legacy_zip_tech",
            password="Testpass123",
            role="technician",
        )
        self.profile = TechnicianProfile.objects.create(
            user=self.user,
            job_title="Legacy Technician",
            identification_documents="technicians/docs/518550fdb371.zip",
        )
        self.form_class = modelform_factory(
            TechnicianProfile,
            fields=["job_title", "identification_documents", "github", "linkedin"],
        )

    def test_existing_legacy_zip_does_not_block_unchanged_admin_save(self):
        form = self.form_class(
            data={
                "job_title": "Updated Technician",
                "github": "",
                "linkedin": "",
            },
            files={},
            instance=self.profile,
        )

        self.assertTrue(form.is_valid(), form.errors.as_data())
        saved = form.save()

        self.assertEqual(saved.job_title, "Updated Technician")
        self.assertEqual(
            saved.identification_documents.name,
            "technicians/docs/518550fdb371.zip",
        )

    def test_existing_legacy_zip_can_be_cleared(self):
        form = self.form_class(
            data={
                "job_title": "Legacy Technician",
                "github": "",
                "linkedin": "",
                "identification_documents-clear": "on",
            },
            files={},
            instance=self.profile,
        )

        self.assertTrue(form.is_valid(), form.errors.as_data())
        saved = form.save()

        self.assertFalse(saved.identification_documents)

    def test_existing_legacy_zip_can_be_replaced_by_allowed_pdf(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                form = self.form_class(
                    data={
                        "job_title": "Legacy Technician",
                        "github": "",
                        "linkedin": "",
                    },
                    files={
                        "identification_documents": SimpleUploadedFile(
                            "replacement.pdf",
                            b"%PDF-1.4 replacement",
                            content_type="application/pdf",
                        )
                    },
                    instance=self.profile,
                )

                self.assertTrue(form.is_valid(), form.errors.as_data())
                saved = form.save()

                self.assertTrue(saved.identification_documents.name.endswith(".pdf"))

    def test_new_zip_replacement_is_rejected(self):
        form = self.form_class(
            data={
                "job_title": "Legacy Technician",
                "github": "",
                "linkedin": "",
            },
            files={
                "identification_documents": SimpleUploadedFile(
                    "replacement.zip",
                    b"PK\x03\x04",
                    content_type="application/zip",
                )
            },
            instance=self.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("identification_documents", form.errors)
        self.assertIn("not allowed", str(form.errors["identification_documents"]))


class TechnicianDocumentAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="api_doc_tech",
            password="Testpass123",
            role="technician",
        )
        self.profile = TechnicianProfile.objects.create(
            user=self.user,
            job_title="API Technician",
            about="Experienced technician",
            years_of_expertise=3,
            github="https://github.com/api-tech",
            linkedin="https://linkedin.com/in/api-tech",
            identification_documents="technicians/docs/518550fdb371.zip",
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/technicians/me/"

    def test_profile_patch_ignores_unchanged_legacy_zip(self):
        response = self.client.patch(
            self.url,
            {"job_title": "API Technician Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.job_title, "API Technician Updated")
        self.assertEqual(
            self.profile.identification_documents.name,
            "technicians/docs/518550fdb371.zip",
        )

    def test_new_zip_upload_is_rejected(self):
        response = self.client.patch(
            self.url,
            {
                "identification_documents": SimpleUploadedFile(
                    "replacement.zip",
                    b"PK\x03\x04",
                    content_type="application/zip",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("identification_documents", response.data)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.identification_documents.name,
            "technicians/docs/518550fdb371.zip",
        )

    def test_allowed_pdf_upload_succeeds(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.patch(
                    self.url,
                    {
                        "identification_documents": SimpleUploadedFile(
                            "replacement.pdf",
                            b"%PDF-1.4 replacement",
                            content_type="application/pdf",
                        )
                    },
                    format="multipart",
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.profile.refresh_from_db()
                self.assertTrue(
                    self.profile.identification_documents.name.endswith(".pdf")
                )
