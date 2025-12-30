import os
import uuid
import random
import string
from decimal import Decimal
from datetime import date, timedelta

from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser

# --- Configuration & Helpers ---

def universal_file_path(instance, filename):
    """Generates paths based on the 'upload_folder' attribute defined in models."""
    ext = filename.split('.')[-1]
    folder = getattr(instance, 'upload_folder', 'uploads')
    uid_part = str(instance.id).split('-')[-1]
    return os.path.join(folder, f"{uid_part}.{ext}")

PHONE_REGEX = RegexValidator(
    regex=r'^07[5|7|8]\d{8}$',
    message="Phone number must be 11 digits (077/078/075)."
)

IRAQI_GOVERNORATES = [
    ('Baghdad', 'بغداد'), ('Basra', 'البصرة'), ('Nineveh', 'نينوى'),
    ('Erbil', 'أربيل'), ('Sulaymaniyah', 'السليمانية'), ('Kirkuk', 'كركوك'),
    ('Duhok', 'دهوك'), ('Najaf', 'النجف'), ('Karbala', 'كربلاء'),
    ('Anbar', 'الأنبار'), ('Babil', 'بابل'), ('Maysan', 'ميسان'),
    ('Wasit', 'واسط'), ('Dhi Qar', 'ذي قار'), ('Muthanna', 'المثنى'),
    ('Qadisiyyah', 'القادسية'), ('Salah al-Din', 'صلاح الدين'), ('Diyala', 'ديالى'),
]

# --- Base Abstract Models ---

class TimestampedModel(models.Model):
    """Centralizes ID, soft-delete, and timestamp logic."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class BaseProfile(TimestampedModel):
    """
    Abstract profile logic handling automatic completion status.
    Uses save() hooks to avoid the complexity of signals.
    """
    is_complete = models.BooleanField(default=False, db_index=True)
    
    # Required field sets to be defined/extended in subclasses
    REQ_USER_FIELDS = ['phone_number', 'profile_image', 'governorate', 'address']
    REQ_PROFILE_FIELDS = []

    class Meta:
        abstract = True

    def calculate_completion(self):
        """Verifies if all required fields (User + Profile level) are populated."""
        user = self.user
        for field in self.REQ_USER_FIELDS:
            if not getattr(user, field): return False
        
        for field in self.REQ_PROFILE_FIELDS:
            val = getattr(self, field)
            if not val or (isinstance(val, (int, Decimal)) and val <= 0):
                return False
        return True

    def get_incomplete_fields(self):
        """Helper for frontend to show which fields are missing."""
        missing = [f for f in self.REQ_USER_FIELDS if not getattr(self.user, f)]
        missing += [f for f in self.REQ_PROFILE_FIELDS if not getattr(self, f)]
        return missing

    def save(self, *args, **kwargs):
        # Hook: Update completion flag before saving
        self.is_complete = self.calculate_completion()
        super().save(*args, **kwargs)

# --- Primary User Model ---

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Client'), 
        ('technician', 'Technician'),
        ('admin', 'Admin'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone_number = models.CharField(validators=[PHONE_REGEX], max_length=11, blank=True, null=True, unique=True)
    governorate = models.CharField(choices=IRAQI_GOVERNORATES, max_length=50, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=6, choices=[('male', 'Male'), ('female', 'Female')], null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_image = models.ImageField(upload_to=universal_file_path, null=True, blank=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    upload_folder = 'Profile'

    class Meta:
        indexes = [models.Index(fields=['role']), models.Index(fields=['governorate'])]

    @property
    def age(self):
        if not self.date_of_birth: return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def __str__(self):
        return f"{self.username} ({self.role})"

# --- Profile Implementations ---

class TechnicianProfile(BaseProfile):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='technician_profile')
    is_available = models.BooleanField(default=True, db_index=True)
    approved = models.BooleanField(default=False, db_index=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)
    identification_documents = models.FileField(upload_to=universal_file_path, null=True, blank=True)
    url1 = models.URLField(max_length=255, null=True, blank=True)
    url2 = models.URLField(max_length=255, null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    years_of_expertise = models.PositiveIntegerField(default=0)
    rate = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    skill_sets = models.OneToOneField('TechnicianSkillSet', on_delete=models.SET_NULL, null=True, blank=True)
    last_active = models.DateTimeField(null=True, blank=True, db_index=True)

    upload_folder = 'technicians/profile_images'
    REQ_USER_FIELDS = BaseProfile.REQ_USER_FIELDS + ['gender', 'date_of_birth']
    REQ_PROFILE_FIELDS = ['job_title', 'about', 'years_of_expertise', 'identification_documents', 'url1', 'url2', 'skill_sets']

    class Meta(BaseProfile.Meta):
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_available', 'approved']),
            models.Index(fields=['rate', 'approved']),
        ]

    def update_rating(self):
        from django.db.models import Avg
        avg_rating = self.reviews_received.aggregate(avg=Avg('rating'))['avg']
        self.rate = round(avg_rating, 2) if avg_rating else 0.00
        self.save(update_fields=['rate'])

    @property
    def is_online(self):
        if not self.last_active: return False
        return (timezone.now() - self.last_active).total_seconds() < 300

class ClientProfile(BaseProfile):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='client_profile')
    REQ_USER_FIELDS = BaseProfile.REQ_USER_FIELDS + ['gender', 'date_of_birth']

    def calculate_completion(self):
        # Custom logic hook for Client-specific age requirement
        basic_complete = super().calculate_completion()
        age_ok = self.user.age is not None and self.user.age >= 18
        return basic_complete and age_ok

class AdminProfile(BaseProfile):
    ADMIN_ROLES = [
        ('system_admin', 'Admin'), 
        ('content_moderator', 'Moderator'), 
        ('finance_admin', 'Finance')
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
    role = models.CharField(max_length=50, choices=ADMIN_ROLES, default='system_admin')
    notes = models.TextField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Hook: Auto-promote User to staff when AdminProfile is created/updated
        if not self.user.is_staff:
            self.user.is_staff = True
            self.user.save(update_fields=['is_staff'])
        super().save(*args, **kwargs)

# --- Financial & Utility Models ---

class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    transaction_id = models.CharField(max_length=12, unique=True, editable=False)

    def save(self, *args, **kwargs):
        # Hook: Business logic for Transaction IDs and Balance safety
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex[:12]
        if self.balance < 0:
            raise ValueError("Balance cannot be negative.")
        super().save(*args, **kwargs)

class WalletTransaction(TimestampedModel):
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transactions')
    contract = models.ForeignKey('contract.Contract', null=True, blank=True, on_delete=models.SET_NULL)
    transaction_type = models.CharField(max_length=20, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()

class OTPVerification(TimestampedModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes')
    otp_code = models.CharField(max_length=6)
    verification_id = models.CharField(max_length=32, unique=True)
    is_used = models.BooleanField(default=False, db_index=True)

    @classmethod
    def generate_otp(cls, user):
        return cls.objects.create(
            user=user,
            otp_code=''.join(random.choices(string.digits, k=6)),
            verification_id=''.join(random.choices(string.ascii_letters + string.digits, k=32))
        )

    def is_valid(self):
        return not self.is_used and (timezone.now() - self.created_at).total_seconds() < 600

class TechnicianSkillSet(TimestampedModel):
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name='skill_set_records')
    categories = models.ManyToManyField('category.Category')
    skills = models.ManyToManyField('category.Skill')
    sub_skills = models.ManyToManyField('category.SubSkill')

class TechnicianImage(TimestampedModel):
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='technicians/uploads/')
    description = models.CharField(max_length=255, blank=True, null=True)