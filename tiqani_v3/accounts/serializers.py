from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, TechnicianProfile, ClientProfile, OTPVerification
from .email_utils import send_otp_email, send_welcome_email


class LoginSerializer(TokenObtainPairSerializer):
    """Extend JWT login to include user payload and role-specific flags."""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        def profile_info():
            info = {
                'id': str(getattr(user, 'id', '')),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'profile_image': user.profile_image.url if user.profile_image else None,
            }
            # Attach role-specific profile snippet if available
            try:
                if user.role == 'admin' and hasattr(user, 'admin_profile') and user.admin_profile:
                    ap = user.admin_profile
                    info['admin_profile'] = {
                        'role': ap.role,
                    }
            except Exception:
                # Do not block login on missing optional relations
                pass
            return info

        data['user'] = profile_info()
        return data


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Creates CustomUser and role-specific profile (TechnicianProfile or ClientProfile).
    Generates OTP and sends verification email.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role')

    def validate(self, attrs):
        """Validate that passwords match and username/email don't already exist."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        
        # Check if username already exists
        if CustomUser.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "This username is already taken."})
        
        # Check if email already exists
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        
        return attrs

    def create(self, validated_data):
        """
        Create CustomUser and role-specific profile.
        Generate OTP and send verification email.
        """
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        role = validated_data.get('role')
        
        # Create user with is_active=False until email verified
        user = CustomUser.objects.create_user(
            password=password,
            is_active=False,
            **validated_data
        )
        
        # Create role-specific profile
        try:
            if role == 'technician':
                TechnicianProfile.objects.create(user=user)
            elif role == 'client':
                ClientProfile.objects.create(user=user)
            # Admin and dealership profiles are typically created via admin
        except Exception as e:
            # Clean up user if profile creation fails
            user.delete()
            raise serializers.ValidationError(f"Error creating profile: {str(e)}")
        
        # Generate and send OTP
        try:
            otp = OTPVerification.generate_otp(user)
            email_sent = send_otp_email(user, otp.otp_code, otp.verification_id)
            if not email_sent:
                raise serializers.ValidationError("Failed to send verification email. Please try again.")
        except Exception as e:
            user.delete()
            raise serializers.ValidationError(f"Error sending verification email: {str(e)}")
        
        return user


class OTPVerificationSerializer(serializers.Serializer):
    """
    Serializer for OTP verification during registration.
    Verifies OTP code and activates the user account.
    """
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)

    def validate(self, attrs):
        """Validate OTP code and activate user if valid."""
        email = attrs['email']
        otp_code = attrs['otp_code']
        
        try:
            user = CustomUser.objects.get(email=email, is_active=False)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "No inactive user found with this email."})
        
        # Find valid OTP
        try:
            otp = OTPVerification.objects.get(
                user=user,
                otp_code=otp_code,
                is_used=False
            )
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError({"otp_code": "Invalid or expired OTP code."})
        
        # Check if OTP is still valid (not expired)
        if not otp.is_valid():
            raise serializers.ValidationError({"otp_code": "OTP code has expired."})
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Activate user
        user.is_active = True
        user.save()
        
        # Send welcome email
        try:
            send_welcome_email(user)
        except Exception:
            pass  # Don't block activation if welcome email fails
        
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        """Return the activated user."""
        return validated_data['user']


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    Sends OTP to user's email if account exists.
    """
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        """Validate email and find user."""
        email = attrs['email']
        
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists (security best practice)
            raise serializers.ValidationError(
                {"email": "If an account exists with this email, you will receive a password reset link."}
            )
        
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        """Generate OTP and send password reset email."""
        user = validated_data['user']
        
        try:
            # Generate OTP for password reset
            otp = OTPVerification.generate_otp(user)
            # Send password reset email with OTP
            from .email_utils import send_password_reset_email
            email_sent = send_password_reset_email(user, otp.otp_code)
            if not email_sent:
                raise serializers.ValidationError("Failed to send password reset email. Please try again.")
        except Exception as e:
            raise serializers.ValidationError(f"Error sending email: {str(e)}")
        
        return user


class ResetPasswordConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    Verifies OTP and sets new password.
    """
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)
    new_password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(
        write_only=True, 
        required=True
    )

    def validate(self, attrs):
        """Validate passwords match and OTP is valid."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        
        email = attrs['email']
        otp_code = attrs['otp_code']
        
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})
        
        # Find valid OTP
        try:
            otp = OTPVerification.objects.get(
                user=user,
                otp_code=otp_code,
                is_used=False
            )
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError({"otp_code": "Invalid or expired OTP code."})
        
        # Check if OTP is still valid
        if not otp.is_valid():
            raise serializers.ValidationError({"otp_code": "OTP code has expired."})
        
        attrs['user'] = user
        attrs['otp'] = otp
        return attrs

    def create(self, validated_data):
        """Reset password and mark OTP as used."""
        user = validated_data['user']
        otp = validated_data['otp']
        new_password = validated_data['new_password']
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        return user
