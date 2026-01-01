from django.urls import path
from .views import (
    LoginView, 
    RefreshTokenView, 
    LogoutView, 
    RegistrationView, 
    VerifyEmailView,
    ForgotPasswordView, 
    ResetPasswordConfirmView
)
from .technician_views import (
    TechnicianProfileView,
    TechnicianSkillsView,
    TechnicianImagesListView,
    TechnicianImageDetailView,
    TechnicianAvailabilityView,
    TechnicianRatingsView
)

urlpatterns = [
    # --- Basic Authentication ---
    path('login/', LoginView.as_view(), name='auth_login'),
    path('refresh/', RefreshTokenView.as_view(), name='auth_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),

    # --- Registration & Account Activation ---
    path('register/', RegistrationView.as_view(), name='auth_register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),

    # --- Password Management ---
    path('password-reset/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password-reset-confirm/', ResetPasswordConfirmView.as_view(), name='reset_password_confirm'),

    # --- Technician Endpoints ---
    path('technician/profile/', TechnicianProfileView.as_view(), name='technician_profile'),
    path('technician/skills/', TechnicianSkillsView.as_view(), name='technician_skills'),
    path('technician/images/', TechnicianImagesListView.as_view(), name='technician_images_list'),
    path('technician/images/<uuid:image_id>/', TechnicianImageDetailView.as_view(), name='technician_image_detail'),
    path('technician/availability/', TechnicianAvailabilityView.as_view(), name='technician_availability'),
    path('technician/ratings/', TechnicianRatingsView.as_view(), name='technician_ratings'),
]