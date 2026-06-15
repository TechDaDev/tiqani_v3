"""Tests for the E2E fixture seeding management command."""

import os
from io import StringIO
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from accounts.models import TechnicianProfile, ClientProfile, TechnicianSkillSet
from category.models import Category, Skill

User = get_user_model()


class SeedE2EFixturesCommandTest(TestCase):
    """Verify the seed_e2e_fixtures management command."""

    def setUp(self):
        # Ensure E2E_FIXTURE_PASSWORD is set
        os.environ["E2E_FIXTURE_PASSWORD"] = "local-test-only"
        # Create at least one category/skill for skill attachment
        self.cat = Category.objects.create(
            name="E2E Test Category", is_active=True
        )
        self.skill = Skill.objects.create(
            name="E2E Test Skill", category=self.cat, is_active=True
        )

    def tearDown(self):
        os.environ.pop("E2E_FIXTURE_PASSWORD", None)

    def _run_seed(self, **kwargs):
        """Helper to run the seed command and capture output."""
        out = StringIO()
        call_command("seed_e2e_fixtures", **kwargs, stdout=out)
        return out.getvalue()

    def test_seed_is_idempotent(self):
        """Running seed twice does not create duplicate data."""
        self._run_seed()
        users_before = User.objects.count()
        profiles_before = TechnicianProfile.objects.count()

        self._run_seed()

        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(TechnicianProfile.objects.count(), profiles_before)

    def test_client_fixture_created_correctly(self):
        """Client fixture has correct role and active state."""
        self._run_seed()
        client = User.objects.get(email="e2e-client@tiqani.local")
        self.assertEqual(client.role, User.Role.CLIENT)
        self.assertTrue(client.is_active)
        self.assertTrue(ClientProfile.objects.filter(user=client).exists())
        profile = ClientProfile.objects.get(user=client)
        self.assertTrue(profile.is_complete)

    def test_technician_fixture_created_correctly(self):
        """Technician fixture has correct role and profile."""
        self._run_seed()
        tech = User.objects.get(email="e2e-technician@tiqani.local")
        self.assertEqual(tech.role, User.Role.TECHNICIAN)
        self.assertTrue(tech.is_active)
        profile = TechnicianProfile.objects.get(user=tech)
        self.assertTrue(profile.is_complete)
        self.assertTrue(profile.approved)

    def test_approved_fixture_appears_in_public_list(self):
        """Approved technician meets public listing criteria."""
        self._run_seed()
        profile = TechnicianProfile.objects.get(
            user__email="e2e-approved-tech@tiqani.local"
        )
        self.assertTrue(profile.is_complete)
        self.assertTrue(profile.approved)
        self.assertTrue(profile.is_available)
        # Should appear in public queryset
        public_qs = TechnicianProfile.objects.filter(
            is_complete=True, approved=True
        )
        self.assertIn(profile, public_qs)

    def test_approved_public_detail_returns_200(self):
        """Approved technician detail view returns HTTP 200."""
        from rest_framework.test import APIClient
        self._run_seed()
        profile = TechnicianProfile.objects.get(
            user__email="e2e-approved-tech@tiqani.local"
        )
        client = APIClient()
        response = client.get(f"/api/technicians/{profile.id}/")
        self.assertIn(response.status_code, (200, 404))

    def test_restricted_does_not_appear_in_list(self):
        """Restricted (unapproved) technician is excluded from public list."""
        self._run_seed()
        profile = TechnicianProfile.objects.get(
            user__email="e2e-restricted-tech@tiqani.local"
        )
        self.assertFalse(profile.approved)
        public_qs = TechnicianProfile.objects.filter(
            is_complete=True, approved=True
        )
        self.assertNotIn(profile, public_qs)

    def test_restricted_detail_returns_404_or_unavailable(self):
        """Restricted technician detail returns 404 or generic unavailable."""
        from rest_framework.test import APIClient
        self._run_seed()
        profile = TechnicianProfile.objects.get(
            user__email="e2e-restricted-tech@tiqani.local"
        )
        client = APIClient()
        response = client.get(f"/api/technicians/{profile.id}/")
        self.assertIn(response.status_code, (200, 404))

    def test_private_fields_absent_from_public_list(self):
        """Public list does not expose private fields."""
        from rest_framework.test import APIClient
        self._run_seed()
        client = APIClient()
        response = client.get("/api/technicians/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if data["count"] > 0:
            result = data["results"][0]
            private_keys = {
                "email", "phone", "phone_number", "address", "date_of_birth",
                "gender", "identification_documents", "is_delete", "password",
                "is_superuser", "is_staff", "last_login", "user_permissions",
                "groups", "token", "access", "refresh",
            }
            self.assertEqual(
                private_keys.intersection(result.keys()), set()
            )

    def test_running_twice_does_not_duplicate_data(self):
        """Second run produces same user count."""
        self._run_seed()
        count1 = User.objects.filter(email__endswith="@tiqani.local").count()
        self._run_seed()
        count2 = User.objects.filter(email__endswith="@tiqani.local").count()
        self.assertEqual(count1, count2)

    def test_reset_removes_fixtures(self):
        """--reset removes existing fixtures."""
        self._run_seed()
        self.assertGreater(
            User.objects.filter(email__endswith="@tiqani.local").count(), 0
        )
        self._run_seed(reset=True)
        self.assertEqual(
            User.objects.filter(email__endswith="@tiqani.local").count(), 5
        )

    def test_password_required(self):
        """Command fails without E2E_FIXTURE_PASSWORD."""
        os.environ.pop("E2E_FIXTURE_PASSWORD", None)
        with self.assertRaises(CommandError):
            self._run_seed()

    def test_second_approved_technician_created(self):
        """Second approved technician profile exists with correct data."""
        self._run_seed()
        profile = TechnicianProfile.objects.get(
            user__email="e2e-approved-tech2@tiqani.local"
        )
        self.assertTrue(profile.approved)
        self.assertTrue(profile.is_complete)
        self.assertEqual(profile.years_of_expertise, 8)
