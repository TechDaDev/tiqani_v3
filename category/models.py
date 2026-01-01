import uuid
from django.db import models


class TimestampedModel(models.Model):
    """Centralizes ID, soft-delete, and timestamp logic."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimestampedModel):
    """Service categories with optional parent for hierarchy."""

    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Category name (e.g., HVAC, Plumbing)",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed category description",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon class or name (e.g., fas fa-wrench)",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="Parent category for hierarchical structure",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Category is available for selection",
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Featured on home page",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in listings",
    )

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["order"]),
        ]
        ordering = ["order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def get_full_hierarchy(self):
        """Return full category path from root to this category."""

        hierarchy = [self.name]
        current = self.parent
        while current:
            hierarchy.insert(0, current.name)
            current = current.parent
        return hierarchy

    def get_all_skills(self):
        """Return all skills in this category and its sub-categories."""

        from category.models import Skill

        all_skills = list(Skill.objects.filter(category=self))
        for child_category in self.children.all():
            all_skills.extend(child_category.get_all_skills())
        return all_skills

    def get_all_sub_skills(self):
        """Return all sub-skills from this category tree."""

        sub_skills = []
        all_skills = self.get_all_skills()
        for skill in all_skills:
            sub_skills.extend(skill.sub_skills.all())
        return sub_skills

    @property
    def skill_count(self):
        return len(self.get_all_skills())

    @property
    def technician_count(self):
        from accounts.models import TechnicianSkillSet

        return (
            TechnicianSkillSet.objects.filter(categories=self)
            .values("technician")
            .distinct()
            .count()
        )


class Skill(TimestampedModel):
    """Skills that belong to a category."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="skills",
        help_text="Parent category",
    )
    name = models.CharField(
        max_length=255,
        help_text="Skill name (e.g., Installation, Repair)",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed skill description",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Skill is available for selection",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within category",
    )

    class Meta:
        unique_together = [("category", "name")]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["order"]),
        ]
        ordering = ["category", "order", "name"]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    @property
    def technician_count(self):
        from accounts.models import TechnicianSkillSet

        return (
            TechnicianSkillSet.objects.filter(skills=self)
            .values("technician")
            .distinct()
            .count()
        )


class SubSkill(TimestampedModel):
    """Sub-skills that refine a parent skill."""

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="sub_skills",
        help_text="Parent skill",
    )
    name = models.CharField(
        max_length=255,
        help_text="Sub-skill name (e.g., AC Installation, Heat Pump Installation)",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed sub-skill description",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Sub-skill is available for selection",
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
            ("expert", "Expert"),
        ],
        default="intermediate",
        help_text="Difficulty level of this sub-skill",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within skill",
    )

    class Meta:
        unique_together = [("skill", "name")]
        indexes = [
            models.Index(fields=["skill"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["difficulty_level"]),
            models.Index(fields=["order"]),
        ]
        ordering = ["skill", "order", "name"]

    def __str__(self):
        return f"{self.name} ({self.skill.category.name} → {self.skill.name})"

    @property
    def technician_count(self):
        from accounts.models import TechnicianSkillSet

        return (
            TechnicianSkillSet.objects.filter(sub_skills=self)
            .values("technician")
            .distinct()
            .count()
        )

    @property
    def full_path(self):
        return f"{self.skill.category.name} → {self.skill.name} → {self.name}"
