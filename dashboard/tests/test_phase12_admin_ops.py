import importlib
import sys
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AdminProfile, CustomUser, TechnicianProfile
from notification.models import ActivityLog
from tiqani_v3.file_validators import validate_document_file, validate_profile_image_file


class Phase12AdminOperationsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = CustomUser.objects.create_superuser(
            username="phase12-admin",
            email="phase12-admin@example.com",
            password="pass12345",
            role=CustomUser.Role.ADMIN,
        )
        AdminProfile.objects.create(user=self.staff, role=AdminProfile.AdminRole.SYSTEM_ADMIN)
        self.user = CustomUser.objects.create_user(
            username="phase12-client",
            email="phase12-client@example.com",
            password="pass12345",
            role=CustomUser.Role.CLIENT,
            is_active=True,
        )
        self.tech_user = CustomUser.objects.create_user(
            username="phase12-tech",
            email="phase12-tech@example.com",
            password="pass12345",
            role=CustomUser.Role.TECHNICIAN,
            is_active=True,
        )
        self.tech = TechnicianProfile.objects.create(user=self.tech_user, job_title="Security Tech")

    def test_staff_can_load_admin_dashboard_alias(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.data)
        self.assertIn("technicians", response.data)

    def test_staff_can_load_platform_statistics_alias(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/platform-statistics/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("finance", response.data)

    def test_admin_payments_alias_is_staff_only(self):
        self.client.force_authenticate(self.user)
        denied = self.client.get("/api/admin/payments/")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.staff)
        allowed = self.client.get("/api/admin/payments/")
        self.assertEqual(allowed.status_code, 200)

    def test_admin_refunds_alias_is_staff_only(self):
        self.client.force_authenticate(self.user)
        denied = self.client.get("/api/admin/refunds/")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.staff)
        allowed = self.client.get("/api/admin/refunds/")
        self.assertEqual(allowed.status_code, 200)

    def test_participant_denied_admin_dashboard(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_user_suspend_requires_reason(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/admin/users/{self.user.id}/suspend/", {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("reason", response.data)

    def test_user_suspend_records_audit_state(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/admin/users/{self.user.id}/suspend/",
            {"reason": "Phase 12 policy test"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        event = ActivityLog.objects.get(verb="user_suspended", target_id=self.user.id)
        self.assertEqual(event.metadata["previous_state"], {"is_active": True})
        self.assertEqual(event.metadata["new_state"], {"is_active": False})
        self.assertEqual(event.metadata["reason"], "Phase 12 policy test")

    def test_user_restore_records_audit_state(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/admin/users/{self.user.id}/restore/",
            {"reason": "Appeal accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(ActivityLog.objects.filter(verb="user_restored", target_id=self.user.id).exists())

    def test_technician_approve_requires_reason(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(f"/api/admin/technicians/{self.tech.id}/approve/", {})
        self.assertEqual(response.status_code, 400)

    def test_technician_approve_records_audit(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/admin/technicians/{self.tech.id}/approve/",
            {"reason": "Documents verified"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.tech.refresh_from_db()
        self.assertTrue(self.tech.approved)
        self.assertTrue(ActivityLog.objects.filter(verb="technician_approved", target_id=self.tech.id).exists())

    def test_technician_suspend_records_audit(self):
        self.tech.approved = True
        self.tech.is_available = True
        self.tech.save(update_fields=["approved", "is_available"])
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/admin/technicians/{self.tech.id}/suspend/",
            {"reason": "Credential issue"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.tech.refresh_from_db()
        self.assertFalse(self.tech.approved)
        self.assertFalse(self.tech.is_available)
        self.assertTrue(ActivityLog.objects.filter(verb="technician_suspended", target_id=self.tech.id).exists())

    def test_audit_events_alias_lists_activity(self):
        ActivityLog.objects.create(verb="phase12_event", actor=self.staff, audience="admin")
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/admin/audit-events/")
        self.assertEqual(response.status_code, 200)
        verbs = [item["verb"] for item in response.data["results"]]
        self.assertIn("phase12_event", verbs)

    def test_platform_health_is_staff_only(self):
        self.client.force_authenticate(self.user)
        denied = self.client.get("/api/admin/platform-health/")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.staff)
        allowed = self.client.get("/api/admin/platform-health/")
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("database", allowed.data)

    def test_ready_endpoint_contains_no_secret_values(self):
        response = self.client.get("/api/ready/")
        self.assertIn(response.status_code, (200, 503))
        body = response.json()
        self.assertNotIn("debug", body)
        self.assertNotIn("SECRET", str(body).upper())
        self.assertNotIn("PASSWORD", str(body).upper())

    def test_health_alias_has_safe_summary(self):
        response = self.client.get("/api/health/")
        self.assertIn(response.status_code, (200, 503))
        body = response.json()
        self.assertIn("database", body)
        self.assertNotIn("database_error", body)

    def test_admin_write_throttle_scope_configured(self):
        self.assertIn("admin_write", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])


class Phase12UploadValidationTests(TestCase):
    def test_profile_image_rejects_executable_extension(self):
        upload = SimpleUploadedFile("avatar.exe", b"fake", content_type="application/x-msdownload")
        with self.assertRaises(Exception):
            validate_profile_image_file(upload)

    @override_settings(MAX_DOCUMENT_SIZE_MB=1)
    def test_document_rejects_oversized_file(self):
        upload = SimpleUploadedFile("doc.pdf", b"x" * (1024 * 1024 + 1), content_type="application/pdf")
        with self.assertRaises(Exception):
            validate_document_file(upload)


class Phase12ProductionSettingsTests(TestCase):
    def test_prod_settings_reject_placeholder_secret(self):
        with mock.patch.dict(
            "os.environ",
            {
                "DJANGO_SECRET_KEY": "change-me-placeholder",
                "ALLOWED_HOSTS": "example.com",
                "DATABASE_URL": "postgres://u:p@localhost:5432/db",
                "CORS_ALLOWED_ORIGINS": "https://example.com",
                "CSRF_TRUSTED_ORIGINS": "https://example.com",
            },
            clear=False,
        ):
            sys.modules.pop("tiqani_v3.settings.prod", None)
            with self.assertRaises(RuntimeError):
                importlib.import_module("tiqani_v3.settings.prod")
