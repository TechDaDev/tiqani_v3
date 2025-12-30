import uuid
from django.db import models
from django.utils import timezone


class Category(models.Model):
	"""
	Service categories that technicians can specialize in.
	Supports hierarchical category structure with parent-child relationships.
	Examples: HVAC, Plumbing, Electrical, General Repairs
	"""
	
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	name = models.CharField(
		max_length=255, 
		unique=True,
		db_index=True,
		help_text="Category name (e.g., HVAC, Plumbing)"
	)
	description = models.TextField(
		blank=True, 
		null=True,
		help_text="Detailed category description"
	)
	icon = models.CharField(
		max_length=50, 
		blank=True, 
		null=True,
		help_text="Icon class or name (e.g., fas fa-wrench)"
	)
	parent = models.ForeignKey(
		'self', 
		null=True, 
		blank=True, 
		on_delete=models.CASCADE, 
		related_name='children',
		help_text="Parent category for hierarchical structure"
	)  # Related name 'children' allows access to child categories
	
	# Status & Audit
	is_active = models.BooleanField(
		default=True,
		db_index=True,
		help_text="Category is available for selection"
	)
	is_featured = models.BooleanField(
		default=False,
		db_index=True,
		help_text="Featured on home page"
	)
	order = models.PositiveIntegerField(
		default=0,
		help_text="Display order in listings"
	)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name_plural = 'Categories'
		indexes = [
			models.Index(fields=['name']),
			models.Index(fields=['is_active']),
			models.Index(fields=['is_featured']),
			models.Index(fields=['parent']),
			models.Index(fields=['order']),
		]
		ordering = ['order', 'name']

	def __str__(self):
		"""Return category name with parent if hierarchical"""
		if self.parent:
			return f"{self.parent.name} → {self.name}"
		return self.name

	def get_full_hierarchy(self):
		"""
		Get full category path from root to this category.
		Returns: List of category names from parent to child
		"""
		hierarchy = [self.name]
		current = self.parent
		while current:
			hierarchy.insert(0, current.name)
			current = current.parent
		return hierarchy

	def get_all_skills(self):
		"""
		Get all skills in this category and sub-categories.
		Useful for displaying comprehensive skill lists.
		"""
		from category.models import Skill
		all_skills = list(Skill.objects.filter(category=self))
		for child_category in self.children.all():
			all_skills.extend(child_category.get_all_skills())
		return all_skills

	def get_all_sub_skills(self):
		"""
		Get all sub-skills from all skills in this category and sub-categories.
		"""
		sub_skills = []
		all_skills = self.get_all_skills()
		for skill in all_skills:
			sub_skills.extend(skill.sub_skills.all())
		return sub_skills

	@property
	def skill_count(self):
		"""Total number of skills in this category"""
		return len(self.get_all_skills())

	@property
	def technician_count(self):
		"""Number of technicians specializing in this category"""
		from accounts.models import TechnicianSkillSet
		# Avoid DISTINCT ON (not supported by SQLite); use values()+distinct()
		return (
			TechnicianSkillSet.objects
			.filter(categories=self)
			.values('technician')
			.distinct()
			.count()
		)


class Skill(models.Model):
	"""
	Skills that fall under a specific category.
	Examples: Installation, Repair, Maintenance, Troubleshooting
	"""
	
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	category = models.ForeignKey(
		Category, 
		on_delete=models.CASCADE, 
		related_name='skills',
		help_text="Parent category"
	)
	name = models.CharField(
		max_length=255,
		help_text="Skill name (e.g., Installation, Repair)"
	)
	description = models.TextField(
		blank=True, 
		null=True,
		help_text="Detailed skill description"
	)
	
	# Status & Organization
	is_active = models.BooleanField(
		default=True,
		db_index=True,
		help_text="Skill is available for selection"
	)
	order = models.PositiveIntegerField(
		default=0,
		help_text="Display order within category"
	)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('category', 'name')]
		indexes = [
			models.Index(fields=['category']),
			models.Index(fields=['is_active']),
			models.Index(fields=['order']),
		]
		ordering = ['category', 'order', 'name']

	def __str__(self):
		"""Return skill name with category"""
		return f"{self.name} ({self.category.name})"

	@property
	def technician_count(self):
		"""Number of technicians with this skill"""
		from accounts.models import TechnicianSkillSet
		return (
			TechnicianSkillSet.objects
			.filter(skills=self)
			.values('technician')
			.distinct()
			.count()
		)


class SubSkill(models.Model):
	"""
	Specialized sub-skills that fall under a specific skill.
	Examples: AC Installation, Heat Pump Installation, Ductwork
	Provides granular skill tracking for technician expertise.
	"""
	
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	skill = models.ForeignKey(
		Skill, 
		on_delete=models.CASCADE, 
		related_name='sub_skills',
		help_text="Parent skill"
	)
	name = models.CharField(
		max_length=255,
		help_text="Sub-skill name (e.g., AC Installation, Heat Pump Installation)"
	)
	description = models.TextField(
		blank=True, 
		null=True,
		help_text="Detailed sub-skill description"
	)
	
	# Status & Organization
	is_active = models.BooleanField(
		default=True,
		db_index=True,
		help_text="Sub-skill is available for selection"
	)
	difficulty_level = models.CharField(
		max_length=20,
		choices=[
			('beginner', 'Beginner'),
			('intermediate', 'Intermediate'),
			('advanced', 'Advanced'),
			('expert', 'Expert'),
		],
		default='intermediate',
		help_text="Difficulty level of this sub-skill"
	)
	order = models.PositiveIntegerField(
		default=0,
		help_text="Display order within skill"
	)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = [('skill', 'name')]
		indexes = [
			models.Index(fields=['skill']),
			models.Index(fields=['is_active']),
			models.Index(fields=['difficulty_level']),
			models.Index(fields=['order']),
		]
		ordering = ['skill', 'order', 'name']

	def __str__(self):
		"""Return sub-skill name with full hierarchy"""
		return f"{self.name} ({self.skill.category.name} → {self.skill.name})"

	@property
	def technician_count(self):
		"""Number of technicians with this sub-skill"""
		from accounts.models import TechnicianSkillSet
		return (
			TechnicianSkillSet.objects
			.filter(sub_skills=self)
			.values('technician')
			.distinct()
			.count()
		)

	@property
	def full_path(self):
		"""Get full skill hierarchy path"""
		return f"{self.skill.category.name} → {self.skill.name} → {self.name}"
