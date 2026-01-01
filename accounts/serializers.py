from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from .models import CustomUser, TechnicianProfile, ClientProfile, OTPVerification, Wallet
from .email_utils import send_otp_email, send_welcome_email, send_password_reset_email



# --- Registration & Account Management ---

class RegistrationSerializer(serializers.ModelSerializer):
    """
    Handles user registration and automatic profile creation.
    Uses database transactions to ensure data integrity.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[('client', 'Client'), ('technician', 'Technician')])

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        role = validated_data.get('role')

        with transaction.atomic():
            # Create inactive user
            user = CustomUser.objects.create_user(
                password=password, 
                is_active=False, 
                **validated_data
            )

            # Create wallet for user
            Wallet.objects.create(user=user)

            # Create specific profile based on role
            if role == 'technician':
                TechnicianProfile.objects.create(user=user)
            elif role == 'client':
                ClientProfile.objects.create(user=user)

            # Generate and Send OTP
            otp = OTPVerification.generate_otp(user)
            if not send_otp_email(user, otp.otp_code, otp.verification_id):
                raise serializers.ValidationError("Email service failure. Please try again later.")

        return user


# --- OTP & Verification ---

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
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        
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