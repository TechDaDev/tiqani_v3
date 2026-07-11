from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import TechnicianProfile, BaseProfile, TechnicianSkillSet
from category.models import Category, Skill, SubSkill

User = get_user_model()


class TechnicianAPITest(APITestCase):
    """Tests for /api/technicians/ endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("technician_list")
        self.me_url = reverse("technician_profile")
        self.skills_url = reverse("technician_skills")
        self.incomplete_url = reverse("incomplete_fields")

        # Create an approved technician
        self.approved_user = User.objects.create_user(
            username="approvedtech", email="approved@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234567", governorate="Baghdad", address="Addr",
            first_name="Approved", last_name="Tech",
        )
        self.approved_profile = TechnicianProfile.objects.create(
            user=self.approved_user, approved=True,
            job_title="Plumber", about="Expert plumber",
            years_of_expertise=5,
        )
        # Mark profile complete (bypass FileField requirement for tests)
        TechnicianProfile.objects.filter(pk=self.approved_profile.pk).update(is_complete=True)
        self.approved_profile.refresh_from_db()

        # Create an unapproved technician
        self.unapproved_user = User.objects.create_user(
            username="unapprovedtech", email="unapproved@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234568", governorate="Basra", address="Addr2",
        )
        self.unapproved_profile = TechnicianProfile.objects.create(
            user=self.unapproved_user, approved=False,
        )

        # Create a non-technician user
        self.client_user = User.objects.create_user(
            username="clientuser", email="client@example.com",
            password="Testpass123", role="client",
        )

        self.category_a = Category.objects.create(name="Category A", is_active=True, order=1)
        self.category_b = Category.objects.create(name="Category B", is_active=True, order=2)
        self.skill_a1 = Skill.objects.create(name="Skill A1", category=self.category_a, is_active=True, order=1)
        self.skill_a2 = Skill.objects.create(name="Skill A2", category=self.category_a, is_active=True, order=2)
        self.skill_b1 = Skill.objects.create(name="Skill B1", category=self.category_b, is_active=True, order=1)
        self.sub_a1 = SubSkill.objects.create(name="Sub A1", skill=self.skill_a1, is_active=True, order=1)
        self.sub_b1 = SubSkill.objects.create(name="Sub B1", skill=self.skill_b1, is_active=True, order=1)

    def test_public_list_returns_200(self):
        """Public GET /api/technicians/ returns 200."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_approved_technician_in_public_list(self):
        """Approved technician appears in public list."""
        response = self.client.get(self.list_url)
        results = response.data["results"]
        user_ids = [r["user_id"] for r in results]
        self.assertIn(str(self.approved_user.id), user_ids)

    def test_unapproved_technician_not_in_public_list(self):
        """Unapproved technician does not appear in public list."""
        response = self.client.get(self.list_url)
        results = response.data["results"]
        user_ids = [r["user_id"] for r in results]
        self.assertNotIn(str(self.unapproved_user.id), user_ids)

    def test_technician_can_get_own_profile(self):
        """Technician can GET /api/technicians/me/."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_can_patch_own_profile(self):
        """Technician can PATCH /api/technicians/me/."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.patch(self.me_url, {"job_title": "Senior Plumber"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.approved_profile.refresh_from_db()
        self.assertEqual(self.approved_profile.job_title, "Senior Plumber")

    def test_anonymous_me_returns_401(self):
        """Anonymous GET /api/technicians/me/ returns 401."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_technician_profile_rejects_client_user(self):
        """Client user cannot access technician profile endpoint."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.me_url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_technician_get_incomplete_fields(self):
        """Incomplete technician returns missing fields, no 500."""
        self.client.force_authenticate(user=self.unapproved_user)
        response = self.client.get(self.incomplete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("incomplete_fields", data)
        self.assertIn("is_complete", data)
        # Unapproved tech has minimal profile
        self.assertGreater(len(data["incomplete_fields"]), 0)
        self.assertFalse(data["is_complete"])

    def test_technician_skills_get(self):
        """Technician can GET own skills."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.get(self.skills_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_skills_rejects_client(self):
        """Client user cannot access technician skills endpoint."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.skills_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_can_patch_skills(self):
        """Technician can PATCH skills with valid data."""
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.patch(self.skills_url, {"categories": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_can_save_multiple_skills_from_same_category(self):
        self.client.force_authenticate(user=self.approved_user)

        response = self.client.patch(
            self.skills_url,
            {"skills": [str(self.skill_a1.id), str(self.skill_a2.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(response.data["skills"], [self.skill_a1.id, self.skill_a2.id])
        self.assertEqual(response.data["categories"], [self.category_a.id])

    def test_technician_can_save_skills_from_different_categories(self):
        self.client.force_authenticate(user=self.approved_user)

        response = self.client.patch(
            self.skills_url,
            {"skills": [str(self.skill_a1.id), str(self.skill_b1.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(response.data["skills"], [self.skill_a1.id, self.skill_b1.id])
        self.assertCountEqual(response.data["categories"], [self.category_a.id, self.category_b.id])
        category_names = {item["category"]["name"] for item in response.data["skills_detail"]}
        self.assertEqual(category_names, {"Category A", "Category B"})

    def test_technician_can_save_sub_skills_from_different_categories(self):
        self.client.force_authenticate(user=self.approved_user)

        response = self.client.patch(
            self.skills_url,
            {"sub_skills": [str(self.sub_a1.id), str(self.sub_b1.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(response.data["sub_skills"], [self.sub_a1.id, self.sub_b1.id])
        self.assertCountEqual(response.data["categories"], [self.category_a.id, self.category_b.id])
        category_names = {item["category"]["name"] for item in response.data["sub_skills_detail"]}
        self.assertEqual(category_names, {"Category A", "Category B"})

    def test_technician_profile_response_returns_all_selected_skills(self):
        skill_set = TechnicianSkillSet.objects.create(technician=self.approved_profile)
        skill_set.skills.add(self.skill_a1, self.skill_b1)
        skill_set.sub_skills.add(self.sub_a1, self.sub_b1)
        skill_set.categories.add(self.category_a, self.category_b)
        self.client.force_authenticate(user=self.approved_user)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["skill_sets"]["skills_detail"]), 2)
        self.assertEqual(len(response.data["skill_sets"]["sub_skills_detail"]), 2)

    def test_profile_completion_requires_at_least_one_skill_or_sub_skill(self):
        self.client.force_authenticate(user=self.approved_user)
        TechnicianSkillSet.objects.filter(technician=self.approved_profile).delete()

        response = self.client.get(self.incomplete_url)
        self.assertIn("skills", response.data["incomplete_fields"])

        skill_set = TechnicianSkillSet.objects.create(technician=self.approved_profile)
        skill_set.sub_skills.add(self.sub_a1)
        skill_set.categories.add(self.category_a)
        self.approved_profile.save()
        response = self.client.get(self.incomplete_url)
        self.assertNotIn("skills", response.data["incomplete_fields"])

    def test_invalid_skill_id_rejected(self):
        self.client.force_authenticate(user=self.approved_user)

        response = self.client.patch(
            self.skills_url,
            {"skills": ["00000000-0000-0000-0000-000000000000"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_selected_ids_are_stored_once(self):
        self.client.force_authenticate(user=self.approved_user)

        response = self.client.patch(
            self.skills_url,
            {"skills": [str(self.skill_a1.id), str(self.skill_a1.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        skill_set = TechnicianSkillSet.objects.get(technician=self.approved_profile)
        self.assertEqual(skill_set.skills.count(), 1)


class TechnicianDetailAPITest(APITestCase):
    """Tests for GET /api/technicians/<id>/ detail endpoint.

    Critical regression: marketplace list returns user_id (User UUID) but
    detail must accept that same user_id in the URL. User.id and
    TechnicianProfile.id are different UUIDs — the fix uses user__id lookup.
    """

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("technician_list")

        self.user = User.objects.create_user(
            username="detailtech", email="detail@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234561", governorate="Baghdad", address="Addr",
            first_name="Detail", last_name="Tech",
        )
        self.profile = TechnicianProfile.objects.create(
            user=self.user, approved=True,
            job_title="Electrician", about="Expert electrician",
            years_of_expertise=3,
        )
        TechnicianProfile.objects.filter(pk=self.profile.pk).update(is_complete=True)
        self.profile.refresh_from_db()

        self.unapproved_user = User.objects.create_user(
            username="unapprovedtech2", email="unapproved2@example.com",
            password="Testpass123", role="technician",
            phone_number="07701234562", governorate="Basra", address="Addr2",
        )
        self.unapproved_profile = TechnicianProfile.objects.create(
            user=self.unapproved_user, approved=False,
        )

    def _detail_url(self, identifier):
        return reverse("technician_detail", kwargs={"id": identifier})

    def test_list_returns_profile_id(self):
        """Marketplace list includes profile_id field."""
        response = self.client.get(self.list_url)
        results = response.data["results"]
        profile_ids = [r["profile_id"] for r in results]
        self.assertIn(str(self.profile.id), profile_ids)

    def test_list_user_id_fetches_detail(self):
        """user_id from marketplace list works as detail URL param.

        Core regression: frontend passes User UUID to detail URL.
        View must look up by user__id.
        """
        detail_url = self._detail_url(str(self.user.id))
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], str(self.user.id))

    def test_profile_id_does_not_fetch_detail(self):
        """Profile UUID (TechnicianProfile.id) is NOT a valid detail URL param.

        Detail endpoint looks up by user__id (User UUID). Profile UUID is a
        different UUID and must not accidentally match a user.
        """
        detail_url = self._detail_url(str(self.profile.id))
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_id_and_profile_id_are_different(self):
        """User UUID and Profile UUID are different values."""
        self.assertNotEqual(str(self.user.id), str(self.profile.id))

    def test_nonexistent_identifier_returns_404(self):
        """Non-existent UUID returns controlled 404."""
        detail_url = self._detail_url("00000000-0000-0000-0000-000000000000")
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn("TechnicianProfile", str(response.data.get("detail", "")))
        self.assertNotIn("matches the given query", str(response.data.get("detail", "")))

    def test_unapproved_profile_returns_404_for_public(self):
        """Unapproved technician returns 404."""
        detail_url = self._detail_url(str(self.unapproved_user.id))
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unapproved_profile_visible_to_owner(self):
        """Unapproved technician visible to owner."""
        self.client.force_authenticate(user=self.unapproved_user)
        detail_url = self._detail_url(str(self.unapproved_user.id))
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unapproved_profile_visible_to_admin(self):
        """Unapproved technician visible to admin."""
        admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Admin123",
        )
        self.client.force_authenticate(user=admin_user)
        detail_url = self._detail_url(str(self.unapproved_user.id))
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_response_contains_profile_id(self):
        """Detail response includes profile_id."""
        detail_url = self._detail_url(str(self.user.id))
        response = self.client.get(detail_url)
        self.assertIn("profile_id", response.data)
        self.assertEqual(response.data["profile_id"], str(self.profile.id))

    def test_detail_response_contains_user_id(self):
        """Detail response includes user_id."""
        detail_url = self._detail_url(str(self.user.id))
        response = self.client.get(detail_url)
        self.assertIn("user_id", response.data)
        self.assertEqual(response.data["user_id"], str(self.user.id))

    def test_detail_response_has_expected_public_fields(self):
        """Detail response has expected public fields."""
        detail_url = self._detail_url(str(self.user.id))
        response = self.client.get(detail_url)
        # Must include both profile_id and user_id
        self.assertIn("profile_id", response.data)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)
        self.assertIn("full_name", response.data)
        self.assertIn("governorate", response.data)
        self.assertIn("job_title", response.data)
        self.assertIn("about", response.data)
        self.assertIn("years_of_expertise", response.data)
        self.assertIn("is_available", response.data)
        self.assertIn("rate", response.data)
        self.assertIn("is_complete", response.data)

    def test_raw_django_exception_not_leaked(self):
        """404 response has no raw Django exception text."""
        detail_url = self._detail_url(str(self.unapproved_user.id))
        response = self.client.get(detail_url)
        detail = str(response.data.get("detail", ""))
        self.assertNotIn("TechnicianProfile", detail)
        self.assertNotIn("get() returned more", detail)
