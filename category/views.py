from django.db import models
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination

from category.models import Category, Skill, SubSkill
from category.serializers import (
	CategorySerializer,
	CategorySlimSerializer,
	SkillSerializer,
	SkillSlimSerializer,
	SubSkillSerializer,
)


def _bool_param(value):
	if value is None:
		return None
	return value.lower() in {"1", "true", "yes", "y"}


class DefaultPagination(PageNumberPagination):
	page_size = 20
	page_size_query_param = "page_size"
	max_page_size = 100


class IsStaffOrReadOnly(permissions.BasePermission):
	"""Allow public reads; restrict writes to staff."""

	def has_permission(self, request, view):
		if request.method in permissions.SAFE_METHODS:
			return True
		return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
	"""Public list/detail; staff can create/update/delete."""

	lookup_field = "id"
	permission_classes = [IsStaffOrReadOnly]
	pagination_class = DefaultPagination

	def get_queryset(self):
		qs = (
			Category.objects.select_related("parent")
			.prefetch_related(
				Prefetch(
					"skills",
					queryset=Skill.objects.filter(is_delete=False, is_active=True)
					.prefetch_related(
						Prefetch(
							"sub_skills",
							queryset=SubSkill.objects.filter(is_delete=False, is_active=True).order_by("order", "name"),
						)
					)
					.order_by("order", "name"),
				),
				"children",
			)
		)

		# Exclude soft-deleted for non-staff
		if not (self.request.user and self.request.user.is_staff):
			qs = qs.filter(is_delete=False, is_active=True)

		q = self.request.query_params.get("q")
		if q:
			qs = qs.filter(models.Q(name__icontains=q) | models.Q(description__icontains=q))

		parent_id = self.request.query_params.get("parent")
		if parent_id:
			qs = qs.filter(parent_id=parent_id)

		for param in ["is_featured", "is_active"]:
			val = _bool_param(self.request.query_params.get(param))
			if val is not None:
				qs = qs.filter(**{param: val})

		ordering = self.request.query_params.get("ordering") or "order,name"
		allowed = {"order", "name", "created_at", "updated_at"}
		clean_ordering = []
		for part in ordering.split(","):
			part = part.strip()
			bare = part.lstrip("-")
			if bare in allowed:
				clean_ordering.append(part)
		if clean_ordering:
			qs = qs.order_by(*clean_ordering)

		return qs

	def get_serializer_class(self):
		if self.action == "list" and self.request.query_params.get("fields") == "basic":
			return CategorySlimSerializer
		return CategorySerializer

	@method_decorator(cache_page(300))
	def list(self, request, *args, **kwargs):
		return super().list(request, *args, **kwargs)

	@method_decorator(cache_page(300))
	def retrieve(self, request, *args, **kwargs):
		return super().retrieve(request, *args, **kwargs)

	def perform_destroy(self, instance):
		# Soft delete via API destroy
		instance.is_delete = True
		instance.save(update_fields=["is_delete", "updated_at"])


class SkillViewSet(viewsets.ModelViewSet):
	"""Public read; staff write. Supports category filtering."""

	permission_classes = [IsStaffOrReadOnly]
	pagination_class = DefaultPagination

	def get_queryset(self):
		qs = Skill.objects.select_related("category").prefetch_related("sub_skills")

		if not (self.request.user and self.request.user.is_staff):
			qs = qs.filter(is_delete=False, is_active=True, category__is_delete=False, category__is_active=True)

		q = self.request.query_params.get("q")
		if q:
			qs = qs.filter(models.Q(name__icontains=q) | models.Q(description__icontains=q))

		category_id = self.request.query_params.get("category_id")
		if category_id:
			qs = qs.filter(category_id=category_id)

		val = _bool_param(self.request.query_params.get("is_active"))
		if val is not None:
			qs = qs.filter(is_active=val)

		ordering = self.request.query_params.get("ordering") or "order,name"
		allowed = {"order", "name", "created_at", "updated_at"}
		clean_ordering = []
		for part in ordering.split(","):
			part = part.strip()
			bare = part.lstrip("-")
			if bare in allowed:
				clean_ordering.append(part)
		if clean_ordering:
			qs = qs.order_by(*clean_ordering)

		return qs

	def get_serializer_class(self):
		if self.action == "list" and self.request.query_params.get("fields") == "basic":
			return SkillSlimSerializer
		return SkillSerializer

	@method_decorator(cache_page(300))
	def list(self, request, *args, **kwargs):
		return super().list(request, *args, **kwargs)

	@method_decorator(cache_page(300))
	def retrieve(self, request, *args, **kwargs):
		return super().retrieve(request, *args, **kwargs)

	def perform_destroy(self, instance):
		instance.is_delete = True
		instance.save(update_fields=["is_delete", "updated_at"])


class SubSkillViewSet(viewsets.ModelViewSet):
	"""Public read; staff write. Filters by skill and difficulty."""

	permission_classes = [IsStaffOrReadOnly]
	pagination_class = DefaultPagination

	def get_queryset(self):
		qs = SubSkill.objects.select_related("skill", "skill__category")

		if not (self.request.user and self.request.user.is_staff):
			qs = qs.filter(
				is_delete=False,
				is_active=True,
				skill__is_delete=False,
				skill__is_active=True,
				skill__category__is_delete=False,
				skill__category__is_active=True,
			)

		q = self.request.query_params.get("q")
		if q:
			qs = qs.filter(models.Q(name__icontains=q) | models.Q(description__icontains=q))

		skill_id = self.request.query_params.get("skill_id")
		if skill_id:
			qs = qs.filter(skill_id=skill_id)

		difficulty = self.request.query_params.get("difficulty_level")
		if difficulty:
			qs = qs.filter(difficulty_level=difficulty)

		val = _bool_param(self.request.query_params.get("is_active"))
		if val is not None:
			qs = qs.filter(is_active=val)

		ordering = self.request.query_params.get("ordering") or "order,name"
		allowed = {"order", "name", "created_at", "updated_at"}
		clean_ordering = []
		for part in ordering.split(","):
			part = part.strip()
			bare = part.lstrip("-")
			if bare in allowed:
				clean_ordering.append(part)
		if clean_ordering:
			qs = qs.order_by(*clean_ordering)

		return qs

	serializer_class = SubSkillSerializer

	@method_decorator(cache_page(300))
	def list(self, request, *args, **kwargs):
		return super().list(request, *args, **kwargs)

	@method_decorator(cache_page(300))
	def retrieve(self, request, *args, **kwargs):
		return super().retrieve(request, *args, **kwargs)

	def perform_destroy(self, instance):
		instance.is_delete = True
		instance.save(update_fields=["is_delete", "updated_at"])
