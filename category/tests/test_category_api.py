from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from category.models import Category, Skill, SubSkill

User = get_user_model()


class CategoryAPITest(APITestCase):
    """Tests for public category endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name="Plumbing", is_active=True,
            description="All plumbing services",
        )
        self.inactive_category = Category.objects.create(
            name="Inactive Cat", is_active=False,
        )
        self.skill = Skill.objects.create(
            name="Pipe Repair", category=self.category, is_active=True,
        )
        self.sub_skill = SubSkill.objects.create(
            name="Leaky Faucet", skill=self.skill, is_active=True,
        )

    def test_public_can_list_categories(self):
        """Public can list active categories."""
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.data["results"]]
        self.assertIn("Plumbing", names)

    def test_public_can_retrieve_category_detail(self):
        """Public can retrieve category detail."""
        response = self.client.get(f"/api/categories/{self.category.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Plumbing")

    def test_public_can_list_skills(self):
        """Public can list skills."""
        response = self.client.get("/api/categories/skills/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.data["results"]]
        self.assertIn("Pipe Repair", names)

    def test_public_can_list_sub_skills(self):
        """Public can list sub-skills."""
        response = self.client.get("/api/categories/sub-skills/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.data["results"]]
        self.assertIn("Leaky Faucet", names)

    def test_inactive_category_hidden_from_public(self):
        """Inactive categories are hidden from anonymous users."""
        response = self.client.get("/api/categories/")
        names = [r["name"] for r in response.data["results"]]
        self.assertNotIn("Inactive Cat", names)
