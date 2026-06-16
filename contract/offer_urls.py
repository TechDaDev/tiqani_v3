"""
Offer URL configuration — included under /api/offers/ and /api/technician/offers/.

Patterns are defined in contract/urls.py and imported here.
"""

from django.urls import include, path

from .urls import offer_urlpatterns, technician_offer_urlpatterns

urlpatterns = offer_urlpatterns

technician_urlpatterns = technician_offer_urlpatterns
