from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .models import CustomUser, TechnicianProfile, ClientProfile, OTPVerification
from wallet.models import Wallet
from .email_utils import send_otp_email, send_welcome_email, send_password_reset_email



# --- Registration & Account Management ---

class RegistrationSerializer(serializers.ModelSerializer):
    """
    Handles user registration and automatic profile creation.
    Uses database transactions to ensure data integrity and aligns with model fields.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=[('client', 'Client'), ('technician', 'Technician')])

    # CustomUser fields
    phone_number = serializers.CharField(required=False, allow_blank=True)
    governorate = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=CustomUser.Gender.choices, required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    # TechnicianProfile fields (only used when role=technician)
    job_title = serializers.CharField(required=False, allow_blank=True)
    about = serializers.CharField(required=False, allow_blank=True)
    years_of_expertise = serializers.IntegerField(required=False, min_value=0)
    identification_documents = serializers.FileField(required=False, allow_null=True)
    github = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    linkedin = serializers.URLField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'password', 'first_name', 'last_name', 'role',
            'phone_number', 'governorate', 'address', 'gender', 'date_of_birth', 'profile_image',
            'job_title', 'about', 'years_of_expertise', 'identification_documents', 'github', 'linkedin'
        )

    def validate(self, attrs):

        email = attrs['email']
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})

        phone = attrs.get('phone_number')
        if phone and CustomUser.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError({"phone_number": "This phone number is already registered."})

        if attrs.get('role') == 'technician':
            required_tech_fields = ['job_title']
            missing = [f for f in required_tech_fields if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "This field is required for technicians." for f in missing})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        role = validated_data.get('role')

        user_fields = {
            'username', 'email', 'first_name', 'last_name', 'role',
            'phone_number', 'governorate', 'address', 'gender', 'date_of_birth', 'profile_image'
        }
        user_data = {k: v for k, v in validated_data.items() if k in user_fields}

        tech_fields = {
            'job_title', 'about', 'years_of_expertise',
            'identification_documents', 'github', 'linkedin'
        }
        tech_data = {k: v for k, v in validated_data.items() if k in tech_fields}

        with transaction.atomic():
            user = CustomUser.objects.create_user(
                password=password,
                is_active=False,
                **user_data
            )
        

            Wallet.objects.create(user=user)

            if role == 'technician':
                TechnicianProfile.objects.create(user=user, **tech_data)
            elif role == 'client':
                ClientProfile.objects.create(user=user)

            otp = OTPVerification.generate_otp(user)
            if not send_otp_email(user, otp.otp_code, otp.verification_id):
                raise serializers.ValidationError("Email service failure. Please try again later.")

        return user

class OTPBaseSerializer(serializers.Serializer):
    """Shared logic for OTP-based operations."""
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)

    def get_valid_otp(self, attrs, is_active_required=False):
        email = attrs['email']
        otp_code = attrs['otp_code']

        try:
            user = CustomUser.objects.get(email=email, is_active=is_active_required)
            otp = OTPVerification.objects.get(user=user, otp_code=otp_code, is_used=False)
        except (CustomUser.DoesNotExist, OTPVerification.DoesNotExist):
            raise serializers.ValidationError("Invalid credentials or OTP code.")

        if not otp.is_valid():
            raise serializers.ValidationError("OTP code has expired.")

        return user, otp


class OTPVerificationSerializer(OTPBaseSerializer):
    """Verifies account registration via OTP."""

    def validate(self, attrs):
        user, otp = self.get_valid_otp(attrs, is_active_required=False)
        
        with transaction.atomic():
            otp.is_used = True
            otp.save()
            user.is_active = True
            user.save()

        # Fire and forget welcome email
        try: send_welcome_email(user)
        except: pass

        # Store user for save() method
        attrs['_user'] = user
        return attrs

    def save(self):
        return self.validated_data['_user']


# --- Password Reset Flow ---

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        email = self.validated_data['email']
        user = CustomUser.objects.filter(email=email, is_active=True).first()
        
        # Security: don't reveal if email exists, just return
        if user:
            otp = OTPVerification.generate_otp(user)
            send_password_reset_email(user, otp.otp_code)
        return True


class ResetPasswordConfirmSerializer(OTPBaseSerializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs):
        
        user, otp = self.get_valid_otp(attrs, is_active_required=True)
        
        attrs['_user'] = user
        attrs['_otp'] = otp
        return attrs

    def save(self):
        user = self.validated_data['_user']
        otp = self.validated_data['_otp']
        
        with transaction.atomic():
            user.set_password(self.validated_data['new_password'])
            user.save()
            otp.is_used = True
            otp.save()
        return user


class CurrentUserSerializer(serializers.ModelSerializer):
    """Public-safe serializer for the currently authenticated user."""

    role = serializers.SerializerMethodField()
    profile_type = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()
    wallet_transaction_id = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone_number",
            "governorate",
            "address",
            "gender",
            "date_of_birth",
            "profile_image",
            "is_active",
            "is_staff",
            "profile_type",
            "is_complete",
            "wallet_balance",
            "wallet_transaction_id",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "role",
            "is_active",
            "is_staff",
            "profile_type",
            "is_complete",
            "wallet_balance",
            "wallet_transaction_id",
        )

    def get_role(self, obj):
        if hasattr(obj, "admin_profile"):
            return obj.admin_profile.role
        return obj.role

    def get_profile_type(self, obj):
        if hasattr(obj, "client_profile"):
            return "client"
        if hasattr(obj, "technician_profile"):
            return "technician"
        if hasattr(obj, "admin_profile"):
            return "admin"
        return None

    def get_is_complete(self, obj):
        if hasattr(obj, "client_profile"):
            return obj.client_profile.is_complete
        if hasattr(obj, "technician_profile"):
            return obj.technician_profile.is_complete
        return None

    def get_wallet_balance(self, obj):
        wallet = getattr(obj, "wallet", None)
        return str(wallet.balance) if wallet else None

    def get_wallet_transaction_id(self, obj):
        wallet = getattr(obj, "wallet", None)
        return wallet.transaction_id if wallet else None
