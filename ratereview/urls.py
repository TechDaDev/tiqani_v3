from django.urls import path
from .views import TechnicianReviewsList, ReviewDetailView

urlpatterns = [
    path(
        "technician/<uuid:technician_id>/",
        TechnicianReviewsList.as_view(),
        name="technician_reviews",
    ),
    path("<uuid:id>/", ReviewDetailView.as_view(), name="review_detail"),
]
