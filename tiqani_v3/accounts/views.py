from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegistrationSerializer, OTPVerificationSerializer
from .models import CustomUser
from .serializers import ForgotPasswordSerializer, ResetPasswordConfirmSerializer


RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SEC = 5 * 60


def _client_ip(request):
	# Basic IP extraction; extend for proxies if needed
	xff = request.META.get('HTTP_X_FORWARDED_FOR')
	if xff:
		return xff.split(',')[0].strip()
	return request.META.get('REMOTE_ADDR', 'unknown')


class LoginView(TokenObtainPairView):
	permission_classes = (AllowAny,)
	serializer_class = LoginSerializer

	def post(self, request, *args, **kwargs):
		ip = _client_ip(request)
		attempts_key = f"login_attempts:{ip}"
		block_key = f"login_block:{ip}"

		# If blocked, return 429 with remaining_timeout
		blocked_until = cache.get(block_key)
		if blocked_until:
			remaining = int((blocked_until - timezone.now()).total_seconds())
			if remaining > 0:
				return Response(
					{
						"detail": "Too many login attempts. Please try again in 5 minutes.",
						"remaining_timeout": remaining,
					},
					status=status.HTTP_429_TOO_MANY_REQUESTS,
				)
			else:
				cache.delete(block_key)

		# Missing fields validation shortcut
		username = request.data.get('username')
		password = request.data.get('password')
		errors = {}
		if username in (None, ''):
			errors.setdefault('username', []).append('This field is required.')
		if password in (None, ''):
			errors.setdefault('password', []).append('This field is required.')
		if errors:
			return Response(errors, status=status.HTTP_400_BAD_REQUEST)

		# Special case: disabled account message
		try:
			user = CustomUser.objects.get(username=username)
			if not user.is_active and user.check_password(password):
				return Response(
					{"detail": "User account is disabled."},
					status=status.HTTP_403_FORBIDDEN,
				)
		except CustomUser.DoesNotExist:
			user = None

		# Proceed with normal JWT flow
		response = None
		try:
			response = super().post(request, *args, **kwargs)
		except Exception:
			# Fall back to 401 with attempts info
			pass

		if response is not None and response.status_code == status.HTTP_200_OK:
			# Successful login: reset counters
			cache.delete(attempts_key)
			cache.delete(block_key)
			return response

		# Failed login: increment attempts and maybe block
		attempts = cache.get(attempts_key, 0)
		attempts += 1
		cache.set(attempts_key, attempts, timeout=RATE_LIMIT_WINDOW_SEC)

		if attempts >= RATE_LIMIT_ATTEMPTS:
			cache.set(block_key, timezone.now() + timezone.timedelta(seconds=RATE_LIMIT_WINDOW_SEC), RATE_LIMIT_WINDOW_SEC)
			return Response(
				{
					"detail": "Too many login attempts. Please try again in 5 minutes.",
					"remaining_timeout": RATE_LIMIT_WINDOW_SEC,
				},
				status=status.HTTP_429_TOO_MANY_REQUESTS,
			)

		attempts_remaining = max(0, RATE_LIMIT_ATTEMPTS - attempts)
		return Response(
			{
				"detail": "No active account found with the given credentials",
				"attempts_remaining": attempts_remaining,
			},
			status=status.HTTP_401_UNAUTHORIZED,
		)


class RefreshTokenView(TokenRefreshView):
	permission_classes = (AllowAny,)


class LogoutView(APIView):
	permission_classes = (AllowAny,)

	def post(self, request, *args, **kwargs):
		refresh = request.data.get('refresh')
		if not refresh:
			return Response({"refresh": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
		try:
			token = RefreshToken(refresh)
			token.blacklist()
		except Exception:
			return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
		return Response(status=status.HTTP_205_RESET_CONTENT)


class RegistrationView(APIView):
	"""
	User registration endpoint.
	Creates CustomUser and role-specific profile.
	Generates OTP and sends verification email.
	"""
	permission_classes = (AllowAny,)

	def post(self, request, *args, **kwargs):
		serializer = RegistrationSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			return Response(
				{
					"detail": "Registration successful. Please check your email for verification code.",
					"email": user.email,
					"message": "An OTP has been sent to your email. Verify your email to activate your account.",
				},
				status=status.HTTP_201_CREATED,
			)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
	"""
	Email verification endpoint.
	Verifies OTP code and activates user account.
	"""
	permission_classes = (AllowAny,)

	def post(self, request, *args, **kwargs):
		serializer = OTPVerificationSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			return Response(
				{
					"detail": "Email verified successfully. Your account is now active.",
					"username": user.username,
					"message": "You can now login with your credentials.",
				},
				status=status.HTTP_200_OK,
			)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
	"""
	Password reset request endpoint.
	Sends OTP code to user's email for password reset.
	"""
	permission_classes = (AllowAny,)

	def post(self, request, *args, **kwargs):
		serializer = ForgotPasswordSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			return Response(
				{
					"detail": "If an account exists with this email, you will receive a password reset code.",
					"email": user.email,
					"message": "Check your email for the password reset code.",
				},
				status=status.HTTP_200_OK,
			)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordConfirmView(APIView):
	"""
	Password reset confirmation endpoint.
	Verifies OTP and sets new password.
	"""
	permission_classes = (AllowAny,)

	def post(self, request, *args, **kwargs):
		serializer = ResetPasswordConfirmSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			return Response(
				{
					"detail": "Password reset successfully. You can now login with your new password.",
					"username": user.username,
					"message": "Your password has been updated.",
				},
				status=status.HTTP_200_OK,
			)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

