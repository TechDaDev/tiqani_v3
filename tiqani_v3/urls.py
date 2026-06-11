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
from .views import health

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
    # Health
    path('api/health/', health),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
