import os
import random
import string
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


def custom_user_profile_image_path(instance, filename):
	"""
	Upload path for CustomUser profile image.
	Format: Profile/{username}_{last_section_of_uuid}.{ext}
	Example: Profile/john_doe_a1b2c3d4e5f6.jpg
	"""
	ext = filename.split('.')[-1]
	uuid_last_section = str(instance.id).split('-')[-1]
	filename = f"{uuid_last_section}.{ext}"
	return os.path.join('Profile/', filename)


def technician_profile_image_path(instance, filename):
	ext = filename.split('.')[-1]
	filename = f"{str(instance.id).split('-')[-1]}.{ext}"
	return os.path.join('technicians/profile_images/', filename)


def client_profile_image_path(instance, filename):
	ext = filename.split('.')[-1]
	filename = f"{str(instance.id).split('-')[-1]}.{ext}"
	return os.path.join('clients/profile_images/', filename)


def technician_identification_docs_path(instance, filename):
	ext = filename.split('.')[-1]
	filename = f"{str(instance.id).split('-')[-1]}_identification.{ext}"
	return os.path.join('technicians/identification_docs/', filename)


phone_regex = RegexValidator(
	regex=r'^07[5|7|8]\d{8}$',
	message="Phone number must be 11 digits and start with 077, 078, or 075."
)


IRAQI_GOVERNORATES = [
	('Baghdad', 'بغداد'),
	('Basra', 'البصرة'),
	('Nineveh', 'نينوى'),
	('Erbil', 'أربيل'),
	('Sulaymaniyah', 'السليمانية'),
	('Kirkuk', 'كركوك'),
	('Duhok', 'دهوك'),
	('Najaf', 'النجف'),
	('Karbala', 'كربلاء'),
	('Anbar', 'الأنبار'),
	('Babil', 'بابل'),
	('Maysan', 'ميسان'),
	('Wasit', 'واسط'),
	('Dhi Qar', 'ذي قار'),
	('Muthanna', 'المثنى'),
	('Qadisiyyah', 'القادسية'),
	('Salah al-Din', 'صلاح الدين'),
	('Diyala', 'ديالى'),
]


class CustomUser(AbstractUser):
	ROLE_CHOICES = [
		('client', 'Client'),
		('technician', 'Technician'),
		('admin', 'Admin'),
		('dealership', 'Dealership'),
	]

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
	phone_number = models.CharField(validators=[phone_regex], max_length=11, blank=True, null=True, unique=True)
	governorate = models.CharField(choices=IRAQI_GOVERNORATES, max_length=50, null=True, blank=True)
	address = models.CharField(max_length=255, null=True, blank=True)
	gender = models.CharField(max_length=6, choices=[('male', 'Male'), ('female', 'Female')], null=True, blank=True)
	date_of_birth = models.DateField(null=True, blank=True)
	profile_image = models.ImageField(upload_to=custom_user_profile_image_path, null=True, blank=True)
	is_delete = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['role']),
			models.Index(fields=['governorate']),
		]

	def __str__(self):
		"""Return username as display name"""
		return self.username

	@property
	def age(self):
		if self.date_of_birth:
			today = date.today()
			return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
		return None



class TechnicianProfile(models.Model):
	user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='technician_profile')
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	is_available = models.BooleanField(default=True, db_index=True)
	approved = models.BooleanField(default=False, help_text="Administrator approval status for technician to appear in public listings", db_index=True)
	job_title = models.CharField(max_length=100, null=True, blank=True, help_text="Professional title or role")
	identification_documents = models.FileField(
		upload_to=technician_identification_docs_path,
		null=True,
		blank=True,
		help_text="Upload identification documents as a ZIP file (required for profile completion)",
	)
	url1 = models.URLField(max_length=255, null=True, blank=True)
	url2 = models.URLField(max_length=255, null=True, blank=True)
	about = models.TextField(null=True, blank=True)
	years_of_expertise = models.PositiveIntegerField(default=0, help_text="Number of years of professional experience")
	rate = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'), help_text="Cached average rating (auto-calculated from reviews)")
	skill_sets = models.OneToOneField('TechnicianSkillSet', on_delete=models.SET_NULL, null=True, blank=True, related_name='technician_profile_skill')
	is_complete = models.BooleanField(default=False)
	is_delete = models.BooleanField(default=False)
	last_active = models.DateTimeField(null=True, blank=True, db_index=True)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['user']),
			models.Index(fields=['is_available', 'approved']),
			models.Index(fields=['approved']),
			models.Index(fields=['rate', 'approved']),
		]
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user.get_full_name() or self.user.username} - {self.job_title or 'Technician'}"

	def update_rating(self):
		"""
		Recalculate and cache the average rating from all reviews.
		Should be called after a new review is added.
		"""
		from django.db.models import Avg

		# Use the FK reverse relation to include every review saved against this technician
		avg_rating = self.reviews_received.aggregate(avg=Avg('rating'))['avg']
		if avg_rating is not None:
			self.rate = round(avg_rating, 2)
		else:
			self.rate = 0.00
		self.save(update_fields=['rate'])
		return self.rate

	def check_profile_completion(self):
		"""
		Check if the technician profile has all required fields filled.
		Required fields from CustomUser: phone_number, profile_image, governorate, address, gender, date_of_birth
		Required fields from TechnicianProfile: job_title, about, years_of_expertise, identification_documents, url1, url2, skill_sets
		"""
		user = self.user
		if not user.phone_number or not user.profile_image or not user.governorate or not user.address or not user.gender or not user.date_of_birth:
			return False
		
		if not self.job_title or not self.about or self.years_of_expertise <= 0 or not self.identification_documents or not self.url1 or not self.url2:
			return False
		
		if not self.skill_sets:
			return False
			
		return True

	def update_completion_status(self):
		"""Update the is_complete flag based on profile completion check"""
		is_complete = self.check_profile_completion()
		if self.is_complete != is_complete:
			self.is_complete = is_complete
			self.save(update_fields=['is_complete'])
		return is_complete

	@property
	def is_online(self):
		"""Returns True if the user was active in the last 5 minutes"""
		if not self.last_active:
			return False
		return (timezone.now() - self.last_active).total_seconds() < 300

	def get_incomplete_fields(self):
		"""
		Returns a list of field names that are incomplete and preventing the profile from being completed.
		This helps users understand exactly what they need to fill out.
		"""
		incomplete_fields = []
		user = self.user
		
		# Check CustomUser fields
		if not user.phone_number:
			incomplete_fields.append('phone_number')
		if not user.profile_image:
			incomplete_fields.append('profile_image')
		if not user.governorate:
			incomplete_fields.append('governorate')
		if not user.address:
			incomplete_fields.append('address')
		if not user.gender:
			incomplete_fields.append('gender')
		if not user.date_of_birth:
			incomplete_fields.append('date_of_birth')
		
		# Check TechnicianProfile fields
		if not self.job_title:
			incomplete_fields.append('job_title')
		if not self.about:
			incomplete_fields.append('about')
		if self.years_of_expertise <= 0:
			incomplete_fields.append('years_of_expertise')
		if not self.identification_documents:
			incomplete_fields.append('identification_documents')
		if not self.url1:
			incomplete_fields.append('url1')
		if not self.url2:
			incomplete_fields.append('url2')
		if not self.skill_sets:
			incomplete_fields.append('Skill Sets')
			
		return incomplete_fields


class TechnicianSkillSet(models.Model):
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name='skill_set_records')
    categories = models.ManyToManyField('category.Category', related_name='technician_skill_sets')
    skills = models.ManyToManyField('category.Skill', related_name='technician_skill_sets')
    sub_skills = models.ManyToManyField('category.SubSkill', related_name='technician_skill_sets')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['technician'])]
        ordering = ['-created_at']

    def __str__(self):
        """Return skill set representation with technician name"""
        return f"SkillSet for {self.technician.user.username}"


class TechnicianImage(models.Model):
	technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='technicians/uploads/')
	description = models.CharField(max_length=255, blank=True, null=True)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [models.Index(fields=['technician']), models.Index(fields=['created_at'])]
		ordering = ['-created_at']

	def __str__(self):
		"""Return image representation with technician and description"""
		return f"Image for {self.technician.user.username}" + (f": {self.description}" if self.description else "")


class ClientProfile(models.Model):
	user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='client_profile')
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	is_complete = models.BooleanField(default=False)
	is_delete = models.BooleanField(default=False)
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['user']),
			models.Index(fields=['is_complete']),
			models.Index(fields=['is_delete']),
		]
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user.get_full_name() or self.user.username} (Client)"

	def check_profile_completion(self):
		"""
		Check if the client profile has all required fields filled.
		Required fields from CustomUser: phone_number, profile_image, governorate, address, gender, date_of_birth
		Age validation: must be >= 18 years old
		"""
		user = self.user
		required_checks = [
			user.phone_number,
			user.profile_image,
			user.governorate,
			user.address,
			user.gender,
			user.date_of_birth,
		]
		
		if not all(required_checks):
			return False
		
		try:
			if user.age is not None and user.age < 18:
				return False
		except Exception:
			return False
		
		return True

	def update_completion_status(self):
		"""Update the is_complete flag based on profile completion check"""
		is_complete = self.check_profile_completion()
		if self.is_complete != is_complete:
			self.is_complete = is_complete
			self.save(update_fields=['is_complete'])
		return is_complete

	def get_incomplete_fields(self):
		"""
		Returns a list of field names that are incomplete and preventing the profile from being completed.
		This helps users understand exactly what they need to fill out.
		"""
		incomplete_fields = []
		user = self.user
		
		if not user.phone_number:
			incomplete_fields.append('phone_number')
		if not user.profile_image:
			incomplete_fields.append('profile_image')
		if not user.governorate:
			incomplete_fields.append('governorate')
		if not user.address:
			incomplete_fields.append('address')
		if not user.gender:
			incomplete_fields.append('gender')
		if not user.date_of_birth:
			incomplete_fields.append('date_of_birth')
		
		# Age validation
		if user.date_of_birth and user.age is not None and user.age < 18:
			incomplete_fields.append('age_requirement')
		
		return incomplete_fields


class Wallet(models.Model):
	"""User wallet for managing account balance and transactions"""
	user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet', db_index=True)
	balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text="Account balance in IQD")
	transaction_id = models.CharField(max_length=12, unique=True, editable=False)

	class Meta:
		indexes = [models.Index(fields=['user'])]

	def save(self, *args, **kwargs):
		"""Generate unique transaction ID if not present; prevent negative balance"""
		if not self.transaction_id:
			self.transaction_id = uuid.uuid4().hex[:12]
		if self.balance < 0:
			raise ValueError("Wallet balance cannot be negative")
		super().save(*args, **kwargs)

	def __str__(self):
		"""Return wallet representation with username and balance"""
		return f"{self.user.username}'s Wallet (Balance: {self.balance} IQD)"


class WalletTransaction(models.Model):
	TRANSACTION_TYPE_CHOICES = [
		('deposit', 'Deposit'),
		('transfer_in', 'Transfer In'),
		('transfer_out', 'Transfer Out'),
		('escrow', 'Escrow'),
		('release', 'Release Payment'),
		('refund', 'Refund'),
		('withdrawal', 'Withdrawal'),
	]

	wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transactions')
	contract = models.ForeignKey('contract.Contract', null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
	transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, db_index=True, help_text="Type of transaction")
	amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Transaction amount in IQD")
	amount_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Equivalent USD amount at transaction time")
	exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Exchange rate IQD to USD at transaction time")
	description = models.TextField(help_text="Transaction description and details")
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['wallet', 'created_at']),
			models.Index(fields=['transaction_type']),
		]
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.transaction_type} of {self.amount} IQD for wallet {self.wallet.user.username}"


class OTPVerification(models.Model):
	"""One-time password verification for sensitive operations"""
	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes')
	otp_code = models.CharField(max_length=6, help_text="6-digit OTP code")
	verification_id = models.CharField(max_length=32, unique=True, help_text="Unique verification identifier")
	created_at = models.DateTimeField(auto_now_add=True)
	is_used = models.BooleanField(default=False, db_index=True, help_text="Whether this OTP has been used")

	class Meta:
		indexes = [
			models.Index(fields=['user', 'created_at']),
			models.Index(fields=['is_used']),
		]
		ordering = ['-created_at']

	@classmethod
	def generate_otp(cls, user):
		"""Generate a new OTP for a user"""
		otp_code = ''.join(random.choices(string.digits, k=6))
		verification_id = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
		return cls.objects.create(
			user=user,
			otp_code=otp_code,
			verification_id=verification_id,
		)

	def is_valid(self):
		"""Check if OTP is still valid (not expired and not used)"""
		expiry_time = self.created_at + timedelta(minutes=10)
		now = timezone.now() if timezone.is_aware(self.created_at) else datetime.now()
		return not self.is_used and now <= expiry_time

	def __str__(self):
		"""Return OTP representation"""
		return f"OTP for {self.user.username} - {self.verification_id[:8]}..."


class AdminProfile(models.Model):
	ADMIN_ROLE_CHOICES = [
		('system_admin', 'System Administrator'),
		('content_moderator', 'Content Moderator'),
		('account_manager', 'Account Manager'),
		('finance_admin', 'Financial Administrator'),
	]

	user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	role = models.CharField(
		max_length=50,
		choices=ADMIN_ROLE_CHOICES,
		default='system_admin',
		help_text="Specific administrative role and permissions",
	)
	notes = models.TextField(blank=True, null=True, help_text="Internal notes about the admin user")
	last_login_ip = models.GenericIPAddressField(null=True, blank=True)
	is_complete = models.BooleanField(default=False)
	is_delete = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['user']),
			models.Index(fields=['role']),
			models.Index(fields=['is_complete']),
			models.Index(fields=['is_delete']),
		]
		ordering = ['-created_at']

	def __str__(self):
		role_display = dict(self.ADMIN_ROLE_CHOICES).get(self.role, self.role)
		return f"{self.user.get_full_name() or self.user.username} ({role_display})"

	def save(self, *args, **kwargs):
		"""Ensure user has staff privileges before saving"""
		if not self.user.is_staff:
			self.user.is_staff = True
			self.user.save(update_fields=['is_staff'])
		super().save(*args, **kwargs)

	@property
	def is_system_admin(self):
		"""Check if this admin has system admin role"""
		return self.role == 'system_admin'

	@property
	def is_content_moderator(self):
		"""Check if this admin has content moderator role"""
		return self.role == 'content_moderator'

	@property
	def is_account_manager(self):
		"""Check if this admin has account manager role"""
		return self.role == 'account_manager'

	@property
	def is_finance_admin(self):
		"""Check if this admin has finance admin role"""
		return self.role == 'finance_admin'

	def check_profile_completion(self):
		"""
		Check if the admin profile has all required fields filled.
		Required fields from CustomUser: phone_number, profile_image, governorate, address, gender, date_of_birth
		Required fields from AdminProfile: role is set (always has default)
		"""
		user = self.user
		required_checks = [
			user.phone_number,
			user.profile_image,
			user.governorate,
			user.address,
			user.gender,
			user.date_of_birth,
		]
		
		return all(required_checks)

	def update_completion_status(self):
		"""Update the is_complete flag based on profile completion check"""
		is_complete = self.check_profile_completion()
		if self.is_complete != is_complete:
			self.is_complete = is_complete
			self.save(update_fields=['is_complete'])
		return is_complete

	def get_incomplete_fields(self):
		"""
		Returns a list of field names that are incomplete and preventing the profile from being completed.
		This helps admins understand exactly what they need to fill out.
		"""
		incomplete_fields = []
		user = self.user
		
		if not user.phone_number:
			incomplete_fields.append('phone_number')
		if not user.profile_image:
			incomplete_fields.append('profile_image')
		if not user.governorate:
			incomplete_fields.append('governorate')
		if not user.address:
			incomplete_fields.append('address')
		if not user.gender:
			incomplete_fields.append('gender')
		if not user.date_of_birth:
			incomplete_fields.append('date_of_birth')
		
		return incomplete_fields


class DealershipProfile(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='dealership_profile')
	company_name = models.CharField(max_length=255)
	company_registration_number = models.CharField(max_length=50, unique=True)
	about = models.TextField(blank=True)
	is_complete = models.BooleanField(default=False)
	is_delete = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['user']),
			models.Index(fields=['company_registration_number']),
			models.Index(fields=['is_complete']),
			models.Index(fields=['is_delete']),
		]
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.company_name} - {self.user.get_full_name() or self.user.username}"

	def check_profile_completion(self):
		"""
		Check if the dealership profile has all required fields filled.
		Required fields from CustomUser: phone_number, profile_image, governorate, address
		Required fields from DealershipProfile: company_name, company_registration_number, about
		"""
		user = self.user
		required_user_fields = [
			user.phone_number,
			user.profile_image,
			user.governorate,
			user.address,
		]
		
		if not all(required_user_fields):
			return False
		
		required_profile_fields = [
			self.company_name,
			self.company_registration_number,
			self.about,
		]
		
		return all(required_profile_fields)

	def update_completion_status(self):
		"""Update the is_complete flag based on profile completion check"""
		is_complete = self.check_profile_completion()
		if self.is_complete != is_complete:
			self.is_complete = is_complete
			self.save(update_fields=['is_complete'])
		return is_complete

	def get_incomplete_fields(self):
		"""
		Returns a list of field names that are incomplete and preventing the profile from being completed.
		This helps dealerships understand exactly what they need to fill out.
		"""
		incomplete_fields = []
		user = self.user
		
		# Check CustomUser fields
		if not user.phone_number:
			incomplete_fields.append('phone_number')
		if not user.profile_image:
			incomplete_fields.append('profile_image')
		if not user.governorate:
			incomplete_fields.append('governorate')
		if not user.address:
			incomplete_fields.append('address')
		
		# Check DealershipProfile fields
		if not self.company_name:
			incomplete_fields.append('company_name')
		if not self.company_registration_number:
			incomplete_fields.append('company_registration_number')
		if not self.about:
			incomplete_fields.append('about')
		
		return incomplete_fields
