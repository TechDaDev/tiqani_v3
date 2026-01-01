from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import (

    RegistrationSerializer, 
    OTPVerificationSerializer,
    ForgotPasswordSerializer, 
    ResetPasswordConfirmSerializer
)

#TODO: limiting config to settings.py and append to env later
# --- Configuration ---
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SEC = 5 * 60

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
        
        userdata = {
            'id': str(user.id),
            'username': user.username,
            'role': user.role,
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