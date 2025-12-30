from django.urls import path
from .views import (
    LoginView, RefreshTokenView, LogoutView, RegistrationView, VerifyEmailView,
    ForgotPasswordView, ResetPasswordConfirmView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth_login'),
    path('refresh/', RefreshTokenView.as_view(), name='auth_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('register/', RegistrationView.as_view(), name='auth_register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('password-reset/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password-reset-confirm/', ResetPasswordConfirmView.as_view(), name='reset_password_confirm'),
]
