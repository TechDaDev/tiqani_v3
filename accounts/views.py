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
    """
    permission_classes = (AllowAny,)
    def post(self, request, *args, **kwargs):
 
        username = request.data.get('username')
        password = request.data.get('password')
        user = CustomUser.objects.filter(username=username).first()
        if user and not user.check_password(password):
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user and not user.is_active:
             return Response({"detail": "Account is inactive. Please verify your email."}, status=status.HTTP_403_FORBIDDEN)

        try:

            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            return Response({
                "refresh": str(refresh),
                "access": str(access),
                "userdata": {
			'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'full_name': user.get_full_name(),
            'profile_image': user.profile_image.url if user.profile_image else None,
				}
            }, status=status.HTTP_200_OK)
        except Exception as e:
            pass

        return Response(
            {"detail": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED
        )

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