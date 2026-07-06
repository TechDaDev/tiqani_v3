from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from tempfile import TemporaryDirectory

User = get_user_model()


class CurrentUserAPITest(APITestCase):
    """Tests for GET/PATCH /api/accounts/me/."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/accounts/me/"
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Testpass123",
            role="client",
        )

    def test_anonymous_returns_401(self):
        """Anonymous GET /api/accounts/me/ returns 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_returns_200(self):
        """Authenticated GET /api/accounts/me/ returns 200."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    def test_patch_updates_name(self):
        """Authenticated PATCH can update first_name / last_name."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"first_name": "New", "last_name": "Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "New")
        self.assertEqual(self.user.last_name, "Name")

    def test_patch_cannot_change_role(self):
        """PATCH must not allow role change."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"role": "technician"}, format="json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "client")

    def test_patch_cannot_change_is_staff(self):
        """PATCH must not allow is_staff change."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"is_staff": True}, format="json")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)

    def test_authenticated_returns_absolute_profile_image_url(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.user.profile_image = SimpleUploadedFile(
                    "avatar.png",
                    b"small-image-bytes",
                    content_type="image/png",
                )
                self.user.save(update_fields=["profile_image"])

                self.client.force_authenticate(user=self.user)
                response = self.client.get(self.url, HTTP_HOST="api.testserver")

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(
                    response.data["profile_image"].startswith(
                        "http://api.testserver/media/"
                    )
                )
                self.assertEqual(
                    response.data["profile_image_url"], response.data["profile_image"]
                )
                self.assertNotIn(str(media_root), response.data["profile_image"])

    def test_login_returns_absolute_profile_image_url(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.user.profile_image = SimpleUploadedFile(
                    "avatar.png",
                    b"small-image-bytes",
                    content_type="image/png",
                )
                self.user.save(update_fields=["profile_image"])

                response = self.client.post(
                    "/api/auth/login/",
                    {"username": "testuser", "password": "Testpass123"},
                    format="json",
                    HTTP_HOST="api.testserver",
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                userdata = response.data["userdata"]
                self.assertTrue(
                    userdata["profile_image"].startswith(
                        "http://api.testserver/media/"
                    )
                )
                self.assertEqual(
                    userdata["profile_image_url"], userdata["profile_image"]
                )
                self.assertNotIn(str(media_root), userdata["profile_image"])
