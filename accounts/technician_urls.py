from django.urls import path
from .technician_views import (
    TechnicianListView,
    TechnicianProfileView,
    TechnicianSkillsView,
    TechnicianImagesListView,
    TechnicianImageDetailView,
    TechnicianAvailabilityView,
    TechnicianRatingsView,
    TechnicianDetailView,
)

urlpatterns = [
    path("", TechnicianListView.as_view(), name="technician_list"),
    path("me/", TechnicianProfileView.as_view(), name="technician_profile"),
    path("me/skills/", TechnicianSkillsView.as_view(), name="technician_skills"),
    path("me/images/", TechnicianImagesListView.as_view(), name="technician_images_list"),
    path("me/images/<uuid:image_id>/", TechnicianImageDetailView.as_view(), name="technician_image_detail"),
    path("me/availability/", TechnicianAvailabilityView.as_view(), name="technician_availability"),
    path("me/ratings/", TechnicianRatingsView.as_view(), name="technician_ratings"),
    path("<uuid:id>/", TechnicianDetailView.as_view(), name="technician_detail"),
]
