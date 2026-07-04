from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import (
    RegistrationSerializer,
    OTPVerificationSerializer,
    ForgotPasswordSerializer,
    ResetPasswordConfirmSerializer,
    CurrentUserSerializer,
)
from .email_utils import send_otp_email
from .models import OTPVerification

#TODO: limiting config to settings.py and append to env later
# --- Configuration ---
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SEC = 5 * 60

# OTP Resend Rate Limiting
OTP_RESEND_COOLDOWN_SEC = 5 * 60  # 5 minutes between resends
OTP_RESEND_DAILY_LIMIT = 5  # Max 5 resends per 24 hours
OTP_RESEND_DAILY_WINDOW_SEC = 24 * 60 * 60  # 24 hours

def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', 'unknown')

# --- Authentication Views ---

class LoginView(TokenObtainPairView):
    """
    JWT Login with built-in rate limiting and account status checks.
    Rate limiting: 5 failed attempts per IP per 5 minutes.
    """
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        client_ip = _get_client_ip(request)
        
        # Rate limiting check
        cache_key = f'login_attempts_{client_ip}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= RATE_LIMIT_ATTEMPTS:
            remaining_time = cache.ttl(cache_key)
            return Response({
                "detail": "Too many login attempts. Please try again later.",
                "remaining_timeout": remaining_time if remaining_time > 0 else 0
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Get user
        user = CustomUser.objects.filter(username=username).first()
        
        # Check credentials
        if not user or not user.check_password(password):
            # Increment failed attempts
            cache.set(cache_key, attempts + 1, RATE_LIMIT_WINDOW_SEC)
            attempts_remaining = RATE_LIMIT_ATTEMPTS - (attempts + 1)
            return Response({
                "detail": "Invalid credentials.",
                "attempts_remaining": max(0, attempts_remaining)
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if account is active
        if not user.is_active:
            return Response({
                "detail": "Account is inactive. Please verify your email."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Successful login - clear rate limit cache
        cache.delete(cache_key)
        
        # Update last_active for technicians
        if user.role == 'technician' and hasattr(user, 'technician_profile'):
            user.technician_profile.last_active = timezone.now()
            user.technician_profile.save(update_fields=['last_active'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        role = user.admin_profile.role if hasattr(user, 'admin_profile') else user.role
        userdata = {
            'id': str(user.id),
            'username': user.username,
            'role': role,
            'is_staff': user.is_staff,
            'full_name': user.get_full_name(),
            'profile_image': user.profile_image.url if user.profile_image else None,
        }

        if user.role == 'technician' and hasattr(user, 'technician_profile'):
            profile = user.technician_profile
            userdata.update({
                'job_title': profile.job_title,
                'is_available': profile.is_available,
                'rating': float(profile.rate) if profile.rate is not None else 0.0,
                'total_reviews': 0,  # placeholder until reviews model is wired
            })

        return Response({
            "refresh": str(refresh),
            "access": str(access),
            "userdata": userdata,
        }, status=status.HTTP_200_OK)

class RefreshTokenView(TokenRefreshView):
    permission_classes = (AllowAny,)

class LogoutView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

# --- Registration & Verification ---

class RegistrationView(APIView):
    """
    Registers user and triggers OTP via serializer.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "detail": "Verification code sent to email.",
            "email": user.email
        }, status=status.HTTP_201_CREATED)

class VerifyEmailView(APIView):
    """
    Activates account using the logic centralized in the serializer.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "detail": "Account activated successfully.",
            "username": user.username
        }, status=status.HTTP_200_OK)

class ResendOTPView(APIView):
    """
    Resends OTP verification code with rate limiting.
    Rate limiting:
    - 5 minutes cooldown between consecutive resends
    - Max 5 resends per 24 hours per email
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({
                "detail": "Email address is required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user exists
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Generic response for security (don't reveal if email exists)
            return Response({
                "detail": "If an account exists with this email, a new verification code will be sent."
            }, status=status.HTTP_200_OK)
        
        # Check if account is already verified
        if user.is_active:
            return Response({
                "detail": "This account is already verified."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Rate limiting: Check cooldown (5 minutes)
        cooldown_cache_key = f'otp_resend_cooldown_{email}'
        if cache.get(cooldown_cache_key):
            remaining_time = cache.ttl(cooldown_cache_key)
            return Response({
                "detail": "Please wait before requesting another code.",
                "remaining_seconds": remaining_time if remaining_time > 0 else 0,
                "retry_after": f"{remaining_time // 60} minutes" if remaining_time > 60 else f"{remaining_time} seconds"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Rate limiting: Check daily limit (5 resends per 24 hours)
        daily_cache_key = f'otp_resend_daily_{email}'
        daily_count = cache.get(daily_cache_key, 0)
        
        if daily_count >= OTP_RESEND_DAILY_LIMIT:
            return Response({
                "detail": "Daily OTP resend limit reached. Please try again tomorrow.",
                "limit": OTP_RESEND_DAILY_LIMIT
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Generate new OTP
        otp = OTPVerification.generate_otp(user)
        
        # Send OTP email
        try:
            send_otp_email(user, otp.otp_code, otp.verification_id)
        except Exception as e:
            return Response({
                "detail": "Failed to send verification email. Please try again later."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Set cooldown (5 minutes)
        cache.set(cooldown_cache_key, True, OTP_RESEND_COOLDOWN_SEC)
        
        # Increment daily counter
        if daily_count == 0:
            # First resend today - set counter with 24-hour expiry
            cache.set(daily_cache_key, 1, OTP_RESEND_DAILY_WINDOW_SEC)
        else:
            # Increment existing counter (preserve original TTL)
            remaining_ttl = cache.ttl(daily_cache_key)
            cache.set(daily_cache_key, daily_count + 1, remaining_ttl if remaining_ttl > 0 else OTP_RESEND_DAILY_WINDOW_SEC)
        
        return Response({
            "detail": "A new verification code has been sent to your email.",
            "email": email,
            "resends_remaining": OTP_RESEND_DAILY_LIMIT - (daily_count + 1)
        }, status=status.HTTP_200_OK)

# --- Password Recovery ---

class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "detail": "If an account exists, a reset code has been sent."
        }, status=status.HTTP_200_OK)

class ResetPasswordConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "detail": "Password has been reset successfully."
        }, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    """
    GET /api/accounts/me/ — return the current user's profile.
    PATCH /api/accounts/me/ — update safe user fields.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        allowed_fields = {
            "first_name",
            "last_name",
            "phone_number",
            "governorate",
            "address",
            "gender",
            "date_of_birth",
            "profile_image",
        }
        # Prevent role/staff/active changes
        for field in ("role", "is_staff", "is_superuser", "is_active"):
            if field in request.data:
                return Response(
                    {field: "This field cannot be changed via this endpoint."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        updated = False
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
                updated = True

        if updated:
            user.save()

            # Recalculate profile completion
            for profile_attr in ("client_profile", "technician_profile"):
                profile = getattr(user, profile_attr, None)
                if profile:
                    profile.save()

        serializer = CurrentUserSerializer(user, context={"request": request})
        return Response(serializer.data)
