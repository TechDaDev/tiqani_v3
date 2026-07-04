"""
URL configuration for tiqani_v3 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from .views import health_live, health_ready, health_deep, health
from servicerequest import urls as servicerequest_urls
from contract import offer_urls as contract_offer_urls
from ratereview.views import UserReputationView, UserReviewsList

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/', include('accounts.urls')),
    # Current user / account
    path('api/accounts/', include('accounts.api_urls')),
    # Categories
    path('api/categories/', include('category.urls')),
    # Technicians
    path('api/technicians/', include('accounts.technician_urls')),
    # Clients
    path('api/clients/', include('accounts.client_urls')),
    # Public reviews
    path('api/reviews/', include('ratereview.urls')),
    # Contracts + Offers
    path('api/contracts/', include('contract.urls')),
    path('api/offers/', include('contract.offer_urls')),
    # Wallet / Fees / Payment Prep
    path('api/wallet/', include('wallet.urls')),
    # Notifications / Activity
    path('api/notifications/', include('notification.urls')),
    # Public user reputation/reviews
    path('api/users/<uuid:user_id>/reputation/', UserReputationView.as_view(), name='user-reputation'),
    path('api/users/<uuid:user_id>/reviews/', UserReviewsList.as_view(), name='user-reviews'),
    # Dealership
    path('api/dealership/', include('dealership.urls')),
    # Chat
    path('api/chat/', include('chat.urls')),
    # Service Requests
    path('api/requests/', include('servicerequest.urls')),
    path('api/technician/requests/', include(servicerequest_urls.technician_urlpatterns)),
    # Technician Offers
    path('api/technician/offers/', include(contract_offer_urls.technician_urlpatterns)),
    # Disputes
    path('api/', include('dispute.urls')),
    # Admin Dashboard
    path('api/admin/', include('dashboard.urls')),
    # Health
    path('api/health/', health),
    path('api/ready/', health_ready),
    path('api/health/live/', health_live),
    path('api/health/ready/', health_ready),
    path('api/health/deep/', health_deep),
]

# ── API schema & docs (drf-spectacular) ──────────────────────────
if getattr(settings, "API_DOCS_PUBLIC", True) or settings.DEBUG:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularSwaggerView,
        SpectacularRedocView,
    )

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
