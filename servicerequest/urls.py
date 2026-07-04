"""
URL routing for ServiceRequest endpoints.

Client endpoints:  /api/requests/
Technician endpoints: /api/technician/requests/
"""

from django.urls import path
from .views import (
    ClientRequestListCreateView,
    ClientRequestDetailView,
    ClientCancelRequestView,
    ClientWithdrawRequestView,
    TechnicianRequestListView,
    TechnicianRequestDetailView,
    TechnicianAcceptRequestView,
    TechnicianDeclineRequestView,
)

urlpatterns = [
    # --- Client-facing ---
    path("", ClientRequestListCreateView.as_view(), name="request-list-create"),
    path("<uuid:request_id>/", ClientRequestDetailView.as_view(), name="request-detail"),
    path("<uuid:request_id>/cancel/", ClientCancelRequestView.as_view(), name="request-cancel"),
    path("<uuid:request_id>/withdraw/", ClientWithdrawRequestView.as_view(), name="request-withdraw"),
]

technician_urlpatterns = [
    path("", TechnicianRequestListView.as_view(), name="technician-request-list"),
    path("<uuid:request_id>/", TechnicianRequestDetailView.as_view(), name="technician-request-detail"),
    path("<uuid:request_id>/accept/", TechnicianAcceptRequestView.as_view(), name="technician-request-accept"),
    path("<uuid:request_id>/decline/", TechnicianDeclineRequestView.as_view(), name="technician-request-decline"),
]
