from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

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
        self.inactive_skill = Skill.objects.create(
            name="Inactive Skill", category=self.category, is_active=False,
        )
        SubSkill.objects.create(
            name="Inactive Child", skill=self.inactive_skill, is_active=True,
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

    def test_category_detail_returns_nested_active_skills_and_sub_skills(self):
        """Category detail includes a stable active taxonomy tree."""
        response = self.client.get(f"/api/categories/{self.category.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        skill_names = [skill["name"] for skill in response.data["skills"]]
        self.assertEqual(skill_names, ["Pipe Repair"])
        self.assertEqual(response.data["skills"][0]["sub_skills"][0]["name"], "Leaky Faucet")

    def test_category_list_supports_frontend_page_size_with_nested_taxonomy(self):
        """Category list returns the fast nested taxonomy shape used by the frontend."""
        response = self.client.get("/api/categories/?page_size=100")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category = next(item for item in response.data["results"] if item["name"] == "Plumbing")
        self.assertNotIn("skill_count", category)
        self.assertEqual(category["skills"][0]["name"], "Pipe Repair")
        self.assertEqual(category["skills"][0]["sub_skills"][0]["name"], "Leaky Faucet")

    def test_category_list_query_count_is_bounded_for_nested_taxonomy(self):
        """The taxonomy endpoint must not query once per skill or sub-skill."""
        for category_index in range(3):
            category = Category.objects.create(name=f"Category {category_index}", is_active=True)
            for skill_index in range(4):
                skill = Skill.objects.create(
                    name=f"Skill {category_index}-{skill_index}",
                    category=category,
                    is_active=True,
                )
                for sub_index in range(3):
                    SubSkill.objects.create(
                        name=f"Sub {category_index}-{skill_index}-{sub_index}",
                        skill=skill,
                        is_active=True,
                    )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/categories/?page_size=100")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(ctx), 8)
