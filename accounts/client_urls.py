from django.urls import path
from .client_views import ClientProfileView

urlpatterns = [
    path("me/", ClientProfileView.as_view(), name="client_profile"),
]
