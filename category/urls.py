from django.urls import path, include
from rest_framework.routers import SimpleRouter

from category.views import CategoryViewSet, SkillViewSet, SubSkillViewSet

# Router for sub-resources; categories handled directly via .as_view()
skill_router = SimpleRouter()
skill_router.register(r"skills", SkillViewSet, basename="skill")
skill_router.register(r"sub-skills", SubSkillViewSet, basename="subskill")

urlpatterns = [
    # Category list & detail – at the root of /api/categories/
    path("", CategoryViewSet.as_view({"get": "list", "post": "create"}), name="category-list"),
    path("<uuid:id>/", CategoryViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="category-detail"),
    # Skills within a category context, and stand-alone skill/sub-skill resources
    path("", include(skill_router.urls)),
]
