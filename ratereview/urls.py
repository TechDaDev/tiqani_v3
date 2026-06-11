from django.urls import path
from .views import (
    TechnicianReviewsList, ReviewDetailUpdateView, ReviewCreateView,
    ReviewTechnicianResponseView,
    ReviewHelpfulView, ReviewReportView,
    ReviewModeratePublishView, ReviewModerateHideView,
    ReviewModerateVerifyView, ReviewModerateUnverifyView,
)

urlpatterns = [
    # Public list (must come before <uuid:id>)
    path(
        "technician/<uuid:technician_id>/",
        TechnicianReviewsList.as_view(),
        name="technician_reviews",
    ),
    # Create
    path("", ReviewCreateView.as_view(), name="review_create"),
    # Detail + Update (GET + PATCH)
    path("<uuid:id>/", ReviewDetailUpdateView.as_view(), name="review_detail_update"),
    # Technician response
    path("<uuid:id>/respond/", ReviewTechnicianResponseView.as_view(), name="review_respond"),
    # Trust actions
    path("<uuid:id>/helpful/", ReviewHelpfulView.as_view(), name="review_helpful"),
    path("<uuid:id>/report/", ReviewReportView.as_view(), name="review_report"),
    # Moderation
    path("<uuid:id>/moderate/publish/", ReviewModeratePublishView.as_view(), name="review_moderate_publish"),
    path("<uuid:id>/moderate/hide/", ReviewModerateHideView.as_view(), name="review_moderate_hide"),
    path("<uuid:id>/moderate/verify/", ReviewModerateVerifyView.as_view(), name="review_moderate_verify"),
    path("<uuid:id>/moderate/unverify/", ReviewModerateUnverifyView.as_view(), name="review_moderate_unverify"),
]
