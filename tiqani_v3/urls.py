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
    # Contracts
    path('api/contracts/', include('contract.urls')),
    # Wallet / Fees / Payment Prep
    path('api/wallet/', include('wallet.urls')),
    # Notifications / Activity
    path('api/notifications/', include('notification.urls')),
    # Dealership
    path('api/dealership/', include('dealership.urls')),
    # Admin Dashboard
    path('api/admin/', include('dashboard.urls')),
    # Health
    path('api/health/', health),
    path('api/health/live/', health_live),
    path('api/health/ready/', health_ready),
    path('api/health/deep/', health_deep),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
