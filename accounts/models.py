import os
import uuid
import random
import string
from decimal import Decimal
from datetime import date

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, MinValueValidator
from tiqani_v3.file_validators import validate_profile_image_file, validate_document_file
from django.contrib.auth.models import AbstractUser

# --- Configuration & Helpers ---

def universal_file_path(instance, filename):
    """
    Generates a clean, unique file path based on the instance's defined upload folder.
    Format: <upload_folder>/<uuid_segment>.<extension>
    """
    ext = filename.split('.')[-1].lower()
    folder = getattr(instance, 'upload_folder', 'uploads/misc')
    # Use the instance ID if available, otherwise a new UUID to prevent collisions
    uid_part = str(instance.id).split('-')[-1] if instance.id else uuid.uuid4().hex[:8]
    return os.path.join(folder, f"{uid_part}.{ext}")

# Validators
PHONE_REGEX = RegexValidator(
    regex=r'^07[5|7|8]\d{8}$',
    message=_("Phone number must be 11 digits starting with 075, 077, or 078.")
)

GITHUB_REGEX = RegexValidator(
    regex=r'^(https?:\/\/)?(www\.)?github\.com\/[A-Za-z0-9_-]+\/?$',
    message=_("Enter a valid GitHub profile URL.")
)

LINKEDIN_REGEX = RegexValidator(
    regex=r'^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[A-Za-z0-9_-]+\/?$',
    message=_("Enter a valid LinkedIn profile URL.")
)

# Constants
IRAQI_GOVERNORATES = [
    ('Baghdad', 'بغداد'), ('Basra', 'البصرة'), ('Nineveh', 'نينوى'),
    ('Erbil', 'أربيل'), ('Sulaymaniyah', 'السليمانية'), ('Kirkuk', 'كركوك'),
    ('Duhok', 'دهوك'), ('Najaf', 'النجف'), ('Karbala', 'كربلاء'),
    ('Anbar', 'الأنبار'), ('Babil', 'بابل'), ('Maysan', 'ميسان'),
    ('Wasit', 'واسط'), ('Dhi Qar', 'ذي قار'), ('Muthanna', 'المثنى'),
    ('Qadisiyyah', 'القادسية'), ('Salah al-Din', 'صلاح الدين'),
    ('Diyala', 'ديالى'), ('Halabja', 'حلبجة')
]

# --- Base Abstract Models ---

class TimestampedModel(models.Model):
    """
    Abstract base class providing UUID primary keys, soft-delete, 
    and timestamping (created/updated).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_delete = models.BooleanField(default=False, verbose_name=_("Deleted"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        abstract = True


class BaseProfile(TimestampedModel):
    """
    Abstract base for user profiles handling completion logic.
    """
    is_complete = models.BooleanField(default=False, db_index=True, verbose_name=_("Profile Complete"))
    
    # Fields required for the profile to be considered "complete"
    # Subclasses should extend these lists
    REQ_USER_FIELDS = ['phone_number', 'governorate', 'address']
    REQ_PROFILE_FIELDS = []

    class Meta:
        abstract = True

    @property
    def completion_percentage(self):
        """Calculates rough percentage of profile completion."""
        fields = self.REQ_USER_FIELDS + self.REQ_PROFILE_FIELDS
        if not fields: return 100
        filled = 0
        
        # Check User fields
        for f in self.REQ_USER_FIELDS:
            if getattr(self.user, f, None): filled += 1
            
        # Check Profile fields
        for f in self.REQ_PROFILE_FIELDS:
            val = getattr(self, f, None)
            if val is not None:
                if isinstance(val, (int, Decimal)) and val < 0: continue
                if isinstance(val, str) and not val.strip(): continue
                filled += 1
        
        return int((filled / len(fields)) * 100)

    def calculate_completion(self):
        """Boolean check for completion."""
        return self.completion_percentage == 100

    def get_incomplete_fields(self):
        """Returns list of field names that are empty/missing."""
        missing = []
        for f in self.REQ_USER_FIELDS:
            if not getattr(self.user, f, None): missing.append(f)
        for f in self.REQ_PROFILE_FIELDS:
            val = getattr(self, f, None)
            if not val: missing.append(f)
        return missing

    # Backward-compatible alias for admin and internal use
    get_missing_fields = get_incomplete_fields

    def save(self, *args, **kwargs):
        self.is_complete = self.calculate_completion()
        super().save(*args, **kwargs)


# --- Primary User Model ---

class CustomUser(AbstractUser, TimestampedModel):
    class Role(models.TextChoices):
        CLIENT = 'client', _('Client')
        TECHNICIAN = 'technician', _('Technician')
        DEALERSHIP = 'dealership', _('Dealership')
        ADMIN = 'admin', _('Admin')

    class Gender(models.TextChoices):
        MALE = 'male', _('Male')
        FEMALE = 'female', _('Female')

    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.CLIENT,
        verbose_name=_("User Role")
    )
    phone_number = models.CharField(
        validators=[PHONE_REGEX], 
        max_length=11, 
        blank=True, 
        null=True, 
        unique=True,
        verbose_name=_("Phone Number")
    )
    governorate = models.CharField(
        choices=IRAQI_GOVERNORATES, 
        max_length=50, 
        null=True, 
        blank=True,
        verbose_name=_("Governorate")
    )
    address = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Address"))
    gender = models.CharField(max_length=6, choices=Gender.choices, null=True, blank=True, verbose_name=_("Gender"))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_("Date of Birth"))
    profile_image = models.ImageField(
        upload_to=universal_file_path,
        null=True, blank=True,
        validators=[validate_profile_image_file],
        verbose_name=_("Avatar"),
    )

    upload_folder = 'users/avatars'
    REQUIRED_FIELDS = [] # Username/Email handled by AbstractUser logic

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=['role']), 
            models.Index(fields=['governorate'])
        ]

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def __str__(self):
        return f"{self.username} | {self.get_role_display()}"


# --- Profile Implementations ---

class TechnicianProfile(BaseProfile):
    """
    Extended profile for Technicians including professional details and stats.
    """
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='technician_profile'
    )
    is_available = models.BooleanField(default=True, db_index=True, verbose_name=_("Available for Work"))
    approved = models.BooleanField(default=False, db_index=True, verbose_name=_("Admin Approved"))
    
    job_title = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text=_("e.g., HVAC Specialist, Full-Stack Developer"),
        verbose_name=_("Job Title")
    )
    identification_documents = models.FileField(
        upload_to=universal_file_path,
        null=True, blank=True,
        validators=[validate_document_file],
        verbose_name=_("ID Documents")
    )
    github = models.URLField(max_length=255, validators=[GITHUB_REGEX], blank=True, null=True)
    linkedin = models.URLField(max_length=255, validators=[LINKEDIN_REGEX], blank=True, null=True)
    
    about = models.TextField(null=True, blank=True, verbose_name=_("Bio"))
    years_of_expertise = models.PositiveSmallIntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name=_("Years of Experience")
    )
    rate = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Rating")
    )
    
    last_active = models.DateTimeField(null=True, blank=True, db_index=True)

    upload_folder = 'technicians/docs'
    
    REQ_USER_FIELDS = BaseProfile.REQ_USER_FIELDS + ['gender', 'date_of_birth', 'profile_image']
    REQ_PROFILE_FIELDS = ['job_title', 'about', 'years_of_expertise', 'identification_documents']

    class Meta(BaseProfile.Meta):
        ordering = ['-created_at']
        verbose_name = _("Technician Profile")
        indexes = [
            models.Index(fields=['is_available', 'approved']),
            models.Index(fields=['rate', 'approved']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Tech)"

    def update_rating(self):
        """Recalculates average rating from public + verified reviews."""
        if hasattr(self, 'reviews_received'):
            qs = self.reviews_received.filter(is_public=True, is_verified=True)
            avg = qs.aggregate(models.Avg('rating'))['rating__avg']
            self.rate = round(avg, 2) if avg else Decimal('0.00')
            self.save(update_fields=['rate'])

    @property
    def is_online(self):
        if not self.last_active: 
            return False
        return (timezone.now() - self.last_active).total_seconds() < 300


class ClientProfile(BaseProfile):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='client_profile'
    )
    
    REQ_USER_FIELDS = BaseProfile.REQ_USER_FIELDS + ['gender', 'date_of_birth']

    class Meta(BaseProfile.Meta):
        ordering = ['-created_at']
        verbose_name = _("Client Profile")

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} (client)"

    def calculate_completion(self):
        # Business logic: Client must be 18+ to be "complete"
        basic_check = super().calculate_completion()
        age_valid = self.user.age is not None and self.user.age >= 18
        return basic_check and age_valid


class AdminProfile(BaseProfile):
    class AdminRole(models.TextChoices):
        SYSTEM_ADMIN = 'system_admin', _('System Admin')
        MODERATOR = 'content_moderator', _('Moderator')
        FINANCE = 'finance_admin', _('Finance')
        ACCOUNT_MANAGER = 'account_manager', _('Account Manager')

    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='admin_profile'
    )
    role = models.CharField(max_length=50, choices=AdminRole.choices, default=AdminRole.SYSTEM_ADMIN)
    notes = models.TextField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta(BaseProfile.Meta):
        verbose_name = _("Admin Profile")

    def save(self, *args, **kwargs):
        # Business Logic: Enforce staff status for admins
        if not self.user.is_staff:
            self.user.is_staff = True
            self.user.save(update_fields=['is_staff'])
        super().save(*args, **kwargs)


# --- Security ---

class OTPVerification(TimestampedModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes')
    otp_code = models.CharField(max_length=6)
    verification_id = models.CharField(max_length=32, unique=True)
    is_used = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _("OTP Code")

    @classmethod
    def generate_otp(cls, user):
        """Business logic to create a secure OTP."""
        return cls.objects.create(
            user=user,
            otp_code=''.join(random.choices(string.digits, k=6)),
            verification_id=uuid.uuid4().hex
        )

    def is_valid(self):
        """Checks if OTP is unused and within 10 minutes validity."""
        expiry_seconds = 600
        age = (timezone.now() - self.created_at).total_seconds()
        return not self.is_used and age < expiry_seconds


# --- Technician Specifics ---

class TechnicianSkillSet(TimestampedModel):
    """
    Links skills to a technician.
    Relationship fixed: Linked TO the technician (OneToOne), 
    rather than the technician linking to a generic SkillSet.
    """
    technician = models.OneToOneField(
        TechnicianProfile, 
        on_delete=models.CASCADE, 
        related_name='skill_set'
    )
    # String references used assuming 'category' app exists
    categories = models.ManyToManyField('category.Category', blank=True)
    skills = models.ManyToManyField('category.Skill', blank=True)
    sub_skills = models.ManyToManyField('category.SubSkill', blank=True)

    def __str__(self):
        return f"Skills: {self.technician.user.username}"


class TechnicianImage(TimestampedModel):
    """
    Enhanced to act as a Portfolio Carousel.
    """
    technician = models.ForeignKey(
        TechnicianProfile, 
        on_delete=models.CASCADE, 
        related_name='portfolio_images'
    )
    image = models.ImageField(
        upload_to=universal_file_path,
        validators=[validate_profile_image_file],
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    
    # Carousel Logic
    display_order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Sort Order"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Cover Image"))

    upload_folder = 'technicians/portfolio'

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = _("Portfolio Image")
        verbose_name_plural = _("Portfolio Images")

    def __str__(self):
        return f"Img: {self.technician.user.username} ({self.id})"