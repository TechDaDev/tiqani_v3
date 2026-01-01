from django.urls import path, include
from rest_framework.routers import DefaultRouter

from category.views import CategoryViewSet, SkillViewSet, SubSkillViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"skills", SkillViewSet, basename="skill")
router.register(r"sub-skills", SubSkillViewSet, basename="subskill")

urlpatterns = [
    path("", include(router.urls)),
]
